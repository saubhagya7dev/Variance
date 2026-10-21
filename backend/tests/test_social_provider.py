import json
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest

from app.config import Settings
from app.providers import social


@pytest.mark.parametrize("platform", ["instagram", "facebook", "threads", "x"])
async def test_publish_request_contracts_and_no_secret_in_url(monkeypatch, platform):
    calls = []
    saved = []

    def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer private-token"
        assert "private-token" not in str(request.url)
        path = request.url.path
        if request.method == "GET":
            return httpx.Response(200, json={"status_code": "FINISHED", "status": "FINISHED"})
        if path.endswith("/media/upload"):
            assert json.loads(request.content)["media_category"] == "tweet_image"
            return httpx.Response(200, json={"data": {"id": "456"}})
        if path.endswith("/media/metadata"):
            assert (
                json.loads(request.content)["metadata"]["alt_text"]["text"] == "Artwork description"
            )
            return httpx.Response(200, json={"data": {"id": "456"}})
        if path.endswith("/tweets"):
            body = json.loads(request.content)
            assert body["text"] == "Approved text" and body["media"]["media_ids"] == ["456"]
            return httpx.Response(201, json={"data": {"id": "789"}})
        if path.endswith("/photos"):
            assert b'filename="artwork.jpg"' in request.content
            assert b"Approved text" in request.content and b"Artwork description" in request.content
            return httpx.Response(200, json={"id": "456", "post_id": "123_789"})
        data = parse_qs(request.content.decode())
        if path.endswith("_publish"):
            assert data["creation_id"] == ["456"]
            assert saved == ["456"]
            return httpx.Response(200, json={"id": "789"})
        assert data["image_url"] == ["https://example.com/art.jpg"]
        assert data["alt_text"] == ["Artwork description"]
        assert data["text" if platform == "threads" else "caption"] == ["Approved text"]
        return httpx.Response(200, json={"id": "456"})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        social.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    config = Settings(
        meta_graph_version="v25.0",
        instagram_access_token="private-token",
        facebook_page_access_token="private-token",
        threads_access_token="private-token",
        x_user_access_token="private-token",
        _env_file=None,
    )
    delivery = SimpleNamespace(platform=platform, account_id="123")
    result = await social.publish(
        config,
        delivery,
        {"post_text": "Approved text", "alt_text": "Artwork description"},
        b"jpeg",
        "https://example.com/art.jpg",
        saved.append,
    )
    assert result == ("123_789" if platform == "facebook" else "789")
    assert len(calls) == {"instagram": 3, "threads": 3, "facebook": 1, "x": 3}[platform]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429, json={}),
        httpx.Response(200, json={"errors": [{"detail": "not accepted"}]}),
        httpx.Response(200, json={"id": "bad/id"}),
    ],
)
async def test_provider_failure_never_retries_write(monkeypatch, response):
    calls = []

    def handler(request):
        calls.append(request)
        return response

    original = httpx.AsyncClient
    monkeypatch.setattr(
        social.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    with pytest.raises((ValueError, httpx.HTTPStatusError)):
        await social.publish(
            Settings(_env_file=None),
            SimpleNamespace(platform="facebook", account_id="123"),
            {"post_text": "Post", "alt_text": "Art"},
            b"jpeg",
            "",
            lambda _: None,
        )
    assert len(calls) == 1


async def test_unready_container_never_reaches_publish(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            200, json={"id": "456"} if request.method == "POST" else {"status": "ERROR"}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        social.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    with pytest.raises(ValueError):
        await social.publish(
            Settings(_env_file=None),
            SimpleNamespace(platform="threads", account_id="123"),
            {"post_text": "Post", "alt_text": "Art"},
            b"jpeg",
            "https://example.com/art.jpg",
            lambda _: None,
        )
    assert len(calls) == 2 and not any(p.endswith("_publish") for p in calls)


@pytest.mark.parametrize(
    ("platform", "body", "owner", "expected"),
    [
        (
            "instagram",
            {
                "id": "789",
                "caption": "Post",
                "owner": {"id": "123"},
                "like_count": 0,
                "comments_count": 4,
            },
            "123",
            {"likes": 0, "comments": 4},
        ),
        (
            "facebook",
            {
                "id": "789",
                "message": "Post",
                "from": {"id": "123"},
                "likes": {"summary": {"total_count": 3}},
                "comments": {"summary": {"total_count": 2}},
            },
            "123",
            {"likes": 3, "comments": 2, "shares": None},
        ),
        ("threads", {"id": "789", "text": "Post", "username": "artist"}, "artist", {}),
        (
            "x",
            {
                "data": {
                    "id": "789",
                    "text": "Post",
                    "author_id": "123",
                    "public_metrics": {"like_count": 7},
                }
            },
            "123",
            {"like_count": 7},
        ),
    ],
)
async def test_remote_read_normalizes_native_metrics_without_filling_missing_counts(
    monkeypatch, platform, body, owner, expected
):
    def handler(request):
        assert request.method == "GET" and request.url.path.endswith("/789")
        return httpx.Response(200, json=body)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        social.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = await social.read_post(Settings(_env_file=None), platform, "789")
    assert result["owner"] == owner and result["text"] == "Post" and result["metrics"] == expected


async def test_threads_insights_preserve_missing_fields(monkeypatch):
    def handler(request):
        assert request.method == "GET" and request.url.path.endswith("/789/insights")
        return httpx.Response(
            200,
            json={
                "data": [
                    {"name": "likes", "values": [{"value": 0}]},
                    {"name": "views", "values": []},
                ]
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        social.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = await social.metrics(
        Settings(_env_file=None), SimpleNamespace(platform="threads", remote_id="789")
    )
    assert result == {"likes": 0}

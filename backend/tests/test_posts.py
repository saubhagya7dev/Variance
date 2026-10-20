import json
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest

from app.post_service import gemini_draft
from tests.test_creation import batch, pixels, prepared


def ready(client):
    _, path, _, prompt, _ = prepared(client)
    b, _ = batch(client, path, prompt, 1)
    art = client.post(path + f"/batches/{b['id']}/artwork", content=pixels()).json()
    client.patch(path + f"/artwork/{art['id']}", json={"revision": 1, "decision": "approved"})
    post = client.post(path + "/posts", json={"artwork_id": art["id"]}).json()
    return path, art, post


def edit_payload(post, **changes):
    return {
        "revision": post["revision"],
        "caption": post["caption"],
        "hashtags": post["hashtags"],
        "alt_text": "A brown rectangular test fixture.",
        "disclosure": post["disclosure"],
    } | changes


def approved(client):
    path, art, post = ready(client)
    row = client.post(path + f"/posts/{post['id']}/versions", json=edit_payload(post)).json()
    response = client.post(
        path + f"/posts/{row['id']}/approve", json={"revision": 1, "content_reviewed": True}
    )
    assert response.status_code == 200, response.text
    return path, art, response.json()


def test_versions_validation_and_export(client):
    path, art, row = ready(client)
    assert row["provider"] == "local"
    assert row["validation"]["errors"]
    assert client.get(path + f"/posts/{row['id']}/export").status_code == 409
    assert (
        client.post(
            path + f"/posts/{row['id']}/approve", json={"revision": 1, "content_reviewed": True}
        ).status_code
        == 422
    )
    new = client.post(path + f"/posts/{row['id']}/versions", json=edit_payload(row)).json()
    assert new["version"] == 2 and new["status"] == "draft"
    assert (
        client.post(
            path + f"/posts/{new['id']}/approve", json={"revision": 1, "content_reviewed": False}
        ).status_code
        == 422
    )
    client.post(
        path + f"/posts/{new['id']}/approve", json={"revision": 1, "content_reviewed": True}
    )
    response = client.get(path + f"/posts/{new['id']}/export")
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as pack:
        assert pack.read("artwork.png")
        assert new["disclosure"] in pack.read("caption.txt").decode()
        assert json.loads(pack.read("manifest.json"))["status"] == "approved"
    rows = client.get(path + "/posts").json()
    assert rows[1]["alt_text"] == ""
    assert rows[0]["status"] == "approved"


def test_publication_is_explicit_validated_and_idempotent(client):
    path, _, row = approved(client)
    endpoint = path + f"/posts/{row['id']}/publication"
    payload = {
        "revision": row["revision"],
        "url": "https://www.instagram.com/p/qa-fixture/",
        "published_at": "2020-01-01T12:00:00Z",
        "manually_published": True,
    }
    assert (
        client.post(
            endpoint, json=payload | {"url": "https://instagram.com.evil.test/p/x"}
        ).status_code
        == 422
    )
    assert (
        client.post(endpoint, json=payload | {"published_at": "2999-01-01T00:00:00Z"}).status_code
        == 422
    )
    assert (
        client.post(endpoint, json=payload | {"published_at": "2020-01-01T12:00:00"}).status_code
        == 422
    )
    assert client.post(endpoint, json=payload).json()["status"] == "published"
    assert client.post(endpoint, json=payload).json()["revision"] == 3
    assert (
        client.post(
            endpoint, json=payload | {"url": "https://www.instagram.com/p/other/"}
        ).status_code
        == 409
    )


def test_changed_artwork_invalidates_approval(client):
    path, art, row = approved(client)
    client.patch(path + f"/artwork/{art['id']}", json={"revision": 2, "decision": "rejected"})
    assert client.get(path + f"/posts/{row['id']}/export").status_code == 409
    assert client.post(path + "/posts", json={"artwork_id": art["id"]}).status_code == 409
    client.patch(path + f"/artwork/{art['id']}", json={"revision": 3, "decision": "approved"})
    assert client.get(path + f"/posts/{row['id']}/export").status_code == 409
    fresh = client.post(path + f"/posts/{row['id']}/versions", json=edit_payload(row)).json()
    assert fresh["status"] == "draft" and not fresh["validation"]["errors"]


def test_limits_ownership_archive_and_gemini_gate(client):
    path, art, post = ready(client)
    assert (
        client.post(
            path + "/posts", json={"artwork_id": art["id"], "provider": "gemini"}
        ).status_code
        == 409
    )
    long = client.post(
        path + f"/posts/{post['id']}/versions", json=edit_payload(post, caption="x" * 2300)
    ).json()
    assert any("character" in e for e in long["validation"]["errors"])
    tags = client.post(
        path + f"/posts/{post['id']}/versions",
        json=edit_payload(post, caption="#one #two #three #four #five #six"),
    ).json()
    assert any("hashtags" in e for e in tags["validation"]["errors"])
    assert (
        client.post(
            path + f"/posts/{post['id']}/versions", json=edit_payload(post, hashtags=["bad tag"])
        ).status_code
        == 422
    )
    other, _, _ = ready(client)
    assert client.get(other + f"/posts/{post['id']}/export").status_code == 404
    client.post(path + "/archive", json={"revision": 1, "archived": True})
    assert (
        client.post(path + f"/posts/{post['id']}/versions", json=edit_payload(post)).status_code
        == 409
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, "rejected"),
        (401, "authentication"),
        (403, "access denied"),
        (404, "gemini-2.5-flash"),
        (429, "quota"),
        (503, "HTTP 503"),
    ],
)
def test_caption_provider_errors_are_actionable_and_preserve_work(
    client, monkeypatch, status, expected
):
    from app.routers import posts

    path, art, _ = ready(client)
    config = client.app.state.config
    config.gemini_api_key = "secret-test-key"
    config.gemini_captions_enabled = True

    async def fail(*args):
        response = httpx.Response(
            status,
            request=httpx.Request(
                "POST",
                "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent",
            ),
            json={"error": {"message": "secret-test-key private-caption-context"}},
        )
        response.raise_for_status()

    monkeypatch.setattr(posts, "gemini_draft", fail)
    response = client.post(path + "/posts", json={"artwork_id": art["id"], "provider": "gemini"})
    assert response.status_code == 502
    assert expected in response.json()["detail"]
    assert "secret-test-key" not in response.text
    assert "private-caption-context" not in response.text
    assert len(client.get(path + "/posts").json()) == 1
    assert not client.app.state.discovery_busy
    assert client.post(path + "/posts", json={"artwork_id": art["id"]}).status_code == 200


async def test_gemini_caption_contract_and_invalid_output(client, monkeypatch):
    import httpx
    import pytest

    from app import post_service

    responses = [
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "caption": "A new creative perspective.",
                                        "hashtags": ["FanArt"],
                                    }
                                )
                            }
                        ]
                    },
                }
            ]
        },
        {"candidates": [{"finishReason": "SAFETY"}]},
    ]

    async def handle(request):
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert request.url.host == "generativelanguage.googleapis.com"
        return httpx.Response(200, json=responses.pop(0))

    original = httpx.AsyncClient
    monkeypatch.setattr(
        post_service.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(handle), **kw),
    )
    text, tags = await gemini_draft(client.app.state.config, {}, "minimal", "instagram")
    assert text and tags == ["FanArt"]
    with pytest.raises(ValueError):
        await gemini_draft(client.app.state.config, {}, "minimal", "instagram")

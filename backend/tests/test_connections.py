import httpx
import pytest

from app.routers import connections


def configure(client):
    config = client.app.state.config
    config.meta_graph_version = "v25.0"
    config.instagram_access_token = "private-ig"
    config.facebook_page_access_token = "private-fb"
    config.facebook_page_id = "123"
    config.threads_access_token = "private-threads"
    config.x_user_access_token = "private-x"


def test_missing_connections_never_call_provider_or_expose_secrets(client):
    rows = client.get("/api/connections").json()
    assert len(rows) == 4 and all(not row["configured"] for row in rows)
    for row in rows:
        assert client.post(f"/api/connections/{row['platform']}/check").status_code == 409
    configure(client)
    response = client.get("/api/connections")
    assert "private-" not in response.text
    assert all(row["configured"] and row["status"] == "not_verified" for row in response.json())
    assert client.post("/api/connections/unknown/check").status_code == 422


@pytest.mark.parametrize(
    ("platform", "host", "token", "body"),
    [
        (
            "instagram",
            "graph.instagram.com",
            "private-ig",
            {"user_id": "123", "username": "artist"},
        ),
        ("facebook", "graph.facebook.com", "private-fb", {"id": "123", "name": "Studio"}),
        ("threads", "graph.threads.net", "private-threads", {"id": "123", "username": "artist"}),
        ("x", "api.x.com", "private-x", {"data": {"id": "123", "username": "artist"}}),
    ],
)
def test_connection_identity_uses_read_only_request(
    client, monkeypatch, platform, host, token, body
):
    configure(client)

    def handle(request):
        assert request.method == "GET" and request.url.host == host
        assert request.headers["Authorization"] == f"Bearer {token}"
        assert token not in str(request.url)
        return httpx.Response(200, json=body)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        connections.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(handle), **kw),
    )
    response = client.post(f"/api/connections/{platform}/check")
    assert response.status_code == 200
    assert response.json()["status"] == "identity_verified"
    assert not response.json()["publishing_enabled"] and token not in response.text


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, {"error": "private-fb"}, 502),
        (429, {}, 502),
        (200, {"id": "999", "name": "Wrong Page"}, 409),
        (200, {}, 502),
        (200, [], 502),
        (302, {}, 502),
    ],
)
def test_connection_failure_is_safe(client, monkeypatch, status, body, expected):
    configure(client)
    original = httpx.AsyncClient
    monkeypatch.setattr(
        connections.httpx,
        "AsyncClient",
        lambda **kw: original(
            transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)), **kw
        ),
    )
    response = client.post("/api/connections/facebook/check")
    assert response.status_code == expected and "private-fb" not in response.text

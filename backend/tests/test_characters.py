from fastapi.testclient import TestClient

from app.main import create_app

IDENTITY = {
    "name": "Fixture character",
    "franchise": "Test franchise",
    "variant": "Original design",
    "fictional_confirmed": True,
}


def create(client):
    response = client.post("/api/characters", json=IDENTITY)
    assert response.status_code == 201
    return response.json()


def test_project_survives_app_restart(client):
    project = create(client)
    app = create_app(client.app.state.config)
    with TestClient(app, base_url="http://localhost") as second:
        assert second.get(f"/api/characters/{project['id']}").json()["name"] == IDENTITY["name"]
        assert len(second.get("/api/characters").json()) == 1


def test_identity_confirmation_and_validation(client):
    for changes in (
        {"name": "   "},
        {"fictional_confirmed": False},
        {"variant": ""},
        {"status": "published"},
    ):
        assert client.post("/api/characters", json=IDENTITY | changes).status_code == 422


def test_updates_are_persisted_and_stale_writes_rejected(client):
    project = create(client)
    path = f"/api/characters/{project['id']}"
    payload = {"revision": 1, "notes": "Reference notes", "direction": "Editorial ink"}
    result = client.patch(path, json=payload)
    assert result.status_code == 200
    assert result.json()["revision"] == 2
    assert client.patch(path, json=payload | {"notes": "Stale overwrite"}).status_code == 409
    assert client.get(path).json()["notes"] == "Reference notes"


def test_archive_restore_and_search(client):
    project = create(client)
    path = f"/api/characters/{project['id']}"
    assert len(client.get("/api/characters?q=Fixture").json()) == 1
    assert client.get("/api/characters?q=%25").json() == []
    assert client.post(path + "/archive", json={"revision": 1, "archived": True}).status_code == 200
    assert client.get("/api/characters").json() == []
    assert len(client.get("/api/characters?archived=true").json()) == 1
    assert client.patch(path, json={"revision": 2, "notes": "", "direction": ""}).status_code == 409
    assert (
        client.post(path + "/archive", json={"revision": 2, "archived": False}).status_code == 200
    )
    assert len(client.get("/api/characters").json()) == 1


def test_nonexistent_and_untrusted_writes(client):
    assert client.get("/api/characters/missing").status_code == 404
    client.headers.pop("X-Variance-Client")
    assert client.post("/api/characters", json=IDENTITY).status_code == 403


def test_capabilities_do_not_claim_live_integrations(client):
    data = client.get("/api/capabilities").json()
    assert data["research"]["available"]
    assert data["research"]["provider"] == "wikipedia"
    assert not data["publishing"]["available"]
    assert "api_key" not in str(data)

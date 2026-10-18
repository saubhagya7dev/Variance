from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from tests.test_characters import create


def pixels(color="brown"):
    output = BytesIO()
    Image.new("RGB", (24, 32), color).save(output, "PNG")
    return output.getvalue()


def prepared(client):
    project = create(client)
    path = f"/api/characters/{project['id']}"
    ref = client.post(path + "/references/upload", content=pixels()).json()
    client.patch(path + f"/references/{ref['id']}", json={"selected": True})
    direction = {"style": "Editorial ink", "palette": "Warm brown", "aspect_ratio": "4:5"}
    preview = client.post(path + "/prompts/preview", json=direction)
    assert preview.status_code == 200, preview.text
    payload = {
        "direction": direction,
        "prompt_text": preview.json()["prompt_text"],
        "context_hash": preview.json()["context_hash"],
    }
    prompt = client.post(path + "/prompts", json=payload)
    assert prompt.status_code == 200, prompt.text
    return project, path, ref, prompt.json(), payload


def batch(client, path, prompt, count=2):
    payload = {"prompt_id": prompt["id"], "target_count": count, "request_key": str(uuid4())}
    response = client.post(path + "/batches", json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


def test_prompt_requires_references_and_rejects_changed_context(client):
    project = create(client)
    path = f"/api/characters/{project['id']}"
    assert client.post(path + "/prompts/preview", json={}).status_code == 409
    project, path, ref, prompt, payload = prepared(client)
    assert prompt["version"] == 1
    client.patch(path, json={"revision": 1, "direction": "New direction", "notes": ""})
    assert client.post(path + "/prompts", json=payload).status_code == 409
    assert len(client.get(path + "/prompts").json()) == 1
    assert (
        client.post(path + "/prompts/preview", json={"aspect_ratio": "anything"}).status_code == 422
    )


def test_prompt_versions_and_reference_pack_are_frozen(client):
    _, path, ref, first, payload = prepared(client)
    second = client.post(
        path + "/prompts", json=payload | {"prompt_text": "A revised composition, with warm ink."}
    ).json()
    assert second["version"] == 2
    client.delete(path + f"/references/{ref['id']}")
    exported = client.get(path + f"/prompts/{first['id']}/pack")
    assert exported.status_code == 200
    with ZipFile(BytesIO(exported.content)) as pack:
        assert pack.read("prompt.txt").decode() == first["prompt_text"]
        assert "references/01.png" in pack.namelist()
        assert Image.open(BytesIO(pack.read("references/01.png"))).size == (24, 32)
    assert client.get(path + "/prompts").json()[0]["prompt_text"] == second["prompt_text"]


def test_batch_idempotency_limits_deduplication_and_review(client):
    _, path, _, prompt, _ = prepared(client)
    created, payload = batch(client, path, prompt)
    assert client.post(path + "/batches", json=payload).json()["id"] == created["id"]
    assert client.post(path + "/batches", json=payload | {"target_count": 4}).status_code == 409
    assert client.post(path + "/batches", json=payload | {"target_count": 10}).status_code == 422
    upload = path + f"/batches/{created['id']}/artwork"
    first = client.post(upload, content=pixels()).json()
    assert client.post(upload, content=pixels()).json()["id"] == first["id"]
    second = client.post(upload, content=pixels("blue")).json()
    assert client.get(path + "/batches").json()[0]["status"] == "awaiting_review"
    assert client.post(upload, content=pixels("red")).status_code == 409
    review = path + f"/artwork/{first['id']}"
    payload = {
        "decision": "approved",
        "review_note": "Identity and composition checked",
        "revision": 1,
    }
    assert client.patch(review, json=payload).json()["revision"] == 2
    assert client.patch(review, json=payload).status_code == 409
    client.patch(
        path + f"/artwork/{second['id']}",
        json={"decision": "rejected", "review_note": "Wrong palette", "revision": 1},
    )
    assert client.get(path + "/batches").json()[0]["status"] == "reviewed"
    client.patch(review, json=payload | {"decision": "pending", "revision": 2})
    assert client.get(path + "/batches").json()[0]["status"] == "awaiting_review"


def test_creation_ownership_archived_writes_and_invalid_images(client):
    _, path, _, prompt, _ = prepared(client)
    created, _ = batch(client, path, prompt)
    upload = path + f"/batches/{created['id']}/artwork"
    assert client.post(upload, content=b"not an image").status_code == 422
    art = client.post(upload, content=pixels()).json()
    other = create(client)
    other_path = f"/api/characters/{other['id']}"
    assert client.get(other_path + f"/prompts/{prompt['id']}/pack").status_code == 404
    assert client.get(other_path + f"/batches/{created['id']}/artwork").status_code == 404
    assert client.get(other_path + f"/artwork/{art['id']}/image").status_code == 404
    client.post(path + "/archive", json={"revision": 1, "archived": True})
    assert client.post(upload, content=pixels("blue")).status_code == 409
    assert (
        client.patch(
            path + f"/artwork/{art['id']}", json={"decision": "approved", "revision": 1}
        ).status_code
        == 409
    )


def test_manual_batch_and_review_survive_restart(client):
    _, path, _, prompt, _ = prepared(client)
    created, _ = batch(client, path, prompt, count=1)
    art = client.post(path + f"/batches/{created['id']}/artwork", content=pixels()).json()
    client.patch(path + f"/artwork/{art['id']}", json={"decision": "approved", "revision": 1})
    with TestClient(create_app(client.app.state.config), base_url="http://localhost") as restarted:
        assert restarted.get(path + "/batches").json()[0]["status"] == "reviewed"
        assert restarted.get(path + f"/artwork/{art['id']}/image").status_code == 200
        assert (
            restarted.get(path + f"/batches/{created['id']}/artwork").json()[0]["decision"]
            == "approved"
        )

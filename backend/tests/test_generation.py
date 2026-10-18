import asyncio
import base64
import json
from uuid import uuid4

import httpx
from sqlmodel import Session, select

from app import generation
from app.creation_models import CreationBatch, PromptVersion
from app.models import ProviderCall
from tests.test_creation import batch, pixels, prepared


def test_api_requires_free_plan_setup(client):
    _, path, _, prompt, _ = prepared(client)
    response = client.post(
        path + "/batches",
        json={"prompt_id": prompt["id"], "mode": "api", "request_key": str(uuid4())},
    )
    assert response.status_code == 409
    assert not client.get("/api/capabilities").json()["generation"]["available"]


async def test_partial_failure_persists_results_without_retry(client, monkeypatch):
    _, path, _, prompt, _ = prepared(client)
    row, _ = batch(client, path, prompt)
    state = client.app.state
    state.config.cloudflare_account_id = "a" * 32
    state.config.cloudflare_api_token = "test-only"
    state.config.cloudflare_free_plan_confirmed = True
    with Session(state.engine) as db:
        model = db.get(CreationBatch, row["id"])
        model.mode, model.status = "api", "running"
        db.add(model)
        db.commit()
    calls = []

    async def fake(*args):
        calls.append(1)
        if len(calls) == 2:
            raise httpx.ReadTimeout("ambiguous response")
        return pixels()

    monkeypatch.setattr(generation, "generate", fake)
    await generation.run_batch(state, row["id"])
    assert len(calls) == 2
    assert len(client.get(path + f"/batches/{row['id']}/artwork").json()) == 1
    assert client.get(path + "/batches").json()[0]["status"] == "failed"
    assert client.post(path + f"/batches/{row['id']}/artwork", content=pixels()).status_code == 409
    with Session(state.engine) as db:
        assert len(db.exec(select(ProviderCall)).all()) == 2


async def test_worker_completes_queued_batch_and_idempotency(client, monkeypatch):
    _, path, _, prompt, _ = prepared(client)
    state = client.app.state
    state.config.cloudflare_account_id = "a" * 32
    state.config.cloudflare_api_token = "test-only"
    state.config.cloudflare_free_plan_confirmed = True

    async def fake(*args):
        return pixels()

    monkeypatch.setattr(generation, "generate", fake)
    payload = {
        "prompt_id": prompt["id"],
        "mode": "api",
        "target_count": 1,
        "request_key": str(uuid4()),
    }
    row = client.post(path + "/batches", json=payload).json()
    assert client.post(path + "/batches", json=payload).json()["id"] == row["id"]
    assert client.post(path + "/batches", json=payload | {"mode": "manual"}).status_code == 409
    for _ in range(30):
        result = client.get(path + "/batches").json()[0]
        if result["status"] == "awaiting_review":
            break
        await asyncio.sleep(0.1)
    assert result["status"] == "awaiting_review"


def test_recovery_does_not_resend_running_requests(client):
    _, path, _, prompt, _ = prepared(client)
    row, _ = batch(client, path, prompt)
    with Session(client.app.state.engine) as db:
        model = db.get(CreationBatch, row["id"])
        model.mode, model.status = "api", "running"
        db.add(model)
        db.commit()
    generation.recover(client.app.state.engine)
    assert client.get(path + "/batches").json()[0]["status"] == "interrupted"


async def test_cloudflare_multipart_contract(client, monkeypatch):
    _, _, _, prompt, _ = prepared(client)
    state = client.app.state
    state.config.cloudflare_account_id = "a" * 32
    state.config.cloudflare_api_token = "test-only"
    captured = []

    async def handle(request):
        captured.append(await request.aread())
        assert request.url.host == "api.cloudflare.com"
        assert "multipart/form-data" in request.headers["content-type"]
        return httpx.Response(
            200, json={"success": True, "result": {"image": base64.b64encode(pixels()).decode()}}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        generation.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    with Session(state.engine) as db:
        model = db.get(PromptVersion, prompt["id"])
    assert await generation.generate(state.config, model) == pixels()
    assert b'name="input_image_0"' in captured[0]
    assert b'name="width"' in captured[0]
    assert json.loads(model.context_json)["references"]

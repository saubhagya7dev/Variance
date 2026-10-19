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


def test_api_requires_explicit_paid_enablement(client):
    client.app.state.config.gemini_api_key = "text-feature-key-only"
    _, path, _, prompt, _ = prepared(client)
    response = client.post(
        path + "/batches",
        json={"prompt_id": prompt["id"], "mode": "api", "request_key": str(uuid4())},
    )
    assert response.status_code == 409
    assert not client.get("/api/capabilities").json()["generation"]["available"]


def test_legacy_cloudflare_queue_is_not_rerouted(client):
    from pathlib import Path

    from app.db import migrate

    _, path, _, prompt, _ = prepared(client)
    row, _ = batch(client, path, prompt)
    with client.app.state.engine.begin() as db:
        db.exec_driver_sql(
            "UPDATE creation_batches SET mode='api', status='queued' WHERE id=?", (row["id"],)
        )
        # Apply the data portion to a legacy queued row: never submit it to Gemini.
        sql = (Path(__file__).parents[1] / "app/migrations/006_generation_provider.sql").read_text()
        for statement in sql.split(";")[2:]:
            if statement.strip():
                db.exec_driver_sql(statement)
    migrate(client.app.state.engine)
    result = client.get(path + "/batches").json()[0]
    assert result["provider"] == "cloudflare"
    assert result["status"] == "interrupted"
    assert "retired" in result["error"]


async def test_text_only_response_is_not_an_image(client, monkeypatch):
    import pytest

    _, _, _, prompt, _ = prepared(client)
    state = client.app.state
    state.config.gemini_api_key = "test-only"
    state.config.gemini_image_paid_enabled = True
    original = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [{"type": "text", "text": "No image generated"}],
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        generation.httpx, "AsyncClient", lambda **kw: original(transport=transport, **kw)
    )
    with Session(state.engine) as db:
        model = db.get(PromptVersion, prompt["id"])
    with pytest.raises(ValueError, match="no completed image"):
        await generation.generate(state.config, model)


async def test_partial_failure_persists_results_without_retry(client, monkeypatch):
    _, path, _, prompt, _ = prepared(client)
    row, _ = batch(client, path, prompt)
    state = client.app.state
    state.config.gemini_api_key = "test-only"
    state.config.gemini_image_paid_enabled = True
    with Session(state.engine) as db:
        model = db.get(CreationBatch, row["id"])
        model.mode, model.status = "api", "running"
        model.provider, model.model = "gemini", "gemini-nano-banana-2.1"
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
    state.config.gemini_api_key = "test-only"
    state.config.gemini_image_paid_enabled = True

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
        model.provider, model.model = "gemini", "gemini-nano-banana-2.1"
        db.add(model)
        db.commit()
    generation.recover(client.app.state.engine)
    assert client.get(path + "/batches").json()[0]["status"] == "interrupted"


async def test_gemini_image_contract(client, monkeypatch):
    _, _, _, prompt, _ = prepared(client)
    state = client.app.state
    state.config.gemini_api_key = "test-only"
    state.config.gemini_image_paid_enabled = True
    captured = []

    async def handle(request):
        captured.append(await request.aread())
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "test-only"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [
                            {
                                "type": "image",
                                "mime_type": "image/png",
                                "data": base64.b64encode(pixels()).decode(),
                            }
                        ],
                    }
                ],
            },
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
    payload = json.loads(captured[0])
    assert payload["input"][1]["type"] == "image"
    assert payload["response_format"]["aspect_ratio"] == "4:5"
    assert payload["store"] is False
    assert json.loads(model.context_json)["references"]

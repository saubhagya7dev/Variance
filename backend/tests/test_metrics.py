import json

import httpx
from sqlmodel import Session, select

from app import delivery_service
from app.delivery_models import Delivery, MetricSample
from app.routers import publishing
from tests.test_delivery import payload, prepared


async def published(client, monkeypatch):
    path, _, post = prepared(client, monkeypatch)

    async def send(*args):
        return "123_456"

    monkeypatch.setattr(publishing.social, "publish", send)
    response = client.post(path + f"/posts/{post['id']}/publish", json=payload(post))
    assert response.json()["status"] == "published"
    with Session(client.app.state.engine) as db:
        sample = db.exec(select(MetricSample).order_by(MetricSample.due_at)).first()
        sample.due_at = "2020-01-01T00:00:00.000000+00:00"
        db.add(sample)
        db.commit()
        db.refresh(sample)
        sample_id = sample.id

    async def identity(*args):
        return {"account_id": "123"}

    monkeypatch.setattr(delivery_service, "verify_identity", identity)
    return path, sample_id


async def test_collection_preserves_deadline_zero_and_absent_values(client, monkeypatch):
    path, sample_id = await published(client, monkeypatch)

    async def counts(*args):
        return {"likes": 0, "comments": 7, "shares": None, "bad": -1, "boolean": True, "float": 1.5}

    monkeypatch.setattr(delivery_service.social, "metrics", counts)
    assert await delivery_service.collect_one(client.app.state)
    assert not await delivery_service.collect_one(client.app.state)
    with Session(client.app.state.engine) as db:
        sample = db.get(MetricSample, sample_id)
        assert sample.status == "collected"
        assert json.loads(sample.values_json) == {"likes": 0, "comments": 7}
        assert sample.due_at.startswith("2020") and not sample.collected_at.startswith("2020")
    assert client.post(path + f"/posts/metrics/{sample_id}/retry").status_code == 409


async def test_unavailable_is_explicit_and_retry_does_not_shift_deadline(client, monkeypatch):
    path, sample_id = await published(client, monkeypatch)

    async def fail(*args):
        raise httpx.ReadTimeout("private-token")

    monkeypatch.setattr(delivery_service.social, "metrics", fail)
    assert await delivery_service.collect_one(client.app.state)
    rows = client.get(path + "/posts/deliveries").json()
    sample = rows[0]["samples"][0]
    assert sample["status"] == "unavailable" and sample["values"] == {}
    assert "private-token" not in json.dumps(rows)
    assert not await delivery_service.collect_one(client.app.state)
    client.app.state.config.metrics_enabled = True
    assert client.post(path + f"/posts/metrics/{sample_id}/retry").status_code == 200
    with Session(client.app.state.engine) as db:
        saved = db.get(MetricSample, sample_id)
        assert saved.due_at == sample["due_at"] and saved.status == "pending"


async def test_wrong_account_never_reads_metrics_and_project_ownership_is_enforced(
    client, monkeypatch
):
    path, sample_id = await published(client, monkeypatch)

    async def wrong(*args):
        return {"account_id": "999"}

    async def never(*args):
        raise AssertionError("must not request metrics for a changed account")

    monkeypatch.setattr(delivery_service, "verify_identity", wrong)
    monkeypatch.setattr(delivery_service.social, "metrics", never)
    assert await delivery_service.collect_one(client.app.state)
    with Session(client.app.state.engine) as db:
        assert db.get(MetricSample, sample_id).status == "unavailable"
        assert db.exec(select(Delivery)).one().remote_id == "123_456"
    other, _, _ = prepared(client, monkeypatch)
    client.app.state.config.metrics_enabled = True
    assert client.post(other + f"/posts/metrics/{sample_id}/retry").status_code == 404
    assert client.get(other + "/posts/deliveries").json() == []

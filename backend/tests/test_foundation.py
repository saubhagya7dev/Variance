import httpx
import pytest
from sqlmodel import Session, select

from app.db import migrate
from app.models import ProviderCall
from app.providers.runner import call_provider


def test_health_and_repeatable_migration(client):
    assert client.get("/api/health").json()["status"] == "ok"
    migrate(client.app.state.engine)
    assert client.get("/api/health").status_code == 200


def test_host_and_origin_guard(client):
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    assert (
        client.post("/api/unknown", headers={"Origin": "https://evil.example"}).status_code == 403
    )


async def test_read_retry_is_bounded_and_logged(client):
    calls, waits = [], []

    async def fail():
        calls.append(1)
        response = httpx.Response(429, request=httpx.Request("GET", "https://fixture.test"))
        raise httpx.HTTPStatusError("fixture", request=response.request, response=response)

    async def pause(seconds):
        waits.append(seconds)

    with pytest.raises(httpx.HTTPStatusError):
        await call_provider(
            client.app.state.engine, "fixture", "research", fail, retry_safe=True, sleep=pause
        )
    assert len(calls) == 3 and waits == [1, 2]
    with Session(client.app.state.engine) as db:
        assert len(db.exec(select(ProviderCall)).all()) == 3


async def test_side_effect_is_not_retried(client):
    calls = []

    async def timeout():
        calls.append(1)
        raise TimeoutError("fixture")

    with pytest.raises(TimeoutError):
        await call_provider(client.app.state.engine, "fixture", "publish", timeout)
    assert len(calls) == 1

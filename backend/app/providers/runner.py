import asyncio
import time
from collections.abc import Awaitable, Callable

import httpx
from sqlalchemy import Engine
from sqlmodel import Session

from app.models import ProviderCall


async def call_provider[T](
    engine: Engine,
    provider: str,
    kind: str,
    operation: Callable[[], Awaitable[T]],
    *,
    retry_safe: bool = False,
    timeout: float = 30,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Logs metadata, never prompts or tokens. Only explicitly safe calls are retried."""
    for attempt in range(1, 4):
        started = time.monotonic()
        status, outcome, transient = None, "success", False
        error: Exception | None = None
        try:
            async with asyncio.timeout(timeout):
                result = await operation()
            status = 200
        except httpx.HTTPStatusError as exc:
            status, outcome, error = exc.response.status_code, "http_error", exc
            transient = status == 429 or status >= 500
        except (httpx.TransportError, TimeoutError) as exc:
            outcome, transient, error = "transport_error", True, exc
        except Exception as exc:
            outcome, error = "invalid_result", exc
        with Session(engine) as db:
            db.add(
                ProviderCall(
                    provider=provider,
                    kind=kind,
                    status_code=status,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    attempt=attempt,
                    outcome=outcome,
                )
            )
            db.commit()
        if error is None:
            return result
        if not (retry_safe and transient and attempt < 3):
            raise error
        await sleep(2 ** (attempt - 1))
    raise RuntimeError("Unreachable retry state")

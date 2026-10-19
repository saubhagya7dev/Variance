"""Sequential durable queue. Ambiguous requests are never automatically retried."""

import asyncio
import base64
import json
from io import BytesIO

import httpx
from PIL import Image
from sqlmodel import Session, select

from app.creation_models import Artwork, CreationBatch, PromptVersion
from app.models import timestamp
from app.providers.runner import call_provider


async def generate(config, prompt, model=None):
    if not config.generation_ready:
        raise ValueError(
            "Gemini image API requires explicit paid enablement; no free API tier is available."
        )
    context = json.loads(prompt.context_json)
    parts = [{"type": "text", "text": prompt.prompt_text}]
    for ref in context["references"]:
        with Image.open(config.asset_dir / f"{ref['digest']}.png") as image:
            image.thumbnail((1536, 1536))
            output = BytesIO()
            image.save(output, "PNG")
            parts.append(
                {
                    "type": "image",
                    "mime_type": "image/png",
                    "data": base64.b64encode(output.getvalue()).decode(),
                }
            )
    payload = {
        "model": model or config.gemini_image_model,
        "input": parts,
        "response_format": {
            "type": "image",
            "aspect_ratio": json.loads(prompt.direction_json)["aspect_ratio"],
            "image_size": "1K",
        },
        "store": False,
    }
    if len(json.dumps(payload).encode()) > 18 * 1024 * 1024:
        raise ValueError("Reference payload is too large. Use fewer references.")
    async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
        async with client.stream(
            "POST",
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={"x-goog-api-key": config.gemini_api_key},
            json=payload,
        ) as response:
            response.raise_for_status()
            raw = bytearray()
            async for chunk in response.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > 12 * 1024 * 1024:
                    raise ValueError("Provider response too large")
    result = json.loads(raw)
    images = [
        part
        for step in result.get("steps", [])
        if step.get("type") == "model_output"
        for part in step.get("content", [])
        if part.get("type") == "image"
    ]
    image = images[0] if len(images) == 1 else {}
    if (
        result.get("status") != "completed"
        or image.get("mime_type") not in {"image/png", "image/jpeg", "image/webp"}
        or not image.get("data")
    ):
        raise ValueError(
            "Gemini returned no completed image. The request may have been blocked or returned text only."
        )
    decoded = base64.b64decode(image["data"], validate=True)
    if len(decoded) > 8 * 1024 * 1024:
        raise ValueError("Generated image exceeds 8 MB.")
    return decoded


def recover(engine):
    with Session(engine) as db:
        for row in db.exec(select(CreationBatch).where(CreationBatch.status == "running")).all():
            row.status = "interrupted"
            row.error = "The app stopped during generation. Results already saved are kept. Start a new batch to try again; no request was automatically resent."
            db.add(row)
        db.commit()


async def run_batch(state, batch_id):
    from app.routers.creation import store_artwork
    from app.routers.discovery import project_check

    try:
        with Session(state.engine) as db:
            batch = db.get(CreationBatch, batch_id)
            prompt = db.get(PromptVersion, batch.prompt_id)
            if not state.config.generation_ready or batch.provider != "gemini" or not batch.model:
                raise ValueError("Generation unavailable")
        for i in range(batch.target_count):
            with Session(state.engine) as db:
                project_check(db, batch.project_id, write=True)
            raw = await call_provider(
                state.engine,
                "gemini",
                "image_generation",
                lambda: generate(state.config, prompt, batch.model),
                timeout=130,
            )
            await asyncio.to_thread(
                store_artwork, state, batch.project_id, batch.id, raw, f"API variation {i + 1}"
            )
        with Session(state.engine) as db:
            count = len(db.exec(select(Artwork).where(Artwork.batch_id == batch_id)).all())
            if count < batch.target_count:
                raise ValueError("Duplicate provider results")
    except asyncio.CancelledError:
        raise
    except Exception:
        with Session(state.engine) as db:
            row = db.get(CreationBatch, batch_id)
            row.status = "failed"
            row.error = "Generation did not complete. Check Gemini model access, billing/quota, reference files and provider availability. Saved results are kept. Requests are never automatically retried."
            row.updated_at = timestamp()
            db.add(row)
            db.commit()


async def worker(state):
    while True:
        with Session(state.engine) as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = db.exec(
                select(CreationBatch)
                .where(CreationBatch.status == "queued")
                .order_by(CreationBatch.created_at)
            ).first()
            batch_id = row.id if row else None
            if row:
                row.status = "running"
                db.add(row)
            db.commit()
        if batch_id:
            await run_batch(state, batch_id)
        else:
            await asyncio.sleep(1)

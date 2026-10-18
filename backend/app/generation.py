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

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
SIZES = {
    "1:1": (1024, 1024),
    "4:5": (768, 960),
    "3:2": (1152, 768),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
}


async def generate(config, prompt):
    context = json.loads(prompt.context_json)
    width, height = SIZES[json.loads(prompt.direction_json)["aspect_ratio"]]
    files = {
        "prompt": (None, prompt.prompt_text),
        "width": (None, str(width)),
        "height": (None, str(height)),
    }
    for i, ref in enumerate(context["references"]):
        with Image.open(config.asset_dir / f"{ref['digest']}.png") as image:
            image.thumbnail((504, 504))
            output = BytesIO()
            image.save(output, "PNG")
            files[f"input_image_{i}"] = (f"reference-{i}.png", output.getvalue(), "image/png")
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"https://api.cloudflare.com/client/v4/accounts/{config.cloudflare_account_id}/ai/run/{MODEL}",
            headers={"Authorization": f"Bearer {config.cloudflare_api_token}"},
            files=files,
        ) as response:
            response.raise_for_status()
            raw = bytearray()
            async for chunk in response.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > 12 * 1024 * 1024:
                    raise ValueError("Provider response too large")
    result = json.loads(raw)
    if not result.get("success"):
        raise ValueError("Provider rejected generation")
    return base64.b64decode(result["result"]["image"], validate=True)


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
            if not state.config.generation_ready:
                raise ValueError("Generation unavailable")
        for i in range(batch.target_count):
            with Session(state.engine) as db:
                project_check(db, batch.project_id, write=True)
            raw = await call_provider(
                state.engine,
                "cloudflare",
                "image_generation",
                lambda: generate(state.config, prompt),
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
            row.error = "Generation did not complete. Check credentials, free quota, reference files and provider availability. Saved results are kept. Requests are never automatically retried."
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

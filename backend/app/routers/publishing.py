import asyncio
import hashlib
import io
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.delivery_models import Delivery, MetricSample
from app.delivery_service import complete
from app.image_store import download_image
from app.models import timestamp
from app.post_service import view
from app.providers import social
from app.providers.runner import call_provider
from app.routers.connections import verify_identity
from app.routers.creation import artwork_for
from app.routers.discovery import project_check
from app.routers.posts import post_for

router = APIRouter(prefix="/api/characters/{project_id}/posts", tags=["publishing"])


def jpeg_for(config, art, platform="instagram"):
    path = config.asset_dir / "artwork" / f"{art.digest}.png"
    if not path.is_file():
        raise HTTPException(409, "Artwork file missing.")
    with Image.open(path) as image:
        if platform == "instagram" and not 0.8 <= image.width / image.height <= 1.91:
            raise HTTPException(
                409,
                "Instagram publishing supports images with aspect ratios from 4:5 to 1.91:1. Import an appropriate crop and approve it first.",
            )
        image = image.convert("RGB")
        image.thumbnail((1440, 1440))
        output = io.BytesIO()
        image.save(output, "JPEG", quality=90)
    return output.getvalue()


class PublishInput(BaseModel):
    revision: int = Field(ge=1)
    account_id: str = Field(pattern=r"^\d+$")
    confirmed: Literal[True]
    public_image_url: str = Field(default="", max_length=2000)


@router.get("/deliveries")
def deliveries(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        return [
            {
                **row.model_dump(exclude={"fingerprint", "content_json"}),
                "samples": [
                    {**s.model_dump(exclude={"values_json"}), "values": json.loads(s.values_json)}
                    for s in db.exec(
                        select(MetricSample)
                        .where(MetricSample.delivery_id == row.id)
                        .order_by(MetricSample.due_at)
                    )
                ],
            }
            for row in db.exec(
                select(Delivery)
                .where(Delivery.project_id == project_id)
                .order_by(Delivery.created_at.desc())
            )
        ]


@router.get("/{post_id}/publish-image")
def publish_image(project_id: str, post_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        row = post_for(db, project_id, post_id)
        art = artwork_for(db, project_id, row.artwork_id)
        return Response(
            jpeg_for(request.app.state.config, art, row.platform),
            media_type="image/jpeg",
            headers={"Content-Disposition": 'attachment; filename="variance-publish.jpg"'},
        )


@router.post("/{post_id}/publish")
async def publish_post(project_id: str, post_id: str, payload: PublishInput, request: Request):
    config, engine = request.app.state.config, request.app.state.engine
    if not config.publish_enabled:
        raise HTTPException(409, "Set PUBLISH_ENABLED=true and restart to enable live posting.")
    with Session(engine) as db:
        project_check(db, project_id, write=True)
        row = post_for(db, project_id, post_id)
        platform = row.platform
    identity = await verify_identity(platform, config)
    if identity["account_id"] != payload.account_id:
        raise HTTPException(409, "Destination account changed. Check the connection again.")
    # Read the hosted bytes before reserving a side-effecting request.
    hosted = None
    if platform in ("instagram", "threads"):
        try:
            hosted = await asyncio.to_thread(download_image, payload.public_image_url)
        except Exception:
            raise HTTPException(
                422, "Provide a public HTTPS URL serving the downloaded publication JPEG unchanged."
            ) from None
    with Session(engine) as db:
        db.exec(text("BEGIN IMMEDIATE"))
        project_check(db, project_id, write=True)
        row = post_for(db, project_id, post_id)
        art = artwork_for(db, project_id, row.artwork_id)
        rendered = view(row, art)
        if (
            row.status != "approved"
            or row.revision != payload.revision
            or rendered["validation"]["errors"]
        ):
            raise HTTPException(
                409, "Post or artwork changed. Review and approve the current version."
            )
        jpeg = jpeg_for(config, art, platform)
        if hosted is not None and hashlib.sha256(hosted).digest() != hashlib.sha256(jpeg).digest():
            raise HTTPException(
                422,
                "Hosted image differs from the publication JPEG. Upload the exact downloaded file.",
            )
        content = {
            "post_text": rendered["post_text"],
            "alt_text": row.alt_text,
            "digest": art.digest,
        }
        fingerprint = hashlib.sha256(
            json.dumps([platform, payload.account_id, art.digest, rendered["post_text"]]).encode()
        ).hexdigest()
        if db.exec(select(Delivery).where(Delivery.fingerprint == fingerprint)).first():
            raise HTTPException(
                409, "This content already has a publication attempt. Check its delivery record."
            )
        today = timestamp()[:10]
        attempts = db.exec(select(Delivery).where(Delivery.created_at >= today)).all()
        if len(attempts) >= config.daily_post_cap:
            raise HTTPException(
                409, "Daily publication cap reached (UTC). Uncertain attempts count toward the cap."
            )
        delivery = Delivery(
            project_id=project_id,
            post_id=post_id,
            platform=platform,
            account_id=payload.account_id,
            account_name=identity["name"],
            fingerprint=fingerprint,
            content_json=json.dumps(content),
        )
        row.status = "publishing"
        row.revision += 1
        db.add(row)
        db.add(delivery)
        try:
            db.commit()
        except IntegrityError:
            raise HTTPException(
                409, "A publication attempt already exists for this post."
            ) from None
        db.refresh(delivery)
        delivery_id = delivery.id
        # Do not keep a read transaction open across network requests or container saves.
        db.expunge(delivery)
        db.rollback()

        def save_container(container):
            with Session(engine) as save:
                item = save.get(Delivery, delivery_id)
                item.container_id = container
                save.add(item)
                save.commit()

        try:
            remote = await call_provider(
                engine,
                platform,
                "publish",
                lambda: social.publish(
                    config, delivery, content, jpeg, payload.public_image_url, save_container
                ),
                timeout=180,
            )
            delivery = db.get(Delivery, delivery_id)
            complete(db, delivery, remote)
            db.commit()
        except Exception:
            db.rollback()
            delivery = db.get(Delivery, delivery_id)
            delivery.status = "uncertain"
            delivery.error = "Result uncertain. Check the native account and reconcile using the remote post ID. Automatic resend is blocked."
            row = post_for(db, project_id, post_id)
            row.status = "uncertain"
            db.add(row)
            db.add(delivery)
            db.commit()
        db.refresh(delivery)
        return delivery.model_dump(exclude={"content_json", "fingerprint"})


class ReconcileInput(BaseModel):
    remote_id: str = Field(pattern=r"^[0-9]+(?:_[0-9]+)?$")


@router.post("/{post_id}/reconcile")
async def reconcile(project_id: str, post_id: str, payload: ReconcileInput, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id, write=True)
        delivery = db.exec(
            select(Delivery).where(Delivery.post_id == post_id, Delivery.project_id == project_id)
        ).first()
        if not delivery or delivery.status != "uncertain":
            raise HTTPException(409, "No uncertain publication to reconcile.")
        try:
            identity = await verify_identity(delivery.platform, request.app.state.config)
            if identity["account_id"] != delivery.account_id:
                raise ValueError("Destination account changed")
            remote = await social.read_post(
                request.app.state.config, delivery.platform, payload.remote_id
            )
            content = json.loads(delivery.content_json)
            owner = delivery.account_name if delivery.platform == "threads" else delivery.account_id
            if (
                remote["id"] != payload.remote_id
                or remote["owner"] != owner
                or remote["text"] != content["post_text"]
            ):
                raise ValueError()
        except Exception:
            raise HTTPException(
                409,
                "Could not verify the remote author and exact post text. Delivery remains unresolved.",
            ) from None
        db.rollback()
        db.exec(text("BEGIN IMMEDIATE"))
        db.refresh(delivery)
        if delivery.status != "uncertain":
            raise HTTPException(409, "Delivery already reconciled.")
        # The reconciliation timestamp is conservative; snapshots start from verification.
        complete(db, delivery, payload.remote_id)
        try:
            db.commit()
        except IntegrityError:
            raise HTTPException(
                409, "This remote post is already linked to another delivery."
            ) from None
        return {"status": "published"}


@router.post("/metrics/{sample_id}/retry")
def retry_sample(project_id: str, sample_id: str, request: Request):
    if not request.app.state.config.metrics_enabled:
        raise HTTPException(409, "Enable METRICS_ENABLED and restart first.")
    with Session(request.app.state.engine) as db:
        project_check(db, project_id, write=True)
        sample = db.get(MetricSample, sample_id)
        delivery = db.get(Delivery, sample.delivery_id) if sample else None
        if not delivery or delivery.project_id != project_id:
            raise HTTPException(404, "Sample not found.")
        if sample.status != "unavailable":
            raise HTTPException(409, "Only unavailable samples can be retried.")
        sample.status = "pending"
        sample.error = ""
        db.add(sample)
        db.commit()
        return {"status": "pending"}


class PreflightInput(BaseModel):
    revision: int = Field(ge=1)


@router.post("/{post_id}/preflight")
def preflight(project_id: str, post_id: str, payload: PreflightInput, request: Request):
    """Local validation only. Never calls a platform or changes publication state."""
    with Session(request.app.state.engine) as db:
        project_check(db, project_id, write=True)
        row = post_for(db, project_id, post_id)
        art = artwork_for(db, project_id, row.artwork_id)
        rendered = view(row, art)
        image_error = ""
        try:
            jpeg_for(request.app.state.config, art, row.platform)
        except HTTPException as exc:
            image_error = exc.detail
        checks = [
            {"label": "Current post version", "passed": row.revision == payload.revision},
            {"label": "Post approved for publication", "passed": row.status == "approved"},
            {
                "label": "Artwork approval and post content valid",
                "passed": not rendered["validation"]["errors"],
            },
            {
                "label": "Artwork file available",
                "passed": (
                    request.app.state.config.asset_dir / "artwork" / f"{art.digest}.png"
                ).is_file(),
            },
            {"label": "Publication image dimensions valid", "passed": not image_error},
        ]
        return {
            "mode": "dry_run",
            "post_id": row.id,
            "revision": row.revision,
            "platform": row.platform,
            "checks": checks,
            "errors": rendered["validation"]["errors"] + ([image_error] if image_error else []),
            "content_ready": all(c["passed"] for c in checks),
            "live_ready": False,
            "blockers": ["Connect and verify the destination account before live publishing."],
            "post_text": rendered["post_text"],
            "alt_text": row.alt_text,
            "message": "Local dry run only. No content was sent to a social platform.",
        }

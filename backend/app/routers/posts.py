import json
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func
from sqlmodel import Session, select

from app.creation_models import Artwork
from app.models import timestamp
from app.post_models import ApprovePost, DraftRequest, PostDraft, PostEdit, PublicationRecord
from app.post_service import gemini_draft, local_draft, view
from app.providers.runner import call_provider
from app.routers.creation import artwork_for, batch_for, prompt_for
from app.routers.discovery import operation, project_check

router = APIRouter(prefix="/api/characters/{project_id}", tags=["posts"])


def approved_art(db, project_id, artwork_id):
    art = artwork_for(db, project_id, artwork_id)
    if art.decision != "approved":
        raise HTTPException(409, "Approve this artwork in Image studio first.")
    return art


def post_for(db, project_id, post_id):
    row = db.get(PostDraft, post_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "Post version not found.")
    return row


def next_version(db, artwork_id):
    return (
        db.exec(select(func.max(PostDraft.version)).where(PostDraft.artwork_id == artwork_id)).one()
        or 0
    ) + 1


@router.get("/approved-artwork")
def approved_images(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        return db.exec(
            select(Artwork).where(Artwork.project_id == project_id, Artwork.decision == "approved")
        ).all()


@router.get("/posts")
def posts(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        rows = db.exec(
            select(PostDraft)
            .where(PostDraft.project_id == project_id)
            .order_by(PostDraft.created_at.desc())
        ).all()
        return [view(row, db.get(Artwork, row.artwork_id)) for row in rows]


@router.post("/posts")
async def create_post(project_id: str, payload: DraftRequest, request: Request):
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
            art = approved_art(db, project_id, payload.artwork_id)
            batch = batch_for(db, project_id, art.batch_id)
            prompt = prompt_for(db, project_id, batch.prompt_id)
            original = json.loads(prompt.context_json)
            context = {
                "identity": original["identity"],
                "style": json.loads(prompt.direction_json)["style"],
                "research": original.get("research"),
                "prompt_id": prompt.id,
                "artwork_digest": art.digest,
            }
            art_revision = art.revision
        if payload.provider == "gemini":
            config = request.app.state.config
            if not config.gemini_api_key or not config.gemini_captions_enabled:
                raise HTTPException(
                    409,
                    "Enable Gemini captions and configure a free-tier key locally, or use local templates.",
                )
            caption, tags = await call_provider(
                request.app.state.engine,
                "gemini",
                "captions",
                lambda: gemini_draft(config, context, payload.tone, payload.platform),
                timeout=90,
            )
        else:
            caption, tags = local_draft(context, payload.tone)
        with Session(request.app.state.engine) as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            project_check(db, project_id, write=True)
            art = approved_art(db, project_id, payload.artwork_id)
            if art.revision != art_revision:
                raise HTTPException(409, "Artwork review changed while drafting. Try again.")
            row = PostDraft(
                project_id=project_id,
                artwork_id=art.id,
                artwork_revision=art.revision,
                version=next_version(db, art.id),
                platform=payload.platform,
                tone=payload.tone,
                caption=caption,
                hashtags_json=json.dumps(tags),
                context_json=json.dumps(context),
                provider=payload.provider,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return view(row, art)


@router.post("/posts/{post_id}/versions")
def revise(project_id: str, post_id: str, payload: PostEdit, request: Request):
    with Session(request.app.state.engine) as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        project_check(db, project_id, write=True)
        old = post_for(db, project_id, post_id)
        if old.revision != payload.revision:
            raise HTTPException(409, "Post status changed in another tab. Reload first.")
        art = approved_art(db, project_id, old.artwork_id)
        row = PostDraft(
            project_id=project_id,
            artwork_id=art.id,
            artwork_revision=art.revision,
            version=next_version(db, art.id),
            platform=old.platform,
            tone=old.tone,
            caption=payload.caption,
            hashtags_json=json.dumps(payload.hashtags),
            alt_text=payload.alt_text,
            disclosure=payload.disclosure,
            context_json=old.context_json,
            provider="edited",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return view(row, art)


@router.post("/posts/{post_id}/approve")
def approve(project_id: str, post_id: str, payload: ApprovePost, request: Request):
    with Session(request.app.state.engine) as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        project_check(db, project_id, write=True)
        row = post_for(db, project_id, post_id)
        art = approved_art(db, project_id, row.artwork_id)
        if row.revision != payload.revision or row.status != "draft":
            raise HTTPException(409, "Post status changed. Reload before approving.")
        errors = view(row, art)["validation"]["errors"]
        if errors:
            raise HTTPException(422, " ".join(errors))
        row.status, row.approved_at = "approved", timestamp()
        row.revision += 1
        db.add(row)
        db.commit()
        db.refresh(row)
        return view(row, art)


@router.get("/posts/{post_id}/export")
def export(project_id: str, post_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        row = post_for(db, project_id, post_id)
        art = artwork_for(db, project_id, row.artwork_id)
        payload = view(row, art)
        if row.status not in ("approved", "published") or payload["validation"]["errors"]:
            raise HTTPException(
                409, "Export requires an approved, valid post and unchanged artwork approval."
            )
        path = request.app.state.config.asset_dir / "artwork" / f"{art.digest}.png"
        if not path.is_file():
            raise HTTPException(409, "Artwork file is missing. Restore your backup.")
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as pack:
            pack.write(path, "artwork.png")
            pack.writestr("caption.txt", payload["post_text"])
            pack.writestr("alt-text.txt", row.alt_text)
            pack.writestr("manifest.json", json.dumps(payload, ensure_ascii=False, indent=2))
            pack.writestr(
                "README.txt",
                "Manual posting pack. Nothing has been published by Variance.\nReview the crop and text in the native composer, add alt text and applicable AI disclosure, then publish yourself. Record the resulting URL and actual posting time in Variance.\nResearch evidence and source links are in manifest.json. Local validation is conservative and cannot guarantee platform acceptance.\n",
            )
        return Response(
            output.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="variance-post-{row.id[:8]}-v{row.version}.zip"'
            },
        )


@router.post("/posts/{post_id}/publication")
def record_publication(project_id: str, post_id: str, payload: PublicationRecord, request: Request):
    try:
        url = urlsplit(payload.url)
        posted = datetime.fromisoformat(payload.published_at.replace("Z", "+00:00"))
        if posted.tzinfo is None or posted > datetime.now(UTC):
            raise ValueError()
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.port not in (None, 443)
            or not url.path.strip("/")
        ):
            raise ValueError()
    except ValueError:
        raise HTTPException(
            422, "Enter an HTTPS post URL and a past posting time with timezone."
        ) from None
    with Session(request.app.state.engine) as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        project_check(db, project_id, write=True)
        row = post_for(db, project_id, post_id)
        if url.hostname not in {
            row.platform + ".com",
            "www." + row.platform + ".com",
            "m." + row.platform + ".com",
        }:
            raise HTTPException(422, "The URL must belong to the selected platform.")
        art = artwork_for(db, project_id, row.artwork_id)
        posted_at = posted.astimezone(UTC).isoformat()
        if (
            row.status == "published"
            and row.publication_url == payload.url
            and row.published_at == posted_at
        ):
            return view(row, art)
        if (
            row.status != "approved"
            or row.revision != payload.revision
            or view(row, art)["validation"]["errors"]
        ):
            raise HTTPException(
                409, "Record publication only for the current approved post version."
            )
        row.publication_url, row.published_at, row.status = payload.url, posted_at, "published"
        row.revision += 1
        db.add(row)
        db.commit()
        db.refresh(row)
        return view(row, art)

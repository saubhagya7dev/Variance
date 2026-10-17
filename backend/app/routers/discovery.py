import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.discovery_models import (
    ReferenceCandidate,
    ReferenceImage,
    ResearchBrief,
    ResearchSnapshot,
    SearchInput,
    SelectionInput,
)
from app.image_store import MAX_BYTES, download_image, normalize_image, store_image
from app.models import CharacterProject
from app.providers.discovery import commons_search, gemini_research, wikipedia_research
from app.providers.runner import call_provider

router = APIRouter(prefix="/api/characters/{project_id}", tags=["discovery"])


def project_check(db: Session, project_id: str, *, write: bool = False):
    project = db.get(CharacterProject, project_id)
    if not project:
        raise HTTPException(404, "Character project not found.")
    if write and project.archived:
        raise HTTPException(409, "Restore this project before changing its research or references.")
    return project


@asynccontextmanager
async def operation(request: Request, project_id: str):
    # One discovery mutation per project; bounded request lifetime, no invisible background job.
    busy = request.app.state.discovery_busy
    if project_id in busy:
        raise HTTPException(409, "A discovery operation is already running for this project.")
    busy.add(project_id)
    try:
        yield
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        message = (
            "Provider rate limit reached. Try again later."
            if status == 429
            else "Provider request failed. Check configuration and try again."
        )
        raise HTTPException(502, message) from exc
    except (httpx.HTTPError, OSError, TimeoutError) as exc:
        raise HTTPException(
            502, "The source could not be reached. Your saved work is unchanged; try again."
        ) from exc
    finally:
        busy.discard(project_id)


def snapshot_view(row: ResearchSnapshot):
    return {
        "id": row.id,
        "provider": row.provider,
        "created_at": row.created_at,
        "brief": ResearchBrief.model_validate_json(row.payload),
    }


@router.get("/research")
def research_history(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        rows = db.exec(
            select(ResearchSnapshot)
            .where(ResearchSnapshot.project_id == project_id)
            .order_by(ResearchSnapshot.created_at.desc())
            .limit(10)
        ).all()
        return [snapshot_view(row) for row in rows]


@router.post("/research")
async def research(project_id: str, request: Request):
    config = request.app.state.config
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project = project_check(db, project_id, write=True)
            identity = {key: getattr(project, key) for key in ("name", "franchise", "variant")}
        if config.research_provider == "gemini":
            if not config.gemini_api_key:
                raise HTTPException(
                    503,
                    "Set GEMINI_API_KEY in the local .env and restart, or use RESEARCH_PROVIDER=wikipedia.",
                )

            def provider_call():
                return gemini_research(identity, config.gemini_api_key, config.gemini_model)
        else:

            def provider_call():
                return wikipedia_research(identity)

        brief = await call_provider(
            request.app.state.engine,
            config.research_provider,
            "research",
            provider_call,
            timeout=90,
            retry_safe=False,
        )
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
            row = ResearchSnapshot(
                project_id=project_id,
                provider=config.research_provider,
                payload=brief.model_dump_json(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return snapshot_view(row)


@router.get("/candidates", response_model=list[ReferenceCandidate])
def candidates(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        return db.exec(
            select(ReferenceCandidate).where(ReferenceCandidate.project_id == project_id)
        ).all()


@router.post("/candidates", response_model=list[ReferenceCandidate])
async def search_references(project_id: str, payload: SearchInput, request: Request):
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project = project_check(db, project_id, write=True)
            query = payload.query.strip() or f"{project.name} {project.franchise}"
        rows = await call_provider(
            request.app.state.engine,
            "wikimedia",
            "image_search",
            lambda: commons_search(project_id, query),
            retry_safe=True,
        )
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
            db.execute(
                delete(ReferenceCandidate).where(ReferenceCandidate.project_id == project_id)
            )
            for row in rows:
                db.add(row)
            db.commit()
            for row in rows:
                db.refresh(row)
            return rows


def candidate_for(db: Session, project_id: str, candidate_id: str):
    row = db.get(ReferenceCandidate, candidate_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "Reference search result not found. Search again.")
    return row


@router.get("/candidates/{candidate_id}/thumbnail")
async def thumbnail(project_id: str, candidate_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        candidate = candidate_for(db, project_id, candidate_id)
        url = candidate.thumb_url
    try:
        async with request.app.state.image_slots:
            raw = await asyncio.to_thread(download_image, url)
            content, _, _ = await asyncio.to_thread(normalize_image, raw)
        return Response(content, media_type="image/png")
    except (ValueError, OSError, TimeoutError) as exc:
        raise HTTPException(502, "Preview unavailable. Open the source page instead.") from exc


def persist_reference(request: Request, project_id: str, raw: bytes, **metadata):
    digest, width, height = store_image(request.app.state.config.asset_dir, raw)
    with Session(request.app.state.engine) as db:
        project_check(db, project_id, write=True)
        existing = db.exec(
            select(ReferenceImage).where(
                ReferenceImage.project_id == project_id, ReferenceImage.digest == digest
            )
        ).first()
        if existing:
            existing.removed = False
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing
        if (
            len(
                db.exec(
                    select(ReferenceImage.id).where(
                        ReferenceImage.project_id == project_id, ReferenceImage.removed.is_(False)
                    )
                ).all()
            )
            >= 64
        ):
            raise HTTPException(409, "This project already has 64 references. Remove one first.")
        row = ReferenceImage(
            project_id=project_id, digest=digest, width=width, height=height, **metadata
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError as exc:
            raise HTTPException(
                409, "This reference was imported in another request. Refresh the list."
            ) from exc
        db.refresh(row)
        return row


@router.post("/candidates/{candidate_id}/import", response_model=ReferenceImage)
async def import_candidate(project_id: str, candidate_id: str, request: Request):
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
            row = candidate_for(db, project_id, candidate_id)
            metadata = {
                key: getattr(row, key)
                for key in ("title", "source_url", "page_url", "license", "attribution")
            }
        async with request.app.state.image_slots:
            raw = await asyncio.to_thread(download_image, metadata["source_url"])
            return await asyncio.to_thread(persist_reference, request, project_id, raw, **metadata)


@router.post("/references/upload", response_model=ReferenceImage)
async def upload(
    project_id: str, request: Request, title: str = Query("Uploaded reference", max_length=160)
):
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_BYTES:
                raise HTTPException(413, "Upload exceeds 8 MB.")
        async with request.app.state.image_slots:
            return await asyncio.to_thread(
                persist_reference, request, project_id, bytes(content), title=title
            )


@router.get("/references", response_model=list[ReferenceImage])
def references(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        return db.exec(
            select(ReferenceImage).where(
                ReferenceImage.project_id == project_id, ReferenceImage.removed.is_(False)
            )
        ).all()


def reference_for(db: Session, project_id: str, reference_id: str):
    row = db.get(ReferenceImage, reference_id)
    if not row or row.project_id != project_id or row.removed:
        raise HTTPException(404, "Reference not found.")
    return row


@router.get("/references/{reference_id}/image")
def reference_file(project_id: str, reference_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project_check(db, project_id)
        row = reference_for(db, project_id, reference_id)
        path = request.app.state.config.asset_dir / f"{row.digest}.png"
        if not path.is_file():
            raise HTTPException(404, "The stored image is missing. Reimport the reference.")
        return FileResponse(path, media_type="image/png")


@router.patch("/references/{reference_id}", response_model=ReferenceImage)
async def select_reference(
    project_id: str, reference_id: str, payload: SelectionInput, request: Request
):
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
            row = reference_for(db, project_id, reference_id)
            row.selected = payload.selected
            db.add(row)
            db.commit()
            db.refresh(row)
            return row


@router.delete("/references/{reference_id}")
async def remove_reference(project_id: str, reference_id: str, request: Request):
    async with operation(request, project_id):
        with Session(request.app.state.engine) as db:
            project_check(db, project_id, write=True)
            row = reference_for(db, project_id, reference_id)
            row.removed, row.selected = True, False
            db.add(row)
            db.commit()
        return {"removed": True}

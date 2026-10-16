from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import update
from sqlmodel import Session, select

from app.models import CharacterProject, timestamp
from app.schemas import ArchiveUpdate, CharacterCreate, CharacterUpdate

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("", response_model=list[CharacterProject])
def list_characters(request: Request, archived: bool = False, q: str = Query("", max_length=100)):
    with Session(request.app.state.engine) as db:
        query = select(CharacterProject).where(CharacterProject.archived == archived)
        if q.strip():
            query = query.where(CharacterProject.name.contains(q.strip(), autoescape=True))
        return db.exec(query.order_by(CharacterProject.updated_at.desc()).limit(100)).all()


@router.post("", response_model=CharacterProject, status_code=201)
def create_character(payload: CharacterCreate, request: Request):
    with Session(request.app.state.engine) as db:
        project = CharacterProject(**payload.model_dump(exclude={"fictional_confirmed"}))
        db.add(project)
        db.commit()
        db.refresh(project)
        return project


@router.get("/{project_id}", response_model=CharacterProject)
def get_character(project_id: str, request: Request):
    with Session(request.app.state.engine) as db:
        project = db.get(CharacterProject, project_id)
        if not project:
            raise HTTPException(404, "Character project not found.")
        return project


def update_project(project_id: str, payload: CharacterUpdate | ArchiveUpdate, request: Request):
    with Session(request.app.state.engine) as db:
        project = db.get(CharacterProject, project_id)
        if not project:
            raise HTTPException(404, "Character project not found.")
        if project.archived and isinstance(payload, CharacterUpdate):
            raise HTTPException(409, "Restore this project before editing it.")
        values = payload.model_dump(exclude={"revision"})
        values.update(revision=payload.revision + 1, updated_at=timestamp())
        result = db.execute(
            update(CharacterProject)
            .where(
                CharacterProject.id == project_id,
                CharacterProject.revision == payload.revision,
            )
            .values(**values)
        )
        if result.rowcount != 1:
            raise HTTPException(
                409, "This project changed in another tab. Reload the project before saving."
            )
        db.commit()
        db.refresh(project)
        return project


@router.patch("/{project_id}", response_model=CharacterProject)
def edit_character(project_id: str, payload: CharacterUpdate, request: Request):
    return update_project(project_id, payload, request)


@router.post("/{project_id}/archive", response_model=CharacterProject)
def archive_character(project_id: str, payload: ArchiveUpdate, request: Request):
    return update_project(project_id, payload, request)

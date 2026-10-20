from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.post_service import view
from app.routers.creation import artwork_for
from app.routers.discovery import project_check
from app.routers.posts import post_for

router = APIRouter(prefix="/api/characters/{project_id}/posts", tags=["publishing"])


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
        ]
        return {
            "mode": "dry_run",
            "post_id": row.id,
            "revision": row.revision,
            "platform": row.platform,
            "checks": checks,
            "errors": rendered["validation"]["errors"],
            "content_ready": all(c["passed"] for c in checks),
            "live_ready": False,
            "blockers": ["Connect and verify the destination account before live publishing."],
            "post_text": rendered["post_text"],
            "alt_text": row.alt_text,
            "message": "Local dry run only. No content was sent to Instagram or Facebook.",
        }

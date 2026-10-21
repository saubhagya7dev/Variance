import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.backup import create_backup

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("")
def status(request: Request):
    with request.app.state.engine.connect() as db:
        integrity = db.exec_driver_sql("PRAGMA quick_check").scalar() == "ok"
        uncertain = db.exec_driver_sql(
            "SELECT count(*) FROM deliveries WHERE status='uncertain'"
        ).scalar()
        pending = db.exec_driver_sql(
            "SELECT count(*) FROM metric_samples WHERE status='pending'"
        ).scalar()
        unavailable = db.exec_driver_sql(
            "SELECT count(*) FROM metric_samples WHERE status='unavailable'"
        ).scalar()
        calls = [
            dict(row)
            for row in db.exec_driver_sql(
                "SELECT provider, kind, status_code, outcome, created_at FROM provider_calls ORDER BY created_at DESC LIMIT 10"
            ).mappings()
        ]
    return {
        "database_ok": integrity,
        "uncertain_deliveries": uncertain,
        "pending_samples": pending,
        "unavailable_samples": unavailable,
        "publishing_enabled": request.app.state.config.publish_enabled,
        "metrics_enabled": request.app.state.config.metrics_enabled,
        "recent_calls": calls,
    }


@router.post("/backup")
def backup(request: Request):
    handle, name = tempfile.mkstemp(suffix=".zip", prefix="variance-")
    os.close(handle)
    path = Path(name)
    try:
        create_backup(request.app.state.engine, request.app.state.config.asset_dir, path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        message = (
            str(exc)
            if isinstance(exc, ValueError)
            else "Backup failed. Check storage and available disk space."
        )
        raise HTTPException(409, message) from None
    return FileResponse(
        path,
        media_type="application/zip",
        filename="variance-backup.zip",
        background=BackgroundTask(path.unlink, missing_ok=True),
    )

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import ROOT, Settings, settings
from app.db import make_engine, migrate
from app.routers.characters import router as characters_router
from app.routers.creation import router as creation_router
from app.routers.discovery import router as discovery_router


def create_app(config: Settings = settings) -> FastAPI:
    engine = make_engine(config.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        migrate(engine)
        yield
        engine.dispose()

    app = FastAPI(title="Variance Studio", version="0.2.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.config = config
    app.state.discovery_busy = set()
    app.state.image_slots = asyncio.Semaphore(4)
    app.include_router(characters_router)
    app.include_router(discovery_router)
    app.include_router(creation_router)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origins = {
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8765",
                "http://127.0.0.1:8765",
            }
            origin = request.headers.get("origin")
            if request.headers.get("x-variance-client") != "studio" or (
                origin and origin not in origins
            ):
                return JSONResponse(
                    {"detail": "Local workspace request required."}, status_code=403
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        with engine.connect() as db:
            db.exec_driver_sql("SELECT 1")
        return {"status": "ok", "version": "0.2.0", "mode": "local", "publishing_enabled": False}

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "phase": 3,
            "research": {
                "available": config.research_provider == "wikipedia" or bool(config.gemini_api_key),
                "configured": config.research_provider == "wikipedia"
                or bool(config.gemini_api_key),
                "provider": config.research_provider,
                "phase": 2,
            },
            "references": {
                "available": True,
                "configured": True,
                "provider": "wikimedia",
                "phase": 2,
            },
            "generation": {
                "available": False,
                "phase": 3,
                "provider": "manual",
                "manual_workflow": True,
            },
            "captions": {"available": False, "phase": 4},
            "publishing": {"available": False, "phase": 5},
            "metrics": {"available": False, "phase": 6},
        }

    frontend = ROOT / "frontend" / "dist"
    if (frontend / "assets").exists():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(frontend / "index.html")

    return app


app = create_app()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings, settings
from app.db import make_engine, migrate


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

    return app


app = create_app()

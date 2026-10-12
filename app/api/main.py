"""
FastAPI application for the PhotoBAse read-only web API.

Run:
    uvicorn app.api.main:app --host 127.0.0.1 --port 8000
or:
    python -m app.api.main

Database connection uses INGEST_DB_* (see docs/database_schema.md).
No authentication yet: intended for local development.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.config import API_HOST, API_PORT, CORS_ORIGINS
from app.api.routes import (
    auth_router,
    collections_router,
    jobs_router,
    originals_router,
    public_router,
    read_router,
    searches_router,
    uploads_router,
    users_router,
)

# Built SPA (frontend/dist). Served when present so production can run from a
# single process; the API keeps its own /api prefix.
SPA_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(
        title="PhotoBAse API",
        version="0.1.0",
        description=(
            "Read-only API over registered photos and their previews. "
            "Authentication is optional (SCENE_API_TOKENS); when unset the "
            "API is open for local development."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(public_router, prefix="/api")
    app.include_router(read_router, prefix="/api")
    app.include_router(originals_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(collections_router, prefix="/api")
    app.include_router(searches_router, prefix="/api")
    app.include_router(uploads_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")

    _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    """
    Serve the built SPA when frontend/dist exists.

    /api routes are registered before this, so they take precedence. Any
    other path falls back to index.html so client-side routing works.
    """

    if not SPA_DIST.is_dir():
        return

    assets = SPA_DIST / "assets"

    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        candidate = SPA_DIST / full_path

        if full_path and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(SPA_DIST / "index.html")


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()

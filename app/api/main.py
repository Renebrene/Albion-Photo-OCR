"""
FastAPI application for the PhotoBAse web API.

Run:
    uvicorn app.api.main:app --host 127.0.0.1 --port 8000
or:
    python -m app.api.main

Database connection uses INGEST_DB_* (see docs/database_schema.md).

Authentication is enforced by default (fail-closed): bearer tokens from
SCENE_API_TOKENS and user session tokens, each carrying scopes (see
app/api/auth.py). Set SCENE_AUTH_REQUIRED=0 only for trusted local development.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import validate_token_config
from app.api.compression import SelectiveGZipMiddleware
from app.api.cloud import (
    read_router as cloud_read_router,
    write_router as cloud_write_router,
)
from app.api.config import API_HOST, API_PORT, CORS_ORIGINS, ENABLE_DOCS
from app.api.videos import (
    originals_router as video_originals_router,
    public_router as video_public_router,
    playback_router as video_playback_router,
    read_router as video_read_router,
    write_router as video_write_router,
)
from app.api.backup import (
    read_router as backup_read_router,
    write_router as backup_write_router,
)
from app.api.routes import (
    addresses_router,
    auth_router,
    collections_router,
    fingerprints_router,
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
    # Fail fast on a malformed SCENE_API_TOKENS instead of weakening access
    # control silently at request time.
    validate_token_config()

    app = FastAPI(
        title="PhotoBAse API",
        version="0.1.0",
        description=(
            "API over registered photos and videos: metadata, previews, "
            "originals, search, collections, jobs and the user directory. "
            "Authentication is fail-closed; see app/api/auth.py for scopes."
        ),
        # Interactive docs are closed unless SCENE_ENABLE_DOCS=1: the schema
        # enumerates every route, and this API is reachable from a LAN and,
        # through a tunnel, from the internet.
        docs_url="/docs" if ENABLE_DOCS else None,
        redoc_url="/redoc" if ENABLE_DOCS else None,
        openapi_url="/openapi.json" if ENABLE_DOCS else None,
    )

    # Сжатие текстовых и JSON-ответов: бандлы сборки и ответы API. Видео,
    # превью и Range-запросы проходят мимо — по типу содержимого
    # (см. app/api/compression.py). SCENE_API_GZIP=0 выключает.
    app.add_middleware(SelectiveGZipMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _security_counters(request: Request, call_next):
        from app.api import security

        path = request.url.path

        try:
            if path.startswith("/api/"):
                ip = security.client_ip(request)

                # Ограничение частоты запросов выключено по умолчанию: одна
                # страница грида законно грузит сотни превью. Включается
                # SCENE_API_RATE_LIMIT, когда API открыт наружу.
                if path != "/api/health":
                    wait = security.note_request(ip)

                    if wait:
                        return JSONResponse(
                            status_code=429,
                            headers={"Retry-After": str(wait)},
                            content={"detail": "слишком много запросов"},
                        )

                security.record_request(ip, path)
        except Exception:  # noqa: BLE001 - counters must not break requests
            pass

        return await call_next(request)

    app.include_router(public_router, prefix="/api")
    app.include_router(read_router, prefix="/api")
    app.include_router(originals_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(collections_router, prefix="/api")
    app.include_router(searches_router, prefix="/api")
    app.include_router(addresses_router, prefix="/api")
    app.include_router(fingerprints_router, prefix="/api")
    app.include_router(uploads_router, prefix="/api")
    app.include_router(cloud_read_router, prefix="/api")
    app.include_router(cloud_write_router, prefix="/api")
    app.include_router(backup_read_router, prefix="/api")
    app.include_router(backup_write_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(video_public_router, prefix="/api")
    app.include_router(video_read_router, prefix="/api")
    app.include_router(video_originals_router, prefix="/api")
    app.include_router(video_write_router, prefix="/api")
    app.include_router(video_playback_router, prefix="/api")

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

    # GET and HEAD: `curl -I /` (and some clients) send HEAD.
    # Документация API: когда она выключена, эти адреса не должны
    # подменяться оболочкой SPA — иначе /docs отдавал бы HTML приложения
    # со статусом 200 и выглядел бы как открытая документация.
    docs_paths = ("docs", "redoc", "openapi.json")

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
    def spa_fallback(full_path: str):
        if not ENABLE_DOCS and full_path in docs_paths:
            raise HTTPException(status_code=404, detail="not found")

        candidate = SPA_DIST / full_path

        if full_path and candidate.is_file():
            return FileResponse(candidate)

        # index.html must not be cached: after a rebuild the hashed bundles
        # change, and a cached shell would keep asking for files that no longer
        # exist (a blank page — ровно так «не загружается» сайт после сборки).
        # `no-store` строже, чем `no-cache`: ни браузер, ни прокси не должны
        # держать копию оболочки. Сами бандлы содержат хеш в имени и кешируются
        # StaticFiles надолго.
        return FileResponse(
            SPA_DIST / "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )


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

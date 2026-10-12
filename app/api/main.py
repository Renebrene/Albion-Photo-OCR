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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import API_HOST, API_PORT, CORS_ORIGINS
from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="PhotoBAse API",
        version="0.1.0",
        description=(
            "Read-only API over registered photos and their previews. "
            "Authentication is not implemented in this slice."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    return app


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

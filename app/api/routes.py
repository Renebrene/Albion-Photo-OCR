"""
Read-only API endpoints.

Authentication is optional (see app/api/auth.py): when SCENE_API_TOKENS is
unset, everything is open for local development. Read endpoints require the
"read" scope; original files require the "originals" scope.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api import repository
from app.api.auth import require_scope
from app.api.config import PREVIEW_ROOT
from app.preview.generator import build_preview_paths

public_router = APIRouter()
read_router = APIRouter(dependencies=[Depends(require_scope("read"))])
originals_router = APIRouter()

PHOTO_ID_RE = re.compile(r"^PH_[0-9a-f]{24}$")

PREVIEW_SIZES = ("small", "middle")


def _validate_photo_id(photo_id: str) -> str:
    if not PHOTO_ID_RE.fullmatch(photo_id):
        # 404 (not 422) to avoid confirming whether an arbitrary id exists.
        raise HTTPException(status_code=404, detail="photo not found")
    return photo_id


@public_router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@read_router.get("/v1/photos", response_model=None)
def list_photos(
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=64),
    q: str | None = Query(None, max_length=256),
):
    items, next_cursor = repository.list_photos(
        limit=limit,
        cursor=cursor,
        query=q,
    )
    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
    }


@read_router.get("/v1/photos/{photo_id}", response_model=None)
def get_photo(photo_id: str):
    photo_id = _validate_photo_id(photo_id)
    photo = repository.get_photo(photo_id)

    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")

    return photo.model_dump()


@read_router.get("/v1/photos/{photo_id}/previews/{size}")
def get_preview(photo_id: str, size: str) -> Response:
    photo_id = _validate_photo_id(photo_id)

    if size not in PREVIEW_SIZES:
        raise HTTPException(status_code=404, detail="unknown preview size")

    # Path is built from photo_id, never from a client-supplied path.
    paths = build_preview_paths(
        preview_root=PREVIEW_ROOT,
        photo_id=photo_id,
    )
    path = paths.small if size == "small" else paths.middle

    if not path.is_file():
        raise HTTPException(status_code=404, detail="preview not found")

    return Response(
        content=path.read_bytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@originals_router.get(
    "/v1/photos/{photo_id}/original",
    dependencies=[Depends(require_scope("originals"))],
)
def get_original(photo_id: str) -> Response:
    photo_id = _validate_photo_id(photo_id)

    source = repository.get_photo_source(photo_id)

    if source is None:
        raise HTTPException(status_code=404, detail="photo not found")

    # Path comes from the database registration, never from the client.
    path = Path(source["source_path"])

    if not path.is_file():
        raise HTTPException(status_code=404, detail="original not found")

    return Response(
        content=path.read_bytes(),
        media_type="image/jpeg",
    )


@read_router.get("/v1/batches/dino", response_model=None)
def list_dino_batches(
    limit: int = Query(50, ge=1, le=100),
    cursor: int | None = Query(None, ge=1),
):
    items, next_cursor = repository.list_dino_batches(
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
    }


@read_router.get("/v1/batches/dino/{batch_id}", response_model=None)
def get_dino_batch(batch_id: int):
    batch = repository.get_dino_batch(batch_id)

    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    return batch.model_dump()


@read_router.get("/v1/batches/dino/{batch_id}/runs", response_model=None)
def list_dino_runs(
    batch_id: int,
    limit: int = Query(50, ge=1, le=100),
    cursor: int | None = Query(None, ge=1),
):
    if repository.get_dino_batch(batch_id) is None:
        raise HTTPException(status_code=404, detail="batch not found")

    items, next_cursor = repository.list_dino_runs(
        batch_id=batch_id,
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
    }


@read_router.get("/v1/hybrid/runs", response_model=None)
def list_hybrid_runs(
    limit: int = Query(50, ge=1, le=100),
    cursor: int | None = Query(None, ge=1),
):
    items, next_cursor = repository.list_hybrid_runs(
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
    }

"""
Read-only API endpoints.

No authentication in this first slice: intended for local development only.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Response

from app.api import repository
from app.api.config import PREVIEW_ROOT
from app.preview.generator import build_preview_paths

router = APIRouter()

PHOTO_ID_RE = re.compile(r"^PH_[0-9a-f]{24}$")

PREVIEW_SIZES = ("small", "middle")


def _validate_photo_id(photo_id: str) -> str:
    if not PHOTO_ID_RE.fullmatch(photo_id):
        # 404 (not 422) to avoid confirming whether an arbitrary id exists.
        raise HTTPException(status_code=404, detail="photo not found")
    return photo_id


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@router.get("/v1/photos", response_model=None)
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


@router.get("/v1/photos/{photo_id}", response_model=None)
def get_photo(photo_id: str):
    photo_id = _validate_photo_id(photo_id)
    photo = repository.get_photo(photo_id)

    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")

    return photo.model_dump()


@router.get("/v1/photos/{photo_id}/previews/{size}")
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

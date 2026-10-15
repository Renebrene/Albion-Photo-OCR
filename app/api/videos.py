"""API for durable video assets, kept separate from photo/DINO/QWEN routes."""

from __future__ import annotations

import mimetypes
import os
import re
from datetime import timezone
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.api import video_repository
from app.api.config import ORIGINALS_ROOTS, VIDEO_PREVIEW_ROOT
from app.api.file_access import allowed_media_path
from app.api.schemas import VideoSummary, VideoTitleUpdate
from app.api.auth import require_scope
from app.preview.video import VIDEO_ID_RE

read_router = APIRouter(dependencies=[Depends(require_scope("read"))])
playback_router = APIRouter(dependencies=[Depends(require_scope("videos:read"))])
write_router = APIRouter(dependencies=[Depends(require_scope("videos:write"))])
originals_router = APIRouter()
public_router = APIRouter()

CHUNK_BYTES = 1024 * 1024
TICKET_TTL_SECONDS = 300
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _video_id(video_id: str) -> str:
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise HTTPException(status_code=404, detail="video not found")
    return video_id


def _source(video_id: str) -> tuple[Path, dict]:
    row = video_repository.video_source(video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    if not ORIGINALS_ROOTS:
        raise HTTPException(status_code=503, detail="originals are not configured")
    path = allowed_media_path(row["source_path"], ORIGINALS_ROOTS)
    if path is None:
        raise HTTPException(status_code=404, detail="video source not found")
    return path, row


def _parse_range(value: str | None, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    match = RANGE_RE.fullmatch(value.strip())
    if not match:
        raise HTTPException(status_code=416, detail="invalid byte range", headers={"Content-Range": f"bytes */{size}"})
    first, last = match.groups()
    if not first and not last:
        raise HTTPException(status_code=416, detail="invalid byte range", headers={"Content-Range": f"bytes */{size}"})
    if not first:
        suffix = int(last)
        if suffix <= 0:
            raise HTTPException(status_code=416, detail="invalid byte range", headers={"Content-Range": f"bytes */{size}"})
        start, end = max(0, size - suffix), size - 1
    else:
        start = int(first)
        end = int(last) if last else size - 1
    if start >= size or end < start:
        raise HTTPException(status_code=416, detail="range not satisfiable", headers={"Content-Range": f"bytes */{size}"})
    return start, min(end, size - 1)


def _disposition(filename: str, action: str) -> str:
    fallback = re.sub(r"[^A-Za-z0-9._-]", "_", filename) or "video"
    return f"{action}; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


def _stream_file(path: Path, filename: str, action: str, range_header: str | None):
    size = path.stat().st_size
    if size <= 0:
        raise HTTPException(status_code=404, detail="video source not found")
    byte_range = _parse_range(range_header, size)
    start, end = byte_range if byte_range else (0, size - 1)
    length = end - start + 1
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    def chunks():
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = length
            while remaining:
                block = stream.read(min(CHUNK_BYTES, remaining))
                if not block:
                    break
                remaining -= len(block)
                yield block

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": _disposition(filename, action),
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    status = 200
    if byte_range:
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(chunks(), status_code=status, media_type=media_type, headers=headers)


def _cookie_name(video_id: str, action: str) -> str:
    return f"scene_video_{action}_{video_id}"


def _cookie_secure(request: Request) -> bool:
    configured = os.getenv("SCENE_COOKIE_SECURE")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes"}
    return request.url.scheme == "https"


def _issue_ticket(response: Response, request: Request, video_id: str, action: str) -> dict:
    path, _row = _source(video_id)
    try:
        token, expires = video_repository.issue_playback_ticket(video_id, action, ttl_seconds=TICKET_TTL_SECONDS)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="video not found") from exc

    # The opaque token is only in a path-scoped HttpOnly cookie, not in the URL,
    # JavaScript state, or access logs. Range requests from <video> reuse it.
    cookie_path = f"/api/v1/videos/{video_id}/{'stream' if action == 'inline' else 'download'}"
    response.set_cookie(
        key=_cookie_name(video_id, action),
        value=token,
        max_age=TICKET_TTL_SECONDS,
        expires=expires,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="strict",
        path=cookie_path,
    )
    suffix = "stream" if action == "inline" else "download"
    return {
        "url": f"/api/v1/videos/{video_id}/{suffix}",
        "expires_at": expires.astimezone(timezone.utc).isoformat(),
    }


@read_router.get("/v1/videos", response_model=None)
def list_videos(
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=64),
    q: str | None = Query(None, max_length=256),
    date_from: str | None = Query(None, max_length=10),
    date_to: str | None = Query(None, max_length=10),
    date_mode: str = Query("upload", pattern="^(upload|capture)$"),
):
    items, next_cursor = video_repository.list_videos(
        limit=limit, cursor=cursor, query=q,
        date_from=date_from, date_to=date_to, date_mode=date_mode,
    )
    return {"items": [VideoSummary(**item).model_dump() for item in items], "next_cursor": next_cursor}


@read_router.get("/v1/videos/{video_id}", response_model=None)
def get_video(video_id: str):
    row = video_repository.get_video(_video_id(video_id))
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    return VideoSummary(**row).model_dump()


@write_router.put("/v1/videos/{video_id}/title", response_model=None)
def update_video_title(video_id: str, request: VideoTitleUpdate):
    row = video_repository.update_display_title(_video_id(video_id), request.display_title)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    return VideoSummary(**row).model_dump()


@playback_router.post("/v1/videos/{video_id}/playback-ticket", response_model=None)
def playback_ticket(video_id: str, request: Request, response: Response):
    return _issue_ticket(response, request, _video_id(video_id), "inline")


@originals_router.post(
    "/v1/videos/{video_id}/download-ticket",
    dependencies=[Depends(require_scope("videos:download"))],
    response_model=None,
)
def download_ticket(video_id: str, request: Request, response: Response):
    return _issue_ticket(response, request, _video_id(video_id), "attachment")


@read_router.get("/v1/videos/{video_id}/poster", response_model=None)
def video_poster(video_id: str):
    video_id = _video_id(video_id)
    path = (VIDEO_PREVIEW_ROOT / f"{video_id}.jpg").resolve()
    root = VIDEO_PREVIEW_ROOT.resolve()
    if root != path.parent or not path.is_file():
        raise HTTPException(status_code=404, detail="video preview not found")
    return Response(path.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


def _request_ticket(request: Request, video_id: str, action: str) -> str | None:
    cookies = SimpleCookie()
    try:
        cookies.load(request.headers.get("cookie", ""))
    except Exception:  # noqa: BLE001 - malformed Cookie header is unauthorized
        return None
    morsel = cookies.get(_cookie_name(video_id, action))
    return morsel.value if morsel is not None else None


@public_router.get("/v1/videos/{video_id}/stream", include_in_schema=False)
def stream_video(
    video_id: str,
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
):
    video_id = _video_id(video_id)
    ticket = _request_ticket(request, video_id, "inline")
    if not ticket or not video_repository.validate_playback_ticket(video_id, ticket, "inline"):
        raise HTTPException(status_code=401, detail="playback ticket required or expired")
    path, row = _source(video_id)
    return _stream_file(path, row["filename"], "inline", range_header)


@public_router.get("/v1/videos/{video_id}/download", include_in_schema=False)
def download_video(
    video_id: str,
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
):
    video_id = _video_id(video_id)
    ticket = _request_ticket(request, video_id, "attachment")
    if not ticket or not video_repository.validate_playback_ticket(video_id, ticket, "attachment"):
        raise HTTPException(status_code=401, detail="download ticket required or expired")
    path, row = _source(video_id)
    return _stream_file(path, row["filename"], "attachment", range_header)


@read_router.get("/v1/media/statistics", response_model=None)
def media_statistics():
    return video_repository.media_statistics()

"""API for durable video assets, kept separate from photo/DINO/QWEN routes."""

from __future__ import annotations

import mimetypes
import os
import re
from datetime import date as date_type
from datetime import timezone
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.api import video_repository
from app.api.config import ORIGINALS_ROOTS, VIDEO_DERIVATIVES_ROOT, VIDEO_PREVIEW_ROOT, VIDEO_STORYBOARD_ROOT
from app.api.file_access import allowed_media_path
from app.api.schemas import VideoSummary, VideoTitleUpdate, VideoTranscodeRequest, VideoTrimRequest
from app.api.auth import require_scope
from app.preview.video import VIDEO_ID_RE
from app.video.profiles import PROFILES
from app.video.transcode import derivatives_root

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


def _date_params(
    date_from: date_type | None,
    date_to: date_type | None,
) -> tuple[str | None, str | None]:
    """ISO dates for SQL; an inverted range is swapped (photos do the same)."""

    start = date_from.isoformat() if date_from else None
    end = date_to.isoformat() if date_to else None

    if start and end and start > end:
        start, end = end, start

    return start, end


def _source(video_id: str) -> tuple[Path, dict]:
    row = video_repository.video_source(video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    allowed_roots = [*ORIGINALS_ROOTS, VIDEO_DERIVATIVES_ROOT]
    if not ORIGINALS_ROOTS and not VIDEO_DERIVATIVES_ROOT.is_dir():
        raise HTTPException(status_code=503, detail="originals are not configured")
    path = allowed_media_path(row["source_path"], allowed_roots)
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
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    date_mode: str = Query("upload", pattern="^(upload|capture)$"),
):
    date_from, date_to = _date_params(date_from, date_to)
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


@write_router.post("/v1/videos/{video_id}/transcodes", status_code=202, response_model=None)
def enqueue_video_transcode(video_id: str, request: VideoTranscodeRequest):
    video_id = _video_id(video_id)
    try:
        result = video_repository.enqueue_transcode(video_id, request.profile)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="video not found")
    return {**result, "profile": request.profile, "profile_label": PROFILES[request.profile]["label"]}


@write_router.post("/v1/videos/{video_id}/storyboard", status_code=202, response_model=None)
def enqueue_video_storyboard(video_id: str):
    video_id = _video_id(video_id)
    result = video_repository.enqueue_storyboard(video_id)
    if result is None:
        raise HTTPException(status_code=404, detail="video not found")
    return {**result, "frame_count": 8}


@playback_router.get("/v1/videos/{video_id}/storyboard/{frame_index}", response_model=None)
def get_video_storyboard_frame(video_id: str, frame_index: int):
    video_id = _video_id(video_id)
    if not 0 <= frame_index < 8:
        raise HTTPException(status_code=404, detail="storyboard frame not found")
    row = video_repository.video_source(video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    if not video_repository.storyboard_ready(video_id, row["sha256"]):
        raise HTTPException(status_code=404, detail="storyboard frame not found")
    from app.video.transcode import _valid_storyboard_frame, storyboard_frame_path

    raw_path = storyboard_frame_path(video_id, row["sha256"], frame_index)
    root = VIDEO_STORYBOARD_ROOT.expanduser().resolve()
    if not _valid_storyboard_frame(raw_path, root):
        raise HTTPException(status_code=404, detail="storyboard frame not found")
    path = raw_path.resolve()
    if root not in path.parents:
        raise HTTPException(status_code=404, detail="storyboard frame not found")
    return Response(path.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


@write_router.post("/v1/videos/{video_id}/trim", status_code=202, response_model=None)
def enqueue_video_trim(video_id: str, request: VideoTrimRequest):
    video_id = _video_id(video_id)
    try:
        result = video_repository.enqueue_trim(video_id, request.start_seconds, request.end_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="video not found")
    return result


@read_router.get("/v1/videos/{video_id}/trim", response_model=None)
def get_video_trim(video_id: str, start_seconds: float = Query(ge=0), end_seconds: float = Query(gt=0)):
    video_id = _video_id(video_id)
    try:
        result = video_repository.trim_state(video_id, start_seconds, end_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="trim derivative not found")
    return result


@read_router.get("/v1/videos/{video_id}/transcodes/{profile}", response_model=None)
def get_video_transcode(video_id: str, profile: str):
    video_id = _video_id(video_id)
    if profile not in PROFILES:
        raise HTTPException(status_code=404, detail="video derivative not found")
    result = video_repository.transcode_state(video_id, profile)
    if result is None:
        raise HTTPException(status_code=404, detail="video derivative not found")
    return {**result, "profile": profile, "profile_label": PROFILES[profile]["label"]}


@originals_router.post(
    "/v1/videos/{video_id}/derivatives/{derivative_id}/download-ticket",
    dependencies=[Depends(require_scope("videos:download"))],
    response_model=None,
)
def derivative_id_download_ticket(video_id: str, derivative_id: int, request: Request, response: Response):
    video_id = _video_id(video_id)
    try:
        token, expires = video_repository.issue_playback_ticket(
            video_id, "derivative_attachment", derivative_id=derivative_id,
            ttl_seconds=TICKET_TTL_SECONDS,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="video derivative not found") from exc
    cookie_path = f"/api/v1/videos/{video_id}/derivatives/{derivative_id}/download"
    response.set_cookie(
        key=_cookie_name(video_id, "derivative_attachment"), value=token,
        max_age=TICKET_TTL_SECONDS, expires=expires, httponly=True,
        secure=_cookie_secure(request), samesite="strict", path=cookie_path,
    )
    return {"url": cookie_path, "expires_at": expires.astimezone(timezone.utc).isoformat()}


@originals_router.post(
    "/v1/videos/{video_id}/transcodes/{profile}/download-ticket",
    dependencies=[Depends(require_scope("videos:download"))],
    response_model=None,
)
def derivative_download_ticket(video_id: str, profile: str, request: Request, response: Response):
    video_id = _video_id(video_id)
    if profile not in PROFILES:
        raise HTTPException(status_code=404, detail="video derivative not found")
    state = video_repository.transcode_state(video_id, profile)
    if state is None or state["status"] != "DONE":
        raise HTTPException(status_code=409, detail="video derivative is not ready")
    derivative_id = state["derivative_id"]
    try:
        token, expires = video_repository.issue_playback_ticket(
            video_id, "derivative_attachment", derivative_id=derivative_id,
            ttl_seconds=TICKET_TTL_SECONDS,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="video derivative not found") from exc
    cookie_path = f"/api/v1/videos/{video_id}/derivatives/{derivative_id}/download"
    response.set_cookie(
        key=_cookie_name(video_id, "derivative_attachment"),
        value=token,
        max_age=TICKET_TTL_SECONDS,
        expires=expires,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="strict",
        path=cookie_path,
    )
    return {"url": cookie_path, "expires_at": expires.astimezone(timezone.utc).isoformat()}


@public_router.get("/v1/videos/{video_id}/derivatives/{derivative_id}/download", include_in_schema=False)
def download_video_derivative(
    video_id: str,
    derivative_id: int,
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
):
    video_id = _video_id(video_id)
    ticket = _request_ticket(request, video_id, "derivative_attachment")
    if not ticket or not video_repository.validate_playback_ticket(
        video_id, ticket, "derivative_attachment", derivative_id=derivative_id
    ):
        raise HTTPException(status_code=401, detail="download ticket required or expired")
    output = video_repository.derivative_source(video_id, derivative_id)
    if output is None:
        raise HTTPException(status_code=404, detail="video derivative not found")
    path = allowed_media_path(output["source_path"], [derivatives_root()])
    if path is None:
        raise HTTPException(status_code=404, detail="video derivative not found")
    filename = f"{video_id}_{derivative_id}.mp4"
    return _stream_file(path, filename, "attachment", range_header)


@read_router.get("/v1/media/statistics", response_model=None)
def media_statistics():
    return video_repository.media_statistics()

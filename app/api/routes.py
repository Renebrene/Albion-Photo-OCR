"""
Read-only API endpoints.

Authentication is optional (see app/api/auth.py): when SCENE_API_TOKENS is
unset, everything is open for local development. Read endpoints require the
"read" scope; original files require the "originals" scope.
"""

from __future__ import annotations

import json
import os
import re
import uuid
import shutil
import subprocess
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse

from app import settings_store
from app.api import directory as directory_mod
from app.api import fingerprints as fingerprints_mod
from app.api import file_access
from app.api import repository
from app.api import archive as archive_mod
from app.api import data as data_mod
from app.api import media_search
from app.api import sources
from app.api import system as sysinfo
from app.api import upload as upload_mod
from app.api.auth import auth_enabled, require_scope, resolve_principal
from app.api.config import ORIGINALS_ROOTS, PREVIEW_ROOT, SOURCE_ROOTS
from app.ingest.integrity import SUPPORTED_EXTENSIONS
from app.core.errors import redact_paths
from app.api.schemas import (
    AddressCreate,
    AddressFingerprintsRequest,
    AddressUpdate,
    ArchiveRequest,
    AutomationUpdate,
    ClientAliasRequest,
    CollectionCreate,
    CollectionMembersRequest,
    DinoBatchRequest,
    FingerprintAddressRequest,
    FingerprintBatchRequest,
    FingerprintBuildRequest,
    FingerprintUpdate,
    HybridRequest,
    LoginRequest,
    NlSearchRequest,
    QwenJobRequest,
    QwenModelRequest,
    QwenSettingsUpdate,
    SavedSearchCreate,
    PipelineStartRequest,
    SourcePathRequest,
    SourceRunRequest,
    SelectionState,
    UserCreate,
    UserUpdate,
)
from app.qwen import processor as qwen
from app.qwen import database as qwen_db
from app.users import database as users_db
from app.users.security import has_password, verify_password
from app.dino import database as dino_db
from app.hybrid import database as hybrid_db
from app.jobs import automation
from app.jobs import database as jobs_db
from app.preview.generator import build_preview_paths

public_router = APIRouter()
read_router = APIRouter(dependencies=[Depends(require_scope("read"))])
originals_router = APIRouter()
jobs_router = APIRouter()
collections_router = APIRouter()
searches_router = APIRouter()
addresses_router = APIRouter()
fingerprints_router = APIRouter()
uploads_router = APIRouter()
auth_router = APIRouter()
users_router = APIRouter()

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
    address: list[str] | None = Query(None, max_length=64),
    client: list[str] | None = Query(None, max_length=64),
    date_from: str | None = Query(None, max_length=10),
    date_to: str | None = Query(None, max_length=10),
    date_mode: str = Query("upload", pattern="^(upload|capture)$"),
    collection_id: int | None = Query(None, ge=1),
    ids: list[str] | None = Query(None, max_length=200),
):
    items, next_cursor = repository.list_photos(
        limit=limit,
        cursor=cursor,
        query=q,
        addresses=address,
        clients=client,
        date_from=date_from,
        date_to=date_to,
        date_mode=date_mode,
        collection_id=collection_id,
        ids=ids,
    )
    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
    }


@read_router.get("/v1/stats", response_model=None)
def get_stats():
    """Counts for the status bar: photos, addresses, clients, last upload."""

    return repository.stats()


@read_router.get("/v1/system", response_model=None)
def get_system_info():
    return sysinfo.system_info()


@read_router.get("/v1/fingerprints", response_model=None)
def list_fingerprints():
    return {"items": sysinfo.list_fingerprints()}


@read_router.get("/v1/runs/last", response_model=None)
def get_last_run():
    return sysinfo.last_run()


@read_router.get("/v1/data/storage", response_model=None)
def data_storage():
    return data_mod.storage_stats()


@read_router.get("/v1/data/export", response_model=None)
def data_export(format: str = Query("json", pattern=r"^(json|csv)$")):
    """Export photo + QWEN metadata (no absolute paths)."""

    rows = data_mod.export_rows()

    if format == "csv":
        return Response(
            content=data_mod.to_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=photos.csv"
            },
        )

    return {"items": rows, "count": len(rows)}


@read_router.get("/v1/addresses", response_model=None)
def list_addresses(limit: int = Query(1000, ge=1, le=5000)):
    return {"items": repository.list_addresses(limit=limit)}


@read_router.get("/v1/clients", response_model=None)
def list_clients(limit: int = Query(1000, ge=1, le=5000)):
    return {"items": repository.list_clients(limit=limit)}


@read_router.get("/v1/photos/{photo_id}", response_model=None)
def get_photo(photo_id: str):
    photo_id = _validate_photo_id(photo_id)
    photo = repository.get_photo(photo_id)

    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")

    return photo.model_dump()


@read_router.get("/v1/photos/{photo_id}/details", response_model=None)
def get_photo_details(photo_id: str):
    """Registered photo plus its QWEN metadata (brand/category/objects/...)."""

    photo_id = _validate_photo_id(photo_id)
    photo = repository.get_photo(photo_id)

    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")

    qwen_meta = qwen_db.get(photo_id)

    if qwen_meta is not None and qwen_meta.get("error_message"):
        # Keep the message but drop any absolute local path in it.
        source = repository.get_photo_source(photo_id)
        qwen_meta["error_message"] = redact_paths(
            qwen_meta["error_message"],
            source["source_path"] if source else None,
        )

    return {"photo": photo.model_dump(), "qwen": qwen_meta}


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


def _allowed_original_path(source_path: str) -> Path | None:
    """Shared fail-closed check used by photo archive/download routes."""

    return file_access.allowed_media_path(source_path, ORIGINALS_ROOTS)


@originals_router.get(
    "/v1/photos/{photo_id}/original",
    dependencies=[Depends(require_scope("originals"))],
)
def get_original(photo_id: str) -> Response:
    photo_id = _validate_photo_id(photo_id)

    # Path comes from the database registration, never from the client.
    if not ORIGINALS_ROOTS:
        raise HTTPException(
            status_code=503,
            detail="originals are not configured (SCENE_ORIGINALS_ROOTS)",
        )

    source = repository.get_photo_source(photo_id)

    if source is None:
        raise HTTPException(status_code=404, detail="photo not found")

    resolved = _allowed_original_path(source["source_path"])

    if resolved is None:
        # 404 (not 403) so we do not confirm a file exists outside the volume.
        raise HTTPException(status_code=404, detail="original not found")

    # Stream from disk (chunked, supports single byte-ranges) instead of
    # reading the whole original into memory: large photos and several
    # concurrent downloads must not spike the API process RSS.
    return FileResponse(
        resolved,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


@originals_router.post(
    "/v1/photos/archive",
    dependencies=[Depends(require_scope("originals"))],
)
def download_archive(request: ArchiveRequest):
    """
    ZIP of the selected photos, assembled on the server.

    The window sends, for each photo, the name it would use when downloading it
    alone (original name or "<address>__<name>"); names are sanitised here so an
    entry can never escape the extraction folder. Files themselves are read from
    the registered source paths inside the allowed roots, as for a single
    download - nothing comes from the request but the ids and the labels.
    """

    if not request.items:
        raise HTTPException(status_code=400, detail="выбор пуст")

    if len(request.items) > archive_mod.MAX_ITEMS:
        raise HTTPException(
            status_code=413,
            detail=f"в одном архиве не больше {archive_mod.MAX_ITEMS} файлов",
        )

    if not ORIGINALS_ROOTS:
        raise HTTPException(
            status_code=503,
            detail="originals are not configured (SCENE_ORIGINALS_ROOTS)",
        )

    wanted: list[str] = []

    for item in request.items:
        try:
            wanted.append(_validate_photo_id(item.photo_id))
        except HTTPException:
            # A malformed id never comes from the window; skip it instead of
            # failing the whole archive.
            continue

    if not wanted:
        raise HTTPException(status_code=404, detail="подходящих файлов не найдено")

    sources = repository.photo_sources(wanted)

    entries: list[tuple[Path, str]] = []

    for item in request.items:
        source = sources.get(item.photo_id)

        if source is None:
            continue

        path = _allowed_original_path(source["source_path"])

        if path is None:
            continue

        name = archive_mod.safe_archive_name(
            item.name,
            source.get("filename") or f"{item.photo_id}.jpg",
        )

        entries.append((path, name))

    if not entries:
        raise HTTPException(status_code=404, detail="подходящих файлов не найдено")

    try:
        buffer, _total = archive_mod.build_archive(entries)
    except archive_mod.ArchiveError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="photobase.zip"',
            # Built per request, possibly large: never cached.
            "Cache-Control": "no-store",
        },
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


# ---------------------------------------------------------------------------
# Job queue: create a batch/run and enqueue deferred processing.
# Inference runs in app.jobs.worker, never here.
# ---------------------------------------------------------------------------


@jobs_router.post(
    "/v1/jobs/dino-batch",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def enqueue_dino_batch(request: DinoBatchRequest):
    if request.run_type == "FORCE_RERUN" and not request.photo_ids:
        raise HTTPException(
            status_code=422,
            detail="FORCE_RERUN requires photo_ids",
        )

    try:
        batch = dino_db.create_batch(
            request.run_type,
            request.photo_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job_id = None

    if batch.total_count > 0:
        job_id = jobs_db.enqueue(
            "DINO_BATCH",
            {"batch_id": batch.batch_id},
        )

    return {
        "job_id": job_id,
        "batch_id": batch.batch_id,
        "batch_status": batch.status,
        "total_count": batch.total_count,
    }


@jobs_router.post(
    "/v1/jobs/hybrid",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def enqueue_hybrid(request: HybridRequest):
    try:
        run = hybrid_db.create_run(request.dino_batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    job_id = None

    if run.total_count > 0:
        job_id = jobs_db.enqueue(
            "HYBRID_RUN",
            {"hybrid_run_id": run.hybrid_run_id},
        )

    return {
        "job_id": job_id,
        "hybrid_run_id": run.hybrid_run_id,
        "status": run.status,
        "total_count": run.total_count,
    }


@jobs_router.post(
    "/v1/jobs/qwen",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def enqueue_qwen(request: QwenJobRequest):
    if request.only_failed:
        photo_ids = repository.photo_ids_with_qwen_status("FAILED")
    else:
        photo_ids = request.photo_ids or repository.all_photo_ids()

    if request.photo_ids:
        invalid = [
            value
            for value in request.photo_ids
            if not PHOTO_ID_RE.fullmatch(value)
        ]

        if invalid:
            raise HTTPException(
                status_code=422,
                detail=(
                    "invalid photo_id(s): "
                    + ", ".join(invalid[:5])
                ),
            )

    if not photo_ids:
        raise HTTPException(
            status_code=422,
            detail="no photos to process",
        )

    job_ids = []
    skipped = 0

    for photo_id in photo_ids:
        # Deduplicated: a photo with an active QWEN job is skipped.
        job_id = jobs_db.enqueue_qwen(photo_id)

        if job_id is None:
            skipped += 1
        else:
            job_ids.append(job_id)

    return {
        "jobs": len(job_ids),
        "skipped": skipped,
        "first_job_id": job_ids[0] if job_ids else None,
    }


@jobs_router.post(
    "/v1/jobs/nl-search",
    status_code=202,
    dependencies=[Depends(require_scope("read"))],
)
def enqueue_nl_search(request: NlSearchRequest):
    """
    Enqueue a natural-language search.

    The QWEN translation runs in the worker; poll GET /v1/jobs/{id} for the
    result ({filters, photo_ids, count}).
    """

    job_id = jobs_db.enqueue("NL_SEARCH", {"query": request.query})
    return {"job_id": job_id}


@jobs_router.get(
    "/v1/jobs/nl-search/{job_id}",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_nl_search(job_id: int):
    """Return an NL-search job (status + result) readable with just `read`."""

    job = jobs_db.get_job(job_id)

    if job is None or job.get("job_type") != "NL_SEARCH":
        raise HTTPException(status_code=404, detail="nl search not found")

    return job


@jobs_router.get(
    "/v1/jobs",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:read"))],
)
def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    cursor: int | None = Query(None, ge=1),
):
    items, next_cursor = jobs_db.list_jobs(limit=limit, cursor=cursor)
    return {"items": items, "next_cursor": next_cursor}


@jobs_router.post(
    "/v1/jobs/requeue-stale",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def requeue_stale_jobs(
    older_than_minutes: int = Query(30, ge=0, le=10080),
):
    """
    Recover stale work: queue jobs plus their DINO runs / HYBRID runs.

    Queue recovery alone leaves a crashed run stuck in RUNNING, which would
    block its batch forever.
    """

    return {
        "jobs": jobs_db.requeue_stale(
            older_than_minutes=older_than_minutes
        ),
        "dino_runs": dino_db.requeue_stale_runs(
            older_than_minutes=older_than_minutes
        ),
        "hybrid_runs": hybrid_db.requeue_stale_runs(
            older_than_minutes=older_than_minutes
        ),
    }


@jobs_router.get(
    "/v1/jobs/{job_id}",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:read"))],
)
def get_job(job_id: int):
    job = jobs_db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    return job


@jobs_router.post(
    "/v1/jobs/{job_id}/pause",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def pause_job(job_id: int):
    """
    Hold a job.

    A PENDING job is not claimed while it is held; one that is already RUNNING
    notices between batches and waits. The wait is bounded by the worker
    (SCENE_PAUSE_MAX_SECONDS), after which the job fails rather than blocking
    the queue forever.
    """

    job = jobs_db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    if job["job_type"] in {"VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD", "PHOTO_PREVIEW"}:
        raise HTTPException(
            status_code=409,
            detail="this job cannot be paused; cancel it instead",
        )

    if not jobs_db.mark_paused(job_id):
        raise HTTPException(
            status_code=409,
            detail="job is not pending or running",
        )

    return {"job_id": job_id, "status": "PAUSED"}


@jobs_router.post(
    "/v1/jobs/{job_id}/resume",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def resume_job(job_id: int):
    """Release a held job back to the worker."""

    job = jobs_db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    if not jobs_db.mark_resumed(job_id):
        raise HTTPException(status_code=409, detail="job is not paused")

    return {"job_id": job_id, "status": jobs_db.job_status(job_id)}


@jobs_router.post(
    "/v1/jobs/{job_id}/cancel",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def cancel_job(job_id: int):
    """
    Cancel a queued job (and mark a running one cancelled).

    A job that is still PENDING is never claimed by the worker. One that is
    already RUNNING cannot be interrupted mid-step, but its result is
    discarded: mark_done() refuses to publish into a cancelled row. A queued
    media search drops its uploaded image here, because the worker that would
    normally delete it never runs.

    Unknown job -> 404; a job that already finished -> 409.
    """

    job = jobs_db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    was_queued = job.get("status") == "PENDING"

    if not jobs_db.mark_cancelled(job_id):
        raise HTTPException(
            status_code=409,
            detail="job is not pending or running",
        )

    # A media search cancelled while it was still queued never reaches the
    # worker, so the worker cannot delete the uploaded image: do it here.
    if was_queued and job.get("job_type") == "MEDIA_SEARCH":
        media_search.discard_query_file((job.get("payload") or {}).get("path"))

    return {"job_id": job_id, "status": "CANCELLED"}


# ---------------------------------------------------------------------------
# Smart search by an uploaded photo (transient: the file is deleted by the
# worker once the job finishes)
# ---------------------------------------------------------------------------


@searches_router.post(
    "/v1/search/media",
    status_code=202,
    dependencies=[Depends(require_scope("searches:write"))],
)
def search_by_media(file: UploadFile = File(...)):
    """
    Enqueue a search by one uploaded photo or video.

    The file is stored in a dedicated working folder, verified with a real
    decoder (PIL for photos, OpenCV for video) and dropped when it is neither.
    A video longer than the query limit is refused here, with the reason.
    The QWEN description and the photo search run in the worker
    (job_type MEDIA_SEARCH); poll GET /v1/jobs/media-search/{id} for
    {qwen, filters, photo_ids, count, per_frame}.

    The response carries the file's facts so the window can show them before
    the search starts (format, size, and for a video - duration and frames).
    """

    kind = media_search.kind_for(file.filename or "")

    limit = (
        media_search.MAX_VIDEO_BYTES
        if kind == "video"
        else media_search.MAX_FILE_BYTES
    )

    try:
        stored = media_search.store_query(
            file.filename,
            file.file,
            max_bytes=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        facts = media_search.verify_media(stored)
    except ValueError as exc:
        media_search.delete_query(stored)

        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = jobs_db.enqueue(
        "MEDIA_SEARCH",
        {
            "path": str(stored),
            "filename": stored.name,
            "kind": kind,
        },
    )

    return {
        "job_id": job_id,
        "kind": kind,
        "filename": file.filename or stored.name,
        "size_bytes": stored.stat().st_size,
        "media": facts,
    }


@searches_router.get(
    "/v1/jobs/media-search/{job_id}",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_media_search(job_id: int):
    """Return a media-search job (status + result), readable with `read`."""

    job = jobs_db.get_job(job_id)

    if job is None or job.get("job_type") != "MEDIA_SEARCH":
        raise HTTPException(status_code=404, detail="media search not found")

    return job


# ---------------------------------------------------------------------------
# Upload → INGEST (bounded, decoder-validated)
# ---------------------------------------------------------------------------


@uploads_router.post(
    "/v1/upload",
    status_code=201,
    dependencies=[Depends(require_scope("upload:write"))],
)
def upload_photos(files: list[UploadFile] = File(...)):
    """Store and register uploaded JPEGs through the INGEST pipeline."""

    if not files:
        raise HTTPException(status_code=422, detail="no files provided")

    if len(files) > upload_mod.MAX_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"too many files (max {upload_mod.MAX_FILES})",
        )

    results = [
        upload_mod.ingest_upload(item.filename, item.file) for item in files
    ]

    return {
        "items": results,
        "accepted": sum(1 for item in results if "photo_id" in item),
    }


# ---------------------------------------------------------------------------
# Automation scheduler (settings + one manual tick)
# ---------------------------------------------------------------------------


@read_router.get("/v1/automation", response_model=None)
def get_automation():
    return automation.get_settings()


@jobs_router.put(
    "/v1/automation",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def update_automation(request: AutomationUpdate):
    return automation.update_settings(
        enabled=request.enabled,
        interval_minutes=request.interval_minutes,
        auto_dino=request.auto_dino,
        auto_qwen=request.auto_qwen,
    )


@jobs_router.post(
    "/v1/automation/run",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def run_automation(force: bool = Query(False)):
    """Run one scheduler tick now (force ignores enabled/interval)."""

    return automation.run_tick(force=force)


# ---------------------------------------------------------------------------
# Collections / bookmarks
# ---------------------------------------------------------------------------


@read_router.get("/v1/collections", response_model=None)
def list_collections():
    return {"items": repository.list_collections()}


@read_router.get("/v1/collections/{collection_id}/members", response_model=None)
def list_collection_members(
    collection_id: int,
    member_type: str = Query("photo", pattern=r"^(address|client|photo)$"),
):
    if repository.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")

    return {
        "items": repository.collection_member_values(
            collection_id, member_type
        )
    }


@collections_router.post(
    "/v1/collections",
    status_code=201,
    dependencies=[Depends(require_scope("collections:write"))],
)
def create_collection(request: CollectionCreate):
    return repository.create_collection(
        name=request.name,
        kind=request.kind,
        client=request.client,
        scope=request.scope,
    )


@collections_router.delete(
    "/v1/collections/{collection_id}",
    dependencies=[Depends(require_scope("collections:write"))],
)
def delete_collection(collection_id: int):
    if not repository.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="collection not found")

    return {"deleted": collection_id}


@collections_router.post(
    "/v1/collections/{collection_id}/members",
    dependencies=[Depends(require_scope("collections:write"))],
)
def add_collection_members(
    collection_id: int,
    request: CollectionMembersRequest,
):
    if repository.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")

    added = repository.add_collection_members(
        collection_id,
        member_type=request.member_type,
        values=request.values,
    )

    return {"collection_id": collection_id, "added": added}


@collections_router.post(
    "/v1/collections/{collection_id}/members/remove",
    dependencies=[Depends(require_scope("collections:write"))],
)
def remove_collection_members(
    collection_id: int,
    request: CollectionMembersRequest,
):
    if repository.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="collection not found")

    removed = repository.remove_collection_members(
        collection_id,
        member_type=request.member_type,
        values=request.values,
    )

    return {"collection_id": collection_id, "removed": removed}


# ---------------------------------------------------------------------------
# Saved searches (bookmarked GRID filters)
# ---------------------------------------------------------------------------


@read_router.get("/v1/searches", response_model=None)
def list_saved_searches():
    return {"items": repository.list_saved_searches()}


@searches_router.post(
    "/v1/searches",
    status_code=201,
    dependencies=[Depends(require_scope("searches:write"))],
)
def create_saved_search(request: SavedSearchCreate):
    return repository.create_saved_search(
        name=request.name,
        filters=request.filters,
    )


@searches_router.delete(
    "/v1/searches/{search_id}",
    dependencies=[Depends(require_scope("searches:write"))],
)
def delete_saved_search(search_id: int):
    if not repository.delete_saved_search(search_id):
        raise HTTPException(status_code=404, detail="saved search not found")

    return {"deleted": search_id}


# ---------------------------------------------------------------------------
# Client aliases (QWEN client name normalization)
# ---------------------------------------------------------------------------


@read_router.get("/v1/client-aliases", response_model=None)
def list_client_aliases():
    return {"items": repository.list_client_aliases()}


def _actor_name(principal: dict | None) -> str | None:
    if not principal:
        return None
    user = principal.get("user") or {}
    return user.get("name")


@searches_router.get(
    "/v1/client-aliases/qwen-names",
    response_model=None,
    dependencies=[Depends(require_scope("collections:write"))],
)
def list_qwen_client_names():
    """Все названия клиентов/брендов от QWEN в алфавитном порядке."""

    return {"items": repository.list_qwen_client_names()}


@searches_router.get(
    "/v1/client-aliases/audit",
    response_model=None,
    dependencies=[Depends(require_scope("collections:write"))],
)
def list_client_alias_audit(limit: int = Query(100, ge=1, le=500)):
    """Журнал правок справочника алиасов: кто, что и когда изменил."""

    return {"items": repository.list_client_alias_audit(limit=limit)}


@searches_router.put("/v1/client-aliases")
def upsert_client_alias(
    request: ClientAliasRequest,
    principal=Depends(require_scope("collections:write")),
):
    return repository.upsert_client_alias(
        request.alias, request.canonical, actor=_actor_name(principal),
    )


@searches_router.delete("/v1/client-aliases")
def delete_client_alias(
    alias: str = Query(..., min_length=1, max_length=200),
    principal=Depends(require_scope("collections:write")),
):
    if not repository.delete_client_alias(alias, actor=_actor_name(principal)):
        raise HTTPException(status_code=404, detail="alias not found")

    return {"deleted": alias}


# ---------------------------------------------------------------------------
# Per-manager UI state
# ---------------------------------------------------------------------------


def _require_user(principal) -> dict:
    user = principal.get("user") if principal else None

    if not user:
        raise HTTPException(status_code=401, detail="authentication required")

    return user


@read_router.get("/v1/selection", response_model=None)
def get_selection(principal=Depends(require_scope("read"))):
    user = _require_user(principal)
    state = repository.get_manager_selection(str(user["user_id"]))
    return {"state": state or {}}


@searches_router.put("/v1/selection")
def put_selection(
    request: SelectionState,
    principal=Depends(require_scope("collections:write")),
):
    user = _require_user(principal)
    user_id = str(user["user_id"])

    # Merge instead of replace: the grid selection and the display settings are
    # saved by different parts of the UI, and neither may drop the other's keys.
    current = repository.get_manager_selection(user_id)
    current = current if isinstance(current, dict) else {}

    merged = {**current, **request.state}

    # Bound the stored blob so a client cannot write arbitrarily large state.
    if len(json.dumps(merged, ensure_ascii=False)) > 65536:
        raise HTTPException(
            status_code=413,
            detail="selection state is too large",
        )

    repository.save_manager_selection(user_id, merged)
    return {"state": merged}


# ---------------------------------------------------------------------------
# Authentication (users + sessions)
# ---------------------------------------------------------------------------


def _public_user(user: dict) -> dict:
    return {key: value for key, value in user.items() if key != "password_hash"}


@auth_router.post("/v1/auth/login")
def login(request: LoginRequest):
    user = users_db.get_user_by_name(request.name)

    if user is None or not user["active"]:
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Fail-closed: an account with no password set cannot log in.
    if not has_password(user.get("password_hash")):
        raise HTTPException(
            status_code=403,
            detail=(
                "no password set for this account; set one with "
                "scripts/set_password.py"
            ),
        )

    if not verify_password(request.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = users_db.create_session(user["user_id"])

    # Учёт посещений. Ошибка записи не должна ломать вход.
    try:
        from app import visits as visits_mod

        visits_mod.record_visit(
            user_id=user["user_id"], user_name=user["name"], event="login",
        )
    except Exception:  # noqa: BLE001 - logging must never block login
        pass

    return {"token": token, "user": _public_user(user)}


@auth_router.post("/v1/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    return {"logged_out": bool(token and users_db.delete_session(token))}


@auth_router.get("/v1/auth/me", response_model=None)
def me(authorization: str | None = Header(default=None)):
    """
    Public: tells the SPA whether login is required and who is logged in.

    Must stay reachable without a token, otherwise an unauthenticated client
    cannot learn that it needs to authenticate.
    """

    principal = resolve_principal(authorization)
    user = principal.get("user") if principal else None
    return {"user": user, "auth_enabled": auth_enabled()}


@read_router.get(
    "/v1/users",
    response_model=None,
    dependencies=[Depends(require_scope("users:manage"))],
)
def list_users(active_only: bool = Query(False)):
    """User directory is administrator-only (names, roles, activity)."""

    return {"items": users_db.list_users(active_only=active_only)}


@read_router.get(
    "/v1/visits",
    response_model=None,
    dependencies=[Depends(require_scope("users:manage"))],
)
def list_visits(limit: int = Query(100, ge=1, le=500)):
    """Журнал посещений (входов) — только Администратору."""

    from app import visits as visits_mod

    return {"items": visits_mod.list_visits(limit=limit)}


@users_router.post(
    "/v1/users",
    status_code=201,
    dependencies=[Depends(require_scope("users:manage"))],
)
def create_user(request: UserCreate):
    try:
        return _public_user(
            users_db.create_user(
                name=request.name,
                role=request.role,
                color=request.color,
                password=request.password,
            )
        )
    except Exception as exc:  # unique violation etc.
        # Do not leak driver/DB details to the client.
        raise HTTPException(
            status_code=409,
            detail="cannot create user (name already taken?)",
        ) from exc


@users_router.patch(
    "/v1/users/{user_id}",
    dependencies=[Depends(require_scope("users:manage"))],
)
def update_user(user_id: int, request: UserUpdate):
    user = users_db.get_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    # The seeded Администратор and Гость keep working: archiving them would
    # leave the installation without an administrator or a shared login.
    if request.active is False and users_db.is_builtin_user(user):
        raise HTTPException(
            status_code=400,
            detail="Администратора и Гостя нельзя архивировать",
        )

    updated = users_db.update_user(
        user_id,
        name=request.name,
        color=request.color,
        role=request.role,
        active=request.active,
    )

    if request.password is not None:
        users_db.set_password(user_id, request.password or None)

    return _public_user(updated)


# ---------------------------------------------------------------------------
# QWEN model selection (runtime setting)
# ---------------------------------------------------------------------------


@read_router.get("/v1/qwen/stats", response_model=None)
def qwen_stats():
    return {
        "counts": repository.qwen_status_counts(),
        "failed_photo_ids": repository.photo_ids_with_qwen_status("FAILED"),
    }


@read_router.get("/v1/qwen/settings", response_model=None)
def qwen_settings():
    """Active QWEN provider settings (api key masked)."""

    return qwen.public_settings()


@jobs_router.put(
    "/v1/qwen/settings",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def update_qwen_settings(request: QwenSettingsUpdate):
    try:
        return qwen.update_settings(
            provider=request.provider,
            model=request.model,
            base_url=request.base_url,
            api_key=request.api_key,
            keep_alive=request.keep_alive,
            unload_on_idle=request.unload_on_idle,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@read_router.get("/v1/qwen/models", response_model=None)
def qwen_models():
    config = qwen.resolve_settings()

    try:
        available = qwen.list_models(config)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"provider '{config['provider']}' unavailable: {exc}",
        ) from exc

    return {
        "current": config["model"],
        "provider": config["provider"],
        "available": available,
    }


@jobs_router.put(
    "/v1/qwen/model",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def set_qwen_model(request: QwenModelRequest):
    settings_store.set_value(qwen.QWEN_MODEL_KEY, request.model)
    return {"model": qwen.resolve_model()}


@jobs_router.post(
    "/v1/qwen/unload",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def unload_qwen():
    try:
        unloaded = qwen.unload_model()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"ollama unavailable: {exc}",
        ) from exc

    if not unloaded:
        return {
            "status": "not_applicable",
            "provider": qwen.resolve_settings()["provider"],
        }

    return {"status": "unloaded", "model": qwen.resolve_model()}


# --- working (source) folder for INGEST -------------------------------------


@read_router.get("/v1/ingest/folder", response_model=None)
def get_ingest_folder():
    """Configured working folder plus its photo count and total size."""

    return sources.folder_state()


@jobs_router.put(
    "/v1/ingest/folder",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def update_ingest_folder(request: SourcePathRequest):
    """Validate and persist the working folder (recursive count + MB)."""

    return sources.set_folder(request.path)


@jobs_router.post(
    "/v1/ingest/scan",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def scan_ingest_folder(request: SourcePathRequest):
    """Count photos and total size of a folder without saving or ingesting it."""

    return sources.folder_stats(sources.resolve_directory(request.path))


@jobs_router.post(
    "/v1/previews/backfill",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def queue_missing_previews(limit: int = Query(500, ge=1, le=5000)):
    """Queue a bounded page of registered photos without a preview record."""

    from app.preview.queue import enqueue_missing_previews

    return enqueue_missing_previews(limit=limit)


@jobs_router.post(
    "/v1/ingest/run",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def run_ingest(request: SourceRunRequest):
    """
    Enqueue an INGEST job for the working folder.

    The scan itself runs in the worker (hashing and decoding must not happen
    in a request handler). An active job for the same folder is not
    duplicated. The folder is optional: without it the configured one is used.
    """

    directory = sources.resolve_directory(
        request.path or sources.current_folder()
    )
    job_id = jobs_db.enqueue_ingest(str(directory))

    return {
        "job_id": job_id,
        "skipped": job_id is None,
        "directory": str(directory),
    }


# ---------------------------------------------------------------------------
# Resumable pipeline run (schema/031): "Обновление базы".
# The supervisor only enqueues/observes jobs; it runs in a separate worker.
# ---------------------------------------------------------------------------


@jobs_router.post(
    "/v1/pipeline/start",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def start_pipeline_run(request: PipelineStartRequest):
    """Start a fresh run (a stopped run is superseded)."""

    from app.supervisor import runs as pipeline_runs

    folder = request.folder or sources.current_folder() or None

    if folder:
        folder = str(sources.resolve_directory(folder))

    try:
        run = pipeline_runs.create_run(mode=request.mode, folder=folder)
    except pipeline_runs.PipelineBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return run


@jobs_router.post(
    "/v1/pipeline/{run_id}/stop",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def stop_pipeline_run(run_id: int):
    from app.supervisor import runs as pipeline_runs

    if not pipeline_runs.request_stop(run_id):
        raise HTTPException(status_code=409, detail="run is not active")

    return pipeline_runs.get_run_with_stages(run_id)


@jobs_router.post(
    "/v1/pipeline/{run_id}/resume",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def resume_pipeline_run(run_id: int):
    from app.supervisor import runs as pipeline_runs

    try:
        if not pipeline_runs.resume_run(run_id):
            raise HTTPException(status_code=409, detail="run is not stopped")
    except pipeline_runs.PipelineBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return pipeline_runs.get_run_with_stages(run_id)


@read_router.get("/v1/pipeline/current", response_model=None)
def current_pipeline_run():
    """Active run with its stages, else the most recent run, else null."""

    from app.supervisor import runs as pipeline_runs

    run = pipeline_runs.active_run() or pipeline_runs.latest_run()

    return {"run": pipeline_runs.get_run_with_stages(run["run_id"]) if run else None}


@read_router.get("/v1/pipeline", response_model=None)
def list_pipeline_runs(limit: int = Query(20, ge=1, le=100)):
    from app.supervisor import runs as pipeline_runs

    items = [
        pipeline_runs.get_run_with_stages(run["run_id"])
        for run in pipeline_runs.list_runs(limit=limit)
    ]

    return {"items": items}


@read_router.get("/v1/pipeline/{run_id}", response_model=None)
def get_pipeline_run(run_id: int):
    from app.supervisor import runs as pipeline_runs

    run = pipeline_runs.get_run_with_stages(run_id)

    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    return run


# ---------------------------------------------------------------------------
# Address directory (schema/022): legal and simplified names for fingerprints
# ---------------------------------------------------------------------------


def _directory_error(exc: directory_mod.DirectoryError) -> HTTPException:
    """Map a directory validation error to a client error without internals."""

    return HTTPException(status_code=400, detail=str(exc))


@addresses_router.get(
    "/v1/addresses/directory",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def list_address_directory():
    """Every address with the fingerprint ids mapped to it."""

    return {"items": directory_mod.list_addresses()}


@addresses_router.get(
    "/v1/addresses/unassigned",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def list_unassigned_fingerprints():
    """
    Fingerprints found on disk that no address owns yet.

    Lets the UI offer the ids that still need a name instead of asking the
    user to type a technical id by hand.
    """

    known = [item["id"] for item in sysinfo.list_fingerprints()]

    return {"items": directory_mod.unassigned_fingerprints(known)}


@addresses_router.post(
    "/v1/addresses/directory",
    status_code=201,
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def create_address(request: AddressCreate):
    """Create one address (at least one of the two names must be filled)."""

    try:
        return directory_mod.create_address(
            legal_address=request.legal_address,
            simple_address=request.simple_address,
            sort_order=request.sort_order,
        )
    except directory_mod.DirectoryError as exc:
        raise _directory_error(exc) from exc


@addresses_router.put(
    "/v1/addresses/directory/{address_id}",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def update_address(address_id: int, request: AddressUpdate):
    """Update the supplied fields; omitted ones keep their value."""

    try:
        updated = directory_mod.update_address(
            address_id,
            legal_address=request.legal_address,
            simple_address=request.simple_address,
            active=request.active,
            sort_order=request.sort_order,
        )
    except directory_mod.DirectoryError as exc:
        raise _directory_error(exc) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="address not found")

    return updated


@addresses_router.delete(
    "/v1/addresses/directory/{address_id}",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def delete_address(address_id: int):
    """Delete an address; its fingerprint mappings go with it."""

    if not directory_mod.delete_address(address_id):
        raise HTTPException(status_code=404, detail="address not found")

    return {"address_id": address_id, "deleted": True}


@addresses_router.put(
    "/v1/addresses/directory/{address_id}/fingerprints",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def set_address_fingerprints(
    address_id: int,
    request: AddressFingerprintsRequest,
):
    """
    Replace the fingerprint ids of an address (the list is the new set).

    A fingerprint id belongs to one address: ids listed here are moved.
    """

    try:
        updated = directory_mod.set_fingerprints(
            address_id,
            request.fingerprints,
        )
    except directory_mod.DirectoryError as exc:
        raise _directory_error(exc) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="address not found")

    return updated


# ---------------------------------------------------------------------------
# Fingerprint registry (schema/023): names, versions, archiving
# ---------------------------------------------------------------------------


def _fingerprint_error(exc: fingerprints_mod.FingerprintError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@fingerprints_router.get(
    "/v1/fingerprints/registry",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def list_fingerprint_registry():
    """Registry rows for every known fingerprint, with address and version."""

    return {"items": fingerprints_mod.list_registry()}


@fingerprints_router.post(
    "/v1/fingerprints/sync",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def sync_fingerprint_registry():
    """
    Mirror data/fingerprints/*/metadata.json into the registry.

    Idempotent: a second run in a row changes nothing. A new version row is
    written only when a fingerprint was rebuilt with a different photo set.
    """

    return fingerprints_mod.sync_from_disk()


@fingerprints_router.get(
    "/v1/fingerprints/registry/{fingerprint_id}",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_fingerprint_registry(fingerprint_id: str):
    try:
        item = fingerprints_mod.get_fingerprint(fingerprint_id)
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    if item is None:
        raise HTTPException(status_code=404, detail="fingerprint not found")

    return item


@fingerprints_router.put(
    "/v1/fingerprints/registry/{fingerprint_id}",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def update_fingerprint_registry(
    fingerprint_id: str,
    request: FingerprintUpdate,
):
    """Rename, describe, archive or point at a source folder."""

    try:
        updated = fingerprints_mod.update_fingerprint(
            fingerprint_id,
            display_name=request.display_name,
            description=request.description,
            source_folder=request.source_folder,
            active=request.active,
        )
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="fingerprint not found")

    return updated


@fingerprints_router.get(
    "/v1/fingerprints/registry/{fingerprint_id}/versions",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def list_fingerprint_versions(fingerprint_id: str):
    """Version journal of one fingerprint, newest first."""

    try:
        versions = fingerprints_mod.list_versions(fingerprint_id)
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    if versions is None:
        raise HTTPException(status_code=404, detail="fingerprint not found")

    return {"items": versions}


@fingerprints_router.get(
    "/v1/fingerprints/registry/{fingerprint_id}/preview",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_fingerprint_preview(fingerprint_id: str) -> Response:
    """
    The montage of source photos stored with a fingerprint (preview.jpg).

    The builder writes it next to the vectors, so it outlives the source folder.
    404 when the fingerprint has none - built before previews existed and not
    rebuilt since.
    """

    try:
        path = fingerprints_mod.preview_path(fingerprint_id)
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    if path is None:
        raise HTTPException(status_code=404, detail="preview not found")

    # Rebuilding a fingerprint keeps its id, so the same URL gets new content:
    # it must not be cached.
    return Response(
        content=path.read_bytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache"},
    )


# ---------------------------------------------------------------------------
# Building a fingerprint from the window: choose a folder, enqueue the build
# ---------------------------------------------------------------------------


@fingerprints_router.post(
    "/v1/fingerprints/build",
    status_code=202,
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def build_fingerprint(request: FingerprintBuildRequest):
    """
    Queue a fingerprint build from a server-side folder.

    The folder is validated the same way as the INGEST working folder
    (existence, and SCENE_SOURCE_ROOTS when it is set). The build itself runs in
    the worker - it reads every photo and runs DINOv2, which must not happen in
    a request handler. Nothing is copied: the builder reads the folder and keeps
    only the result plus the names and capture dates of the photos used.
    """

    try:
        fingerprint_id = fingerprints_mod._check_id(request.fingerprint_id)
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    folder = sources.resolve_directory(request.folder)
    stats = sources.folder_stats(folder)

    if not stats["files"]:
        raise HTTPException(
            status_code=400,
            detail="в папке нет фотографий",
        )

    job_id = jobs_db.enqueue_fingerprint_build(
        fingerprint_id,
        str(folder),
        max_photos=request.max_photos,
        replace=request.replace,
    )

    return {
        "job_id": job_id,
        "skipped": job_id is None,
        "fingerprint_id": fingerprint_id,
        "folder": str(folder),
        "photos": stats["files"],
        "max_photos": request.max_photos,
    }


def _direct_photo_count(directory: Path) -> int:
    """Photos directly inside *directory* (no recursion): a hint for the picker."""

    try:
        return sum(
            1
            for entry in os.scandir(directory)
            if entry.is_file()
            and Path(entry.name).suffix.lower() in SUPPORTED_EXTENSIONS
        )
    except OSError:
        return 0


@fingerprints_router.get(
    "/v1/fingerprints/browse",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def browse_folders(path: str | None = Query(default=None)):
    """
    List sub-folders of a server directory, for the folder picker.

    Without a path it lists the allowed roots (or the home directory when
    SCENE_SOURCE_ROOTS is not configured). This reads directory names only;
    when SCENE_SOURCE_ROOTS is set, nothing outside those roots is listed.
    """

    if path:
        current = sources.resolve_directory(path)
    else:
        roots = SOURCE_ROOTS or [Path.home()]

        return {
            "path": None,
            "parent": None,
            "dirs": [
                {
                    "name": str(root),
                    "path": str(root),
                    "photos": _direct_photo_count(root),
                }
                for root in roots
                if root.is_dir()
            ],
            "photos": 0,
        }

    parent = current.parent

    try:
        entries = sorted(
            (
                entry
                for entry in os.scandir(current)
                if entry.is_dir() and not entry.name.startswith(".")
            ),
            key=lambda entry: entry.name.lower(),
        )
    except OSError as exc:
        raise HTTPException(status_code=400, detail="folder is not readable") from exc

    dirs = []

    for entry in entries:
        child = Path(entry.path)

        # Keep the listing inside the configured roots.
        if SOURCE_ROOTS and not any(
            str(child).startswith(str(root)) for root in SOURCE_ROOTS
        ):
            continue

        dirs.append(
            {
                "name": entry.name,
                "path": entry.path,
                "photos": _direct_photo_count(child),
            }
        )

    return {
        "path": str(current),
        "parent": str(parent) if parent != current else None,
        "dirs": dirs,
        "photos": _direct_photo_count(current),
    }


# The OS folder dialog can only run on the machine that has a desktop session
# (the server, when the browser is used locally). It is off by default: the
# in-app browser works from any client.
MAX_IMPORT_BYTES = 10 * 1024 * 1024

NATIVE_PICKER = os.getenv("SCENE_NATIVE_PICKER", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}


@fingerprints_router.post(
    "/v1/fingerprints/pick-folder",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def pick_folder_native():
    """
    Open the system folder dialog on the server and return the chosen path.

    A browser cannot hand a server-side path to the page, so this is the only
    way to get a literal OS dialog; it needs a desktop session on the server and
    is enabled with SCENE_NATIVE_PICKER=1. The chosen folder is validated with
    the same rules as everywhere else (existence, SCENE_SOURCE_ROOTS).
    """

    if not NATIVE_PICKER:
        raise HTTPException(
            status_code=501,
            detail="системный выбор папки выключен (SCENE_NATIVE_PICKER=1)",
        )

    zenity = shutil.which("zenity")

    if zenity is None:
        raise HTTPException(
            status_code=501,
            detail="zenity не найден на сервере",
        )

    try:
        completed = subprocess.run(
            [
                zenity,
                "--file-selection",
                "--directory",
                "--title=Папка с фотографиями для слепка",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="диалог не был закрыт") from exc

    if completed.returncode != 0:
        raise HTTPException(status_code=409, detail="выбор папки отменён")

    chosen = (completed.stdout or "").strip()

    if not chosen:
        raise HTTPException(status_code=409, detail="папка не выбрана")

    return {"path": str(sources.resolve_directory(chosen))}


@fingerprints_router.put(
    "/v1/fingerprints/registry/{fingerprint_id}/address",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def set_fingerprint_address(
    fingerprint_id: str,
    request: FingerprintAddressRequest,
):
    """
    Map a fingerprint to a legal address from the directory (or clear it).

    The id comes from the directory dropdown; nothing is typed by hand, so a
    fingerprint can only point at an address that exists.
    """

    try:
        updated = fingerprints_mod.set_address(
            fingerprint_id,
            request.address_id,
        )
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="fingerprint not found")

    return updated


@addresses_router.post(
    "/v1/addresses/import",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def import_address_directory(file: UploadFile = File(...)):
    """
    Import legal addresses from a spreadsheet (.xlsx, .xlsm, .csv, .tsv).

    The header row is optional. Existing addresses are matched by the legal name
    and keep their id, so photos and fingerprints mapped to them stay mapped;
    only a different simplified name is refreshed.
    """

    try:
        content = file.file.read()
    except OSError as exc:
        raise HTTPException(status_code=400, detail="файл не читается") from exc

    if not content:
        raise HTTPException(status_code=400, detail="пустой файл")

    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="файл слишком большой")

    try:
        items = directory_mod.parse_address_table(content, file.filename or "")
    except directory_mod.DirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not items:
        raise HTTPException(status_code=400, detail="в файле нет адресов")

    try:
        result = directory_mod.import_addresses(items)
    except directory_mod.DirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"rows": len(items), **result}


@fingerprints_router.post(
    "/v1/fingerprints/build-batch",
    status_code=202,
    response_model=None,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def build_fingerprint_batch(request: FingerprintBatchRequest):
    """
    Queue several fingerprint builds at once.

    Every item becomes its own job, so any number of builder workers can take
    them in parallel (`app.jobs.worker --only FINGERPRINT_BUILD --parallel N`).
    All jobs share a batch id, which the window uses to draw one progress bar;
    GET /v1/fingerprints/batch/{id} reports the aggregate.
    """

    batch_id = uuid.uuid4().hex
    jobs_out = []
    errors = []

    for item in request.items:
        try:
            fingerprint_id = fingerprints_mod._check_id(item.fingerprint_id)
            folder = sources.resolve_directory(item.folder)
        except fingerprints_mod.FingerprintError as exc:
            errors.append({"fingerprint_id": item.fingerprint_id, "error": str(exc)})
            continue
        except HTTPException as exc:
            errors.append(
                {"fingerprint_id": item.fingerprint_id, "error": str(exc.detail)}
            )
            continue

        stats = sources.folder_stats(folder)

        if not stats["files"]:
            errors.append(
                {
                    "fingerprint_id": fingerprint_id,
                    "error": "в папке нет фотографий",
                }
            )
            continue

        job_id = jobs_db.enqueue_fingerprint_build(
            fingerprint_id,
            str(folder),
            max_photos=request.max_photos,
            replace=request.replace,
            batch_id=batch_id,
        )

        jobs_out.append(
            {
                "fingerprint_id": fingerprint_id,
                "job_id": job_id,
                "skipped": job_id is None,
                "photos": stats["files"],
            }
        )

    return {
        "batch_id": batch_id,
        "jobs": jobs_out,
        "errors": errors,
    }


@fingerprints_router.get(
    "/v1/fingerprints/batch/{batch_id}",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_fingerprint_batch(batch_id: str):
    """
    Aggregate state of a batch: per-job status and one percentage.

    The percentage is weighted by photos: finished jobs count as complete, so
    the bar moves smoothly even while other jobs are still starting.
    """

    if not re.match(r"^[0-9a-f]{8,64}$", batch_id):
        raise HTTPException(status_code=400, detail="bad batch id")

    batch_jobs = jobs_db.list_batch(batch_id)

    total_units = 0
    done_units = 0
    counts: dict[str, int] = {}

    for job in batch_jobs:
        counts[job["status"]] = counts.get(job["status"], 0) + 1

        progress = job.get("progress") or {}
        units = int(progress.get("total") or 0) or 2
        total_units += units

        if job["status"] == "DONE":
            done_units += units
        elif job["status"] == "RUNNING":
            done_units += int(progress.get("done") or 0)

    percent = round(done_units / total_units * 100, 1) if total_units else 0.0

    return {
        "batch_id": batch_id,
        "total": len(batch_jobs),
        "counts": counts,
        "percent": percent,
        "jobs": [
            {
                "job_id": job["id"],
                "fingerprint_id": (job.get("payload") or {}).get("fingerprint_id"),
                "status": job["status"],
                "progress": job.get("progress"),
                "result": job.get("result"),
                "error_message": job.get("error_message"),
            }
            for job in batch_jobs
        ],
    }

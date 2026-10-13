"""
Read-only API endpoints.

Authentication is optional (see app/api/auth.py): when SCENE_API_TOKENS is
unset, everything is open for local development. Read endpoints require the
"read" scope; original files require the "originals" scope.
"""

from __future__ import annotations

import re
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

from app import settings_store
from app.api import repository
from app.api import data as data_mod
from app.api import system as sysinfo
from app.api import upload as upload_mod
from app.api.auth import auth_enabled, require_scope
from app.api.config import PREVIEW_ROOT
from app.core.errors import redact_paths
from app.api.schemas import (
    AutomationUpdate,
    ClientAliasRequest,
    CollectionCreate,
    CollectionMembersRequest,
    DinoBatchRequest,
    HybridRequest,
    LoginRequest,
    NlSearchRequest,
    QwenJobRequest,
    QwenModelRequest,
    QwenSettingsUpdate,
    SavedSearchCreate,
    SelectionState,
    UserCreate,
    UserUpdate,
)
from app.qwen import processor as qwen
from app.qwen import database as qwen_db
from app.users import database as users_db
from app.users.security import verify_password
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
        collection_id=collection_id,
        ids=ids,
    )
    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
    }


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

    if not photo_ids:
        raise HTTPException(
            status_code=422,
            detail="no photos to process",
        )

    job_ids = [
        jobs_db.enqueue("QWEN_PHOTO", {"photo_id": photo_id})
        for photo_id in photo_ids
    ]

    return {
        "jobs": len(job_ids),
        "first_job_id": job_ids[0],
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
    count = jobs_db.requeue_stale(older_than_minutes=older_than_minutes)
    return {"requeued": count}


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


@searches_router.put(
    "/v1/client-aliases",
    dependencies=[Depends(require_scope("collections:write"))],
)
def upsert_client_alias(request: ClientAliasRequest):
    return repository.upsert_client_alias(request.alias, request.canonical)


@searches_router.delete(
    "/v1/client-aliases",
    dependencies=[Depends(require_scope("collections:write"))],
)
def delete_client_alias(alias: str = Query(..., min_length=1, max_length=200)):
    if not repository.delete_client_alias(alias):
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
    repository.save_manager_selection(str(user["user_id"]), request.state)
    return {"state": request.state}


# ---------------------------------------------------------------------------
# Authentication (users + sessions)
# ---------------------------------------------------------------------------


def _public_user(user: dict) -> dict:
    return {key: value for key, value in user.items() if key != "password_hash"}


@auth_router.post("/v1/auth/login")
def login(request: LoginRequest):
    user = users_db.get_user_by_name(request.name)

    if (
        user is None
        or not user["active"]
        or not verify_password(request.password, user.get("password_hash"))
    ):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = users_db.create_session(user["user_id"])

    return {"token": token, "user": _public_user(user)}


@auth_router.post("/v1/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    return {"logged_out": bool(token and users_db.delete_session(token))}


@auth_router.get("/v1/auth/me", response_model=None)
def me(principal=Depends(require_scope("read"))):
    user = principal.get("user") if principal else None
    return {"user": user, "auth_enabled": auth_enabled()}


@read_router.get("/v1/users", response_model=None)
def list_users(active_only: bool = Query(False)):
    return {"items": users_db.list_users(active_only=active_only)}


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
        raise HTTPException(
            status_code=409,
            detail=f"cannot create user: {exc}",
        ) from exc


@users_router.patch(
    "/v1/users/{user_id}",
    dependencies=[Depends(require_scope("users:manage"))],
)
def update_user(user_id: int, request: UserUpdate):
    if users_db.get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

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

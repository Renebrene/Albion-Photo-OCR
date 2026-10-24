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
from datetime import date as date_type
from pathlib import Path

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
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
from app.core.layout import to_other_layout
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
    HybridSettingsUpdate,
    LoginRequest,
    MediaLinkRequest,
    NlSearchRequest,
    PhotoAddressRequest,
    PreviewBackfillRequest,
    QwenJobRequest,
    QwenTextUpdate,
    QwenModelRequest,
    QwenPeriodScanRequest,
    QwenRescanRequest,
    QwenSettingsUpdate,
    RefineSettingsUpdate,
    SavedSearchCreate,
    PipelineStartRequest,
    SearchQueryRequest,
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
from app.preview import formats as preview_formats
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


def _date_params(
    date_from: date_type | None,
    date_to: date_type | None,
) -> tuple[str | None, str | None]:
    """ISO dates for SQL; an inverted range is swapped, not silently empty."""

    start = date_from.isoformat() if date_from else None
    end = date_to.isoformat() if date_to else None

    if start and end and start > end:
        start, end = end, start

    return start, end


@public_router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@read_router.get("/v1/photos", response_model=None)
def list_photos(
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=64),
    q: str | None = Query(None, max_length=256),
    # `max_length` on a list query parameter limits the NUMBER of values.
    # The clients panel shows at most 100, so «Все» can send at most 100.
    address: list[str] | None = Query(None, max_length=1000),
    client: list[str] | None = Query(None, max_length=100),
    # Structured values chosen from the search suggestions. Matched exactly,
    # unlike the free-text `q` (which is deliberately a substring search).
    brand: str | None = Query(None, max_length=200),
    tag: str | None = Query(None, max_length=200),
    category: str | None = Query(None, max_length=200),
    date_from: date_type | None = Query(None),
    date_to: date_type | None = Query(None),
    date_mode: str = Query("upload", pattern="^(upload|capture)$"),
    # How address and client selections combine: union (join), or one facet
    # leads and the other refines inside it.
    combine: str = Query("union", pattern="^(union|address|client)$"),
    collection_id: int | None = Query(None, ge=1),
    ids: list[str] | None = Query(None, max_length=200),
    principal=Depends(require_scope("read")),
    sort: str = Query("photo_id"),
    order: str = Query("asc", pattern=r"^(asc|desc)$"),
):
    date_from, date_to = _date_params(date_from, date_to)

    # A collection belongs to its owner; asking for somebody else's yields an
    # empty page rather than 404, so the response does not reveal that the id
    # exists. Only photo collections are valid here: address/client
    # collections are applied through address/client values.
    if collection_id is not None:
        collection = repository.get_collection(
            collection_id, _principal_user_id(principal)
        )

        if collection is None:
            return {"items": [], "next_cursor": None, "total": 0}

        if collection.get("scope") != "photos":
            raise HTTPException(
                status_code=422,
                detail="collection scope must be photos",
            )

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
        brand=brand,
        tag=tag,
        category=category,
        # The grid shows a photo only after HYBRID has assigned an address
        # (or after a manual override); videos are a separate list.
        recognized_only=True,
        combine=combine,
        sort=sort,
        order=order,
    )

    if sort not in repository.SORT_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported sort key: {sort}",
        )

    # The grid label («За период N фото») needs the size of the whole filtered
    # set, not just the loaded page. Count once, on the first page: subsequent
    # pages are the same set while the user scrolls.
    total = None

    if cursor is None:
        total = repository.count_photos(
            query=q,
            addresses=address,
            clients=client,
            date_from=date_from,
            date_to=date_to,
            date_mode=date_mode,
            collection_id=collection_id,
            ids=ids,
            brand=brand,
            tag=tag,
            category=category,
            recognized_only=True,
            combine=combine,
        )

    return {
        "items": [item.model_dump() for item in items],
        "next_cursor": next_cursor,
        "total": total,
    }


@read_router.get("/v1/stats", response_model=None)
def get_stats(
    date_from: date_type | None = Query(None),
    date_to: date_type | None = Query(None),
    date_mode: str = Query("upload", pattern="^(upload|capture)$"),
):
    """Counts for the status bar: totals, period counts, addresses, clients."""

    start, end = _date_params(date_from, date_to)

    return repository.stats(
        date_from=start,
        date_to=end,
        date_mode=date_mode,
    )


@read_router.get("/v1/system", response_model=None)
def get_system_info():
    return sysinfo.system_info()


@read_router.get("/v1/fingerprints", response_model=None)
def list_fingerprints():
    return {"items": sysinfo.list_fingerprints()}


@read_router.get("/v1/runs/last", response_model=None)
def get_last_run():
    return sysinfo.last_run()


@read_router.get("/v1/runs/activity", response_model=None)
def run_activity():
    """Operation that currently changes recognition state (if any)."""

    from app.runs import coordination

    active = coordination.active_operation()

    return {
        "active": active,
        "message": coordination.busy_message(active) if active else None,
    }


@jobs_router.get(
    "/v1/media-links",
    dependencies=[Depends(require_scope("jobs:read"))],
)
def list_media_links(
    limit: int = Query(100, ge=1, le=200),
    all: bool = Query(False),
    include_unready: bool = Query(False),
    principal=Depends(require_scope("jobs:read")),
):
    """Albion links; by default ready ones, only the caller's own."""

    from app.cloud import albion, repository as cloud_repository

    if all and principal is not None:
        scopes = principal.get("scopes") or set()
        if "*" not in scopes and "users:manage" not in scopes:
            raise HTTPException(
                status_code=403,
                detail="all media links require administrator rights",
            )

    user = principal.get("user") if principal else None
    owner = None if all or user is None else str(user["user_id"])
    return {
        "items": cloud_repository.list_links(
            owner_user_id=owner,
            limit=limit,
            include_unready=include_unready,
        ),
        "configured": albion.is_configured(),
    }


@jobs_router.post(
    "/v1/media-links",
    status_code=202,
    dependencies=[Depends(require_scope("upload:write"))],
)
def create_media_links(
    request: MediaLinkRequest,
    principal=Depends(require_scope("upload:write")),
):
    """Queue one Albion upload per selected photo/video."""

    from app.cloud import albion, repository as cloud_repository

    user = principal.get("user") if principal else None
    # Service tokens may also export; their links carry no personal owner.
    owner_id = str(user["user_id"]) if user else "service"
    owner_name = user.get("name") if user else "service"
    items: list[dict] = []
    job_ids: list[int] = []

    if not albion.is_configured():
        raise HTTPException(
            status_code=503,
            detail="облачное хранилище Albion не настроено",
        )

    for media_kind, ids, pattern in (
        ("photo", request.photo_ids, PHOTO_ID_RE),
        ("video", request.video_ids, re.compile(r"^VI_[0-9a-f]{24}$")),
    ):
        for media_id in ids:
            if not pattern.fullmatch(media_id):
                raise HTTPException(
                    status_code=422,
                    detail=f"invalid {media_kind}_id: {media_id}",
                )
            if cloud_repository.media_source(media_kind, media_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"{media_kind} not found: {media_id}",
                )

            link = cloud_repository.create_pending(
                owner_user_id=owner_id,
                owner_name=owner_name,
                media_kind=media_kind,
                media_id=media_id,
            )
            items.append(link)
            if link["status"] == "READY":
                continue

            try:
                job_id = jobs_db.enqueue(
                    "MEDIA_EXPORT",
                    {"link_id": link["link_id"]},
                )
            except Exception as exc:
                cloud_repository.mark_failed(
                    link["link_id"],
                    f"не удалось поставить загрузку в очередь: {type(exc).__name__}",
                )
                raise HTTPException(
                    status_code=503,
                    detail="не удалось поставить загрузку в очередь",
                ) from exc

            cloud_repository.attach_job(link["link_id"], job_id)
            job_ids.append(job_id)

    return {
        "items": items,
        "job_ids": job_ids,
        "configured": True,
    }


@read_router.get("/v1/runs/history", response_model=None)
def list_run_history(
    kind: str | None = Query(None, pattern=r"^(pipeline|ingest|sort|qwen|scheduler)$"),
    limit: int = Query(20, ge=1, le=200),
):
    """Единая история пользовательских запусков по видам."""

    from app.runs import history

    return {"items": history.list_runs(kind=kind, limit=limit)}


@jobs_router.get(
    "/v1/runs/history/{run_id}/log",
    response_class=Response,
    dependencies=[Depends(require_scope("jobs:read"))],
)
def read_run_log(run_id: int):
    """Безопасно прочитать лог по внутреннему ID; путь/имя файла клиент не задаёт."""

    from app.runs import history

    text = history.read_run_log(run_id)

    if text is None:
        raise HTTPException(status_code=404, detail="run log not found")

    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


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
def list_addresses(
    limit: int = Query(1000, ge=1, le=5000),
    date_from: date_type | None = Query(None),
    date_to: date_type | None = Query(None),
    date_mode: str = Query("upload", pattern="^(upload|capture)$"),
    client: list[str] | None = Query(None, max_length=100),
):
    # `count` is all-time (the panel must not lose it when a period is picked);
    # `period_count` repeats the count inside the caller's date range.
    # `client` narrows the list in client-priority mode.
    start, end = _date_params(date_from, date_to)

    return {
        "items": repository.list_addresses(
            limit=limit,
            date_from=start,
            date_to=end,
            date_mode=date_mode,
            clients=client,
        )
    }


@read_router.get("/v1/clients", response_model=None)
def list_clients(
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None, max_length=500),
    address: list[str] | None = Query(None, max_length=1000),
):
    """
    Клиенты и бренды для правой панели: страница по алфавиту + курсор.

    Панель листает список при прокрутке, поэтому отдаём `next_cursor`: без
    него панель была бы ограничена первыми ста именами (в корпусе их больше
    двухсот), а найти остальные можно было только через строку поиска.

    `address` narrowing is used in address-priority mode.
    """

    items, next_cursor = repository.list_clients(
        limit=limit,
        cursor=cursor,
        addresses=address,
    )

    return {"items": items, "next_cursor": next_cursor}


@read_router.get("/v1/search/suggestions", response_model=None)
def search_suggestions(
    q: str = Query("", max_length=100),
    limit: int = Query(8, ge=1, le=20),
):
    """
    Подсказки строки поиска по уже существующим значениям.

    Ищутся теги, клиенты, бренды и категории (подстрока или триграммное
    сходство). Если в текущей раскладке ничего не нашлось, слово
    переворачивается в другую раскладку и подсказки повторяются — так
    «rjvfyjdf» находит «Комарова».
    """

    term = q.strip()

    if len(term) < 2:
        return {"items": [], "layout": None}

    items = repository.suggest_terms(term, limit=limit)
    layout = None

    if len(items) < 3:
        converted = to_other_layout(term).strip()

        if converted and converted.lower() != term.lower():
            alt_items = repository.suggest_terms(converted, limit=limit)

            if alt_items:
                layout = {"query": converted, "items": alt_items}

    return {"items": items, "layout": layout}


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

    return {
        "photo": photo.model_dump(),
        "qwen": qwen_meta,
        "address_override": repository.get_photo_address_override(photo_id),
    }


@jobs_router.put(
    "/v1/photos/{photo_id}/qwen-text",
    response_model=None,
    dependencies=[Depends(require_scope("photos:write"))],
)
def update_photo_qwen_text(photo_id: str, request: QwenTextUpdate):
    """Save a hand-edited description from the photo card."""

    photo_id = _validate_photo_id(photo_id)

    if repository.get_photo(photo_id) is None:
        raise HTTPException(status_code=404, detail="photo not found")

    qwen_db.save_manual(
        photo_id,
        fields={**request.model_dump(), "tags": request.tags},
    )

    return qwen_db.get(photo_id)


@read_router.get("/v1/photos/{photo_id}/qwen-history", response_model=None)
def get_qwen_history(
    photo_id: str,
    limit: int = Query(10, ge=1, le=100),
):
    """
    Прежние результаты распознавания этого фото, новые сверху.

    Успешный ответ перезаписывает поля `photo_qwen` (владелец: «полная
    перезапись + история версий»), поэтому вытесненные результаты лежат здесь —
    их можно сравнить и вернуть.
    """

    photo_id = _validate_photo_id(photo_id)

    return {"items": qwen_db.list_history(photo_id, limit=limit)}


@read_router.get("/v1/qwen/history", response_model=None)
def get_global_qwen_history(limit: int = Query(200, ge=1, le=1000)):
    """Recent QWEN versions across all photos in a plain-text-ready form."""
    items = qwen_db.list_global_history(limit=limit)
    lines = []
    for item in items:
        when = str(item.get("replaced_at") or "").replace("T", " ")[:19] or "—"
        name = item.get("filename") or item.get("photo_id") or "—"
        tags = item.get("tags") or []
        if isinstance(tags, list):
            tags = ", ".join(str(tag) for tag in tags)
        lines.append(
            f"{when} | {name} | модель: {item.get('qwen_model') or '—'}"
            f" → {item.get('replaced_by_model') or '—'} | {item.get('status') or '—'}\n"
            f"клиент: {item.get('client') or '—'}, бренд: {item.get('brand') or '—'}, "
            f"категория: {item.get('category') or '—'}, теги: {tags or '—'}\n"
            f"{item.get('description') or '—'}"
        )
    return {"items": items, "text": "\n\n".join(lines)}


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
    requested = paths.small if size == "small" else paths.middle

    # Текущий формат (SCENE_PREVIEW_FORMAT), затем прежний JPEG: во время
    # перехода часть файлов ещё не пересоздана, и отдавать 404 нельзя.
    path = next(
        (candidate for candidate in preview_candidates(requested) if candidate.is_file()),
        None,
    )

    if path is None:
        raise HTTPException(status_code=404, detail="preview not found")

    return Response(
        content=path.read_bytes(),
        media_type=preview_media_type(path),
        headers={"Cache-Control": "public, max-age=3600"},
    )


@read_router.get("/v1/photos/{photo_id}/original/status")
def get_original_status(photo_id: str) -> dict:
    """
    Whether the original file of a photo can be served right now.

    The UI calls this before the user clicks "посмотреть" or "скачать", so a
    disappeared original (unmounted volume, deleted file) turns into
    "оригинал недоступен, используйте превью" instead of a failed request.
    Only the availability is reported — never the path, and nothing is read.
    The photo row itself is never deleted: the preview stays usable.
    """

    photo_id = _validate_photo_id(photo_id)
    source = repository.get_photo_source(photo_id)

    if source is None:
        raise HTTPException(status_code=404, detail="photo not found")

    status = file_access.original_availability(
        source.get("source_path"), ORIGINALS_ROOTS
    )

    return {
        "photo_id": photo_id,
        "available": status == file_access.ORIGINAL_OK,
        "reason": status,
    }


def preview_candidates(path: Path) -> list[Path]:
    """Пути превью этого размера: текущий формат, затем прежний JPEG."""

    return preview_formats.candidate_paths(path)


def preview_media_type(path: Path) -> str:
    """MIME по расширению отданного файла, а не по настройке."""

    suffix = path.suffix.lower()

    for _name, (extension, media) in preview_formats.FORMATS.items():
        if suffix == extension:
            return media

    return preview_formats.media_type()


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


@read_router.get(
    "/v1/sort/status",
    response_model=None,
    dependencies=[Depends(require_scope("jobs:read"))],
)
def get_sort_status():
    """Последняя сортировка: совпадения, статус, режимы и текущий batch."""

    from app.runs import sort_status as sort_status_mod

    return sort_status_mod.status()


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

    from app.runs import coordination

    try:
        with coordination.launch_guard():
            active = coordination.active_operation()

            if active:
                raise HTTPException(
                    status_code=409,
                    detail=coordination.busy_message(active),
                )

            return _enqueue_dino_batch_impl(request)
    except coordination.OperationBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _enqueue_dino_batch_impl(request: DinoBatchRequest):
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

    from app.runs import history as run_history

    try:
        history_id = run_history.create_run(
            kind="sort",
            mode=request.mode or "manual",
            title=f"DINO batch #{batch.batch_id}",
            total=batch.total_count,
            counts=run_history.initial_sort_counts(
                batch.total_count,
                dino=True,
                hybrid=bool(request.auto_hybrid),
            ),
            source_id=batch.batch_id,
            status="RUNNING" if batch.total_count else "PENDING",
            started=True,
        )
    except Exception:
        history_id = None
    job_id = None

    if batch.total_count > 0:
        try:
            job_id = jobs_db.enqueue(
                "DINO_BATCH",
                {
                    "batch_id": batch.batch_id,
                    "auto_hybrid": bool(request.auto_hybrid),
                },
                run_history_id=history_id,
            )
        except Exception as exc:
            if history_id is not None:
                try:
                    run_history.update_run(
                        history_id,
                        status="FAILED",
                        message=f"Не удалось поставить DINO batch в очередь: {type(exc).__name__}",
                        finished=True,
                        error_count_delta=1,
                        log_lines=[f"enqueue failed: {type(exc).__name__}"],
                    )
                except Exception:
                    pass
            raise

        _finish_sort_history_enqueue(run_history, history_id, [job_id], batch.total_count)
    else:
        _finish_sort_history_enqueue(run_history, history_id, [], 0)

    return {
        "job_id": job_id,
        "batch_id": batch.batch_id,
        "batch_status": batch.status,
        "total_count": batch.total_count,
    }


def _finish_sort_history_enqueue(history_module, run_id, job_ids, total):
    if run_id is None:
        return
    try:
        history_module.add_jobs(run_id, job_ids)
        # One DINO/HYBRID queue job covers the whole batch: all photos are
        # tracked, none are "untracked".
        history_module.finish_enqueue(run_id, total=total, covered=total)
    except Exception:
        # History is observational; already-created jobs remain authoritative.
        return


@jobs_router.post(
    "/v1/jobs/hybrid",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def enqueue_hybrid(request: HybridRequest):
    from app.runs import coordination

    try:
        with coordination.launch_guard():
            active = coordination.active_operation()

            if active:
                raise HTTPException(
                    status_code=409,
                    detail=coordination.busy_message(active),
                )

            return _enqueue_hybrid_impl(request)
    except coordination.OperationBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _enqueue_hybrid_impl(request: HybridRequest):
    try:
        run, job_id, _history_id = hybrid_db.create_and_enqueue_run(
            request.dino_batch_id,
            history_spec={
                "mode": "manual",
                "title_prefix": "HYBRID run",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

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
    elif request.photo_ids is not None:
        # Explicit list (even an empty one) never falls back to the whole
        # corpus: «Пересканировать» в карточке запускает только это фото.
        photo_ids = request.photo_ids
    else:
        photo_ids = repository.all_photo_ids()

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

    from app.runs import history as run_history

    history_id = run_history.create_run(
        kind="qwen",
        mode="manual",
        title="QWEN: ручной запуск",
        total=len(photo_ids),
    )
    job_ids = []
    skipped = 0

    try:
        for photo_id in photo_ids:
            # Deduplicated: a photo with an active QWEN job is skipped.
            job_id = jobs_db.enqueue_qwen(
                photo_id,
                source="manual",
                provider=request.provider,
                model=request.model,
                run_history_id=history_id,
                # «Пересканировать» в карточке — одно фото: не ждём массовый
                # прогон, который может стоять в очереди часами.
                priority=bool(request.photo_ids and len(request.photo_ids) == 1),
            )

            if job_id is None:
                skipped += 1
            else:
                job_ids.append(job_id)
    except Exception as exc:
        run_history.add_jobs(history_id, job_ids, skipped=skipped)
        run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)
        run_history.update_run(
            history_id,
            status="PARTIAL" if job_ids else "FAILED",
            message=f"Не удалось полностью поставить задания: {type(exc).__name__}",
            finished=True,
            error_count_delta=1,
            log_lines=[f"enqueue failed: {type(exc).__name__}"],
        )
        raise

    run_history.add_jobs(history_id, job_ids, skipped=skipped)
    run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)

    return {
        "jobs": len(job_ids),
        "skipped": skipped,
        "first_job_id": job_ids[0] if job_ids else None,
        "run_history_id": history_id,
    }


@jobs_router.post(
    "/v1/jobs/qwen/rescan",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def rescan_qwen_period(request: QwenRescanRequest):
    """
    Destructive QWEN refresh for one date range.

    Current QWEN rows of the selected photos are copied to
    photo_qwen_history and removed before new QWEN jobs are enqueued.
    """
    if jobs_db.active_count("QWEN_PHOTO"):
        raise HTTPException(
            status_code=409,
            detail="Сначала остановите активное распознавание QWEN",
        )

    photo_ids = qwen_db.photo_ids_in_period(
        date_from=request.date_from,
        date_to=request.date_to,
        date_mode=request.date_mode,
    )
    if not photo_ids:
        raise HTTPException(status_code=422, detail="За выбранный период фотографии не найдены")

    config = qwen.resolve_settings()
    if not config.get("provider") or not config.get("model"):
        raise HTTPException(status_code=422, detail="Модель QWEN не настроена")

    from app.runs import history as run_history

    title = f"QWEN: пересканирование {request.date_from} — {request.date_to}"
    history_id = run_history.create_run(
        kind="qwen",
        mode="manual",
        title=title,
        total=len(photo_ids),
    )

    try:
        archived = qwen_db.archive_and_clear(
            photo_ids, replaced_by_model=str(config["model"])
        )
    except Exception as exc:
        run_history.update_run(
            history_id,
            status="FAILED",
            message=f"Архивирование QWEN не выполнено: {type(exc).__name__}",
            finished=True,
            error_count_delta=1,
        )
        raise

    job_ids = []
    skipped = 0
    try:
        for photo_id in photo_ids:
            job_id = jobs_db.enqueue_qwen(
                photo_id,
                source="manual",
                provider=config["provider"],
                model=config["model"],
                run_history_id=history_id,
            )
            if job_id is None:
                skipped += 1
            else:
                job_ids.append(job_id)
    except Exception as exc:
        run_history.add_jobs(history_id, job_ids, skipped=skipped)
        run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)
        run_history.update_run(
            history_id,
            status="PARTIAL" if job_ids else "FAILED",
            message=f"Очистка выполнена, но очередь QWEN не создана полностью: {type(exc).__name__}",
            finished=True,
            error_count_delta=1,
        )
        raise

    run_history.add_jobs(history_id, job_ids, skipped=skipped)
    run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)

    return {
        "job_id": job_ids[0] if job_ids else None,
        "jobs": len(job_ids),
        "skipped": skipped,
        "photos": len(photo_ids),
        "archived": archived,
        "model": config["model"],
        "run_history_id": history_id,
    }


@jobs_router.post(
    "/v1/jobs/qwen/scan",
    status_code=202,
    dependencies=[Depends(require_scope("jobs:write"))],
)
def scan_qwen_period(request: QwenPeriodScanRequest):
    """
    Non-destructive QWEN catch-up for one date range.

    Only photos without a successful description are enqueued; existing rows
    are never removed. This is the second half of "skip QWEN in the pipeline,
    run it later for the period".
    """

    config = qwen.resolve_settings()

    if not config.get("provider") or not config.get("model"):
        raise HTTPException(status_code=422, detail="Модель QWEN не настроена")

    photo_ids = qwen_db.photo_ids_missing_in_period(
        date_from=request.date_from,
        date_to=request.date_to,
        date_mode=request.date_mode,
        limit=request.limit,
    )

    if not photo_ids:
        return {
            "photos": 0,
            "jobs": 0,
            "skipped": 0,
            "run_history_id": None,
            "model": config["model"],
        }

    from app.runs import history as run_history

    history_id = run_history.create_run(
        kind="qwen",
        mode="manual",
        title=(
            f"QWEN: дозаполнение {request.date_from} — {request.date_to}"
        ),
        total=len(photo_ids),
    )

    job_ids = []
    skipped = 0

    try:
        for photo_id in photo_ids:
            job_id = jobs_db.enqueue_qwen(
                photo_id,
                source="manual",
                provider=config["provider"],
                model=config["model"],
                run_history_id=history_id,
            )

            if job_id is None:
                skipped += 1
            else:
                job_ids.append(job_id)
    except Exception as exc:
        run_history.add_jobs(history_id, job_ids, skipped=skipped)
        run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)
        run_history.update_run(
            history_id,
            status="PARTIAL" if job_ids else "FAILED",
            message=f"Очередь QWEN создана не полностью: {type(exc).__name__}",
            finished=True,
            error_count_delta=1,
        )
        raise

    run_history.add_jobs(history_id, job_ids, skipped=skipped)
    run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)

    return {
        "photos": len(photo_ids),
        "jobs": len(job_ids),
        "skipped": skipped,
        "run_history_id": history_id,
        "model": config["model"],
    }


@jobs_router.post(
    "/v1/jobs/qwen/stop",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def stop_qwen_jobs():
    """
    Остановить распознавание: активные задания QWEN уходят в CANCELLED.

    Текущий запрос к модели доиграет, но результат не публикуется. Уже
    сделанные описания остаются на месте.
    """

    return {"cancelled": jobs_db.cancel_jobs("QWEN_PHOTO")}


@jobs_router.post(
    "/v1/jobs/qwen/clear",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def clear_qwen_jobs():
    """
    Очистить список заданий QWEN: убрать завершённые (DONE/FAILED/CANCELLED).

    Описания живут в `photo_qwen`, поэтому удаляются только строки журнала
    очереди. Активные задания не тронем.
    """

    return {"deleted": jobs_db.clear_finished_jobs("QWEN_PHOTO")}


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
    Cancel a queued, paused, or running job.

    PENDING is never claimed. PAUSED becomes terminal CANCELLED; a running DINO
    job observes cancellation at its next safe checkpoint. Other in-flight
    operations may finish their current step, but mark_done() refuses to publish
    into a cancelled row. A queued/held media search drops its upload because
    the worker that would normally delete it never resumes.

    Unknown job -> 404; a job that already finished -> 409.
    """

    job = jobs_db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    was_queued = (
        job.get("status") in {"PENDING", "PAUSED"}
        and job.get("started_at") is None
    )

    if not jobs_db.mark_cancelled(job_id):
        raise HTTPException(
            status_code=409,
            detail="job is not pending, running, or paused",
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


def _store_media_query(
    file: UploadFile,
    mode: str,
    *,
    frame_seconds: float | None = None,
) -> dict:
    """Store one uploaded query file, verify it, enqueue MEDIA_SEARCH."""

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

    payload = {
        "path": str(stored),
        "filename": stored.name,
        "kind": kind,
        "mode": mode,
    }

    if frame_seconds is not None:
        payload["frame_seconds"] = float(frame_seconds)

    job_id = jobs_db.enqueue("MEDIA_SEARCH", payload)

    return {
        "job_id": job_id,
        "kind": kind,
        "mode": mode,
        "filename": file.filename or stored.name,
        "size_bytes": stored.stat().st_size,
        "media": facts,
    }


@searches_router.post(
    "/v1/search/media",
    status_code=202,
    dependencies=[Depends(require_scope("searches:write"))],
)
def search_by_media(file: UploadFile = File(...)):
    """
    Enqueue a search by one uploaded photo or video (авто-режим).

    The file is stored in a dedicated working folder, verified with a real
    decoder (PIL for photos, OpenCV for video) and dropped when it is neither.
    A video longer than the query limit is refused here, with the reason.
    The QWEN description and the photo search run in the worker
    (job_type MEDIA_SEARCH); poll GET /v1/jobs/media-search/{id} for
    {qwen, filters, photo_ids, count, per_frame}.

    The response carries the file's facts so the window can show them before
    the search starts (format, size, and for a video - duration and frames).
    """

    return _store_media_query(file, "auto")


@searches_router.post(
    "/v1/search/media/describe",
    status_code=202,
    dependencies=[Depends(require_scope("searches:write"))],
)
def describe_media(
    file: UploadFile = File(...),
    frame_seconds: float | None = Form(default=None),
):
    """Ручной режим, шаг 1: только описание QWEN (поля для правки).

    Для видео можно указать frame_seconds — тогда описывается только этот кадр.
    """

    if frame_seconds is not None and frame_seconds < 0:
        raise HTTPException(status_code=422, detail="frame_seconds must be >= 0")

    return _store_media_query(file, "describe", frame_seconds=frame_seconds)


@searches_router.post(
    "/v1/search/query",
    status_code=202,
    dependencies=[Depends(require_scope("searches:write"))],
)
def search_by_query(request: SearchQueryRequest):
    """Ручной режим, шаг 2: поиск по уже собранным/поправленным фильтрам."""

    tags: list[str] = []

    for raw in request.tags or []:
        if not isinstance(raw, str):
            continue

        tag = raw.strip()

        if tag and tag not in tags:
            tags.append(tag)

    filters = {
        "q": request.q,
        "client": request.client,
        "brand": request.brand,
        "category": request.category,
        "tags": tags,
        "address": None,
    }

    if not any(
        filters[key] for key in ("q", "client", "brand", "category", "tags")
    ):
        raise HTTPException(status_code=422, detail="empty query")

    job_id = jobs_db.enqueue("MEDIA_SEARCH", {"filters": filters})

    return {"job_id": job_id, "filters": filters}


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
        mode=request.mode,
        daily_time=request.daily_time,
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


def _principal_user_id(principal) -> str | None:
    """Owner id for per-user records; None for service tokens / open mode."""

    user = principal.get("user") if principal else None
    return str(user["user_id"]) if user else None


@read_router.get("/v1/collections", response_model=None)
def list_collections(principal=Depends(require_scope("read"))):
    return {"items": repository.list_collections(_principal_user_id(principal))}


def _require_member_type(collection: dict, member_type: str) -> None:
    """A collection scope owns exactly one member type."""

    expected = repository.member_type_for_scope(collection.get("scope"))

    if expected and member_type != expected:
        raise HTTPException(
            status_code=422,
            detail=f"collection scope {collection.get('scope')} "
                   f"requires member_type {expected}",
        )


@read_router.get("/v1/collections/{collection_id}/members", response_model=None)
def list_collection_members(
    collection_id: int,
    member_type: str = Query("photo", pattern=r"^(address|client|photo)$"),
    principal=Depends(require_scope("read")),
):
    collection = repository.get_collection(
        collection_id, _principal_user_id(principal)
    )

    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")

    _require_member_type(collection, member_type)

    return {
        "items": repository.collection_member_values(
            collection_id, member_type
        )
    }


@collections_router.post("/v1/collections", status_code=201)
def create_collection(
    request: CollectionCreate,
    principal=Depends(require_scope("collections:write")),
):
    return repository.create_collection(
        name=request.name,
        kind=request.kind,
        client=request.client,
        scope=request.scope,
        user_id=_principal_user_id(principal),
    )


@collections_router.delete("/v1/collections/{collection_id}")
def delete_collection(
    collection_id: int,
    principal=Depends(require_scope("collections:write")),
):
    if not repository.delete_collection(
        collection_id, _principal_user_id(principal)
    ):
        raise HTTPException(status_code=404, detail="collection not found")

    return {"deleted": collection_id}


@collections_router.post("/v1/collections/{collection_id}/members")
def add_collection_members(
    collection_id: int,
    request: CollectionMembersRequest,
    principal=Depends(require_scope("collections:write")),
):
    collection = repository.get_collection(
        collection_id, _principal_user_id(principal)
    )

    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")

    _require_member_type(collection, request.member_type)

    try:
        added = repository.add_collection_members(
            collection_id,
            member_type=request.member_type,
            values=request.values,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"collection_id": collection_id, "added": added}


@collections_router.post("/v1/collections/{collection_id}/members/remove")
def remove_collection_members(
    collection_id: int,
    request: CollectionMembersRequest,
    principal=Depends(require_scope("collections:write")),
):
    collection = repository.get_collection(
        collection_id, _principal_user_id(principal)
    )

    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")

    _require_member_type(collection, request.member_type)

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
def list_saved_searches(principal=Depends(require_scope("read"))):
    return {"items": repository.list_saved_searches(_principal_user_id(principal))}


@searches_router.post("/v1/searches", status_code=201)
def create_saved_search(
    request: SavedSearchCreate,
    principal=Depends(require_scope("searches:write")),
):
    return repository.create_saved_search(
        name=request.name,
        filters=request.filters,
        user_id=_principal_user_id(principal),
    )


@searches_router.delete("/v1/searches/{search_id}")
def delete_saved_search(
    search_id: int,
    principal=Depends(require_scope("searches:write")),
):
    if not repository.delete_saved_search(
        search_id, _principal_user_id(principal)
    ):
        raise HTTPException(status_code=404, detail="saved search not found")

    return {"deleted": search_id}


# ---------------------------------------------------------------------------
# Client aliases (QWEN client name normalization)
# ---------------------------------------------------------------------------


@read_router.get("/v1/client-aliases", response_model=None)
def list_client_aliases(
    kind: str = Query("client", pattern=r"^(client|brand)$"),
):
    """Справочник алиасов: клиенты (`client`) или бренды (`brand`)."""

    return {"items": repository.list_client_aliases(kind)}


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
def list_client_alias_audit(
    limit: int = Query(100, ge=1, le=500),
    kind: str = Query("client", pattern=r"^(client|brand)$"),
):
    """Журнал правок справочника алиасов: кто, что и когда изменил."""

    return {"items": repository.list_client_alias_audit(limit=limit, kind=kind)}


@searches_router.put("/v1/client-aliases")
def upsert_client_alias(
    request: ClientAliasRequest,
    kind: str = Query("client", pattern=r"^(client|brand)$"),
    principal=Depends(require_scope("collections:write")),
):
    return repository.upsert_client_alias(
        request.alias,
        request.canonical,
        kind=kind,
        actor=_actor_name(principal),
    )


@searches_router.delete("/v1/client-aliases")
def delete_client_alias(
    alias: str = Query(..., min_length=1, max_length=200),
    kind: str = Query("client", pattern=r"^(client|brand)$"),
    principal=Depends(require_scope("collections:write")),
):
    if not repository.delete_client_alias(
        alias, kind=kind, actor=_actor_name(principal)
    ):
        raise HTTPException(status_code=404, detail="alias not found")

    return {"deleted": alias, "kind": kind}


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


def _set_session_cookie(response: Response, token: str) -> None:
    """
    Поставить сессионную куку для чтения.

    HttpOnly — из JS её не прочитать; SameSite=Lax — не уходит с чужих сайтов;
    Secure включается настройкой, когда перед API стоит TLS-прокси. Кука
    принимается только для GET/HEAD (app/api/auth.py).
    """

    from app.api.config import COOKIE_MAX_AGE, COOKIE_SECURE, SESSION_COOKIE

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


@auth_router.post("/v1/auth/login")
def login(payload: LoginRequest, http_request: Request, response: Response):
    from app.api import security

    ip = security.client_ip(http_request)

    # Подбор пароля: после серии неудач с одного адреса вход отклоняется
    # до конца окна (SCENE_LOGIN_LOCKOUT=0 отключает).
    wait = security.login_lockout(ip)

    if wait:
        raise HTTPException(
            status_code=429,
            detail=(
                "слишком много неудачных попыток входа с этого адреса; "
                f"повторите через {wait} с"
            ),
            headers={"Retry-After": str(wait)},
        )

    user = users_db.get_user_by_name(payload.name)

    if user is None or not user["active"]:
        security.record_login_failure(ip, payload.name)
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Fail-closed: an account with no password set cannot log in.
    if not has_password(user.get("password_hash")):
        security.record_login_failure(ip, payload.name)
        raise HTTPException(
            status_code=403,
            detail=(
                "no password set for this account; set one with "
                "scripts/set_password.py"
            ),
        )

    if not verify_password(payload.password, user.get("password_hash")):
        security.record_login_failure(ip, payload.name)
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = users_db.create_session(user["user_id"])

    # Удачный вход обнуляет счётчик ошибок этого адреса: опечатки не должны
    # копить блокировку для того, кто в итоге ввёл верный пароль.
    security.clear_login_failures(ip)

    # Учёт посещений. Ошибка записи не должна ломать вход.
    try:
        from app import visits as visits_mod

        visits_mod.record_visit(
            user_id=user["user_id"], user_name=user["name"], event="login",
        )
    except Exception:  # noqa: BLE001 - logging must never block login
        pass

    _set_session_cookie(response, token)

    return {"token": token, "user": _public_user(user)}


@auth_router.post("/v1/auth/logout")
def logout(
    response: Response,
    authorization: str | None = Header(default=None),
):
    from app.api.config import SESSION_COOKIE

    response.delete_cookie(SESSION_COOKIE, path="/")

    token = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    return {"logged_out": bool(token and users_db.delete_session(token))}


@auth_router.get("/v1/auth/me", response_model=None)
def me(response: Response, authorization: str | None = Header(default=None)):
    """
    Public: tells the SPA whether login is required and who is logged in.

    Must stay reachable without a token, otherwise an unauthenticated client
    cannot learn that it needs to authenticate.
    """

    principal = resolve_principal(authorization)
    user = principal.get("user") if principal else None

    # Сессия, начатая до появления куки, получит её при следующем открытии:
    # SPA зовёт /auth/me на старте.
    if user is not None:
        token = None

        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()

        if token:
            _set_session_cookie(response, token)

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
    """
    QWEN card: base size + statuses + last run per trigger.

    `photos` is the base (a photo never described has no photo_qwen row, so the
    status counts alone cannot say how much is left); `runs` gives the last
    finished run of each trigger (manual / automation / pipeline).
    """

    result = repository.qwen_stats()
    result["failed_photo_ids"] = repository.photo_ids_with_qwen_status("FAILED")

    return result


@read_router.get("/v1/hybrid/settings", response_model=None)
def hybrid_settings():
    """Порог уверенности: ниже него фото уходит в «Требуют проверки»."""

    from app.hybrid import config as hybrid_config

    return hybrid_config.resolve_settings()


@read_router.get("/v1/refine/settings", response_model=None)
def refine_settings():
    """
    Настройки этапа «Уточнение» и готовность данных.

    Ручного запуска нет: этап идёт сам после QWEN. Здесь только состояние —
    включён ли, сколько кадров готово (кроп с хешем и описание).
    """

    from app.refine import config as refine_config
    from app.refine.runner import ready_count

    return {**refine_config.resolve_settings(), "photos_ready": ready_count()}


@jobs_router.put(
    "/v1/refine/settings",
    dependencies=[Depends(require_scope("settings:write"))],
)
def update_refine_settings(request: RefineSettingsUpdate):
    from app.refine import config as refine_config

    try:
        if request.enabled is not None:
            refine_config.set_enabled(request.enabled)
        if request.gap_seconds is not None:
            refine_config.set_gap_seconds(request.gap_seconds)
        if request.crop_retention_days is not None:
            refine_config.set_retention_days(request.crop_retention_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return refine_config.resolve_settings()


@read_router.get("/v1/hybrid/settings/preview", response_model=None)
def preview_hybrid_settings(
    low_score: float = Query(0.85, ge=0, le=1),
    min_margin: float = Query(0.0, ge=0, le=1),
):
    """
    Сколько фото попадёт в «Требуют проверки» при таком пороге.

    Ничего не сохраняет: нужно, чтобы подобрать значение по своему корпусу,
    видя результат до нажатия «Сохранить».
    """

    return {
        "low_score": low_score,
        "min_margin": min_margin,
        "review_count": repository.review_count(low_score, min_margin),
    }


@jobs_router.put(
    "/v1/hybrid/settings",
    dependencies=[Depends(require_scope("settings:write"))],
)
def update_hybrid_settings(request: HybridSettingsUpdate):
    from app.hybrid import config as hybrid_config

    try:
        if request.low_score is not None:
            hybrid_config.set_low_score(request.low_score)
        if request.min_margin is not None:
            hybrid_config.set_min_margin(request.min_margin)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return hybrid_config.resolve_settings()


@read_router.get("/v1/qwen/settings", response_model=None)
def qwen_settings():
    """Active QWEN provider settings (api key masked)."""

    return qwen.public_settings()


@jobs_router.put(
    "/v1/qwen/settings",
    dependencies=[Depends(require_scope("settings:write"))],
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
            billboard_crop_enabled=request.billboard_crop_enabled,
            in_pipeline=request.in_pipeline,
            prompt=request.prompt,
            crop_prompt=request.crop_prompt,
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
    dependencies=[Depends(require_scope("settings:write"))],
)
def set_qwen_model(request: QwenModelRequest):
    # Идёт через update_settings: модель запоминается для ТЕКУЩЕГО провайдера,
    # поэтому переключение провайдера не теряет выбор другого.
    return qwen.update_settings(model=request.model)


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
    """Configured working folder plus its preliminary photo/video statistics."""

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
    """Shallow photo/video count and size check; never decodes or saves."""

    return sources.folder_stats(
        sources.resolve_directory(request.path),
        since=request.date_from,
        until=request.date_to,
    )


@jobs_router.post(
    "/v1/previews/backfill",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def queue_missing_previews(
    limit: int = Query(500, ge=1, le=5000),
    request: PreviewBackfillRequest | None = Body(default=None),
):
    """
    Queue a bounded page of registered photos without a preview record.

    With a `{"photo_ids": [...]}` body only those photos are considered —
    the "пересоздать превью по photo_id" path after preview files were
    cleared. Photos whose original is unavailable are reported in
    `originals_missing` and never queued.
    """

    from app.preview.queue import enqueue_missing_previews

    return enqueue_missing_previews(
        limit=limit,
        photo_ids=request.photo_ids if request and request.photo_ids else None,
    )


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
    from app.runs import history as run_history

    # The period belongs in the title: two runs of one folder with different
    # depth are different runs in the history.
    period = ""
    if request.date_from or request.date_to:
        bounds = "—".join(
            value.isoformat() if value else "…"
            for value in (request.date_from, request.date_to)
        )
        mode_label = "съёмка" if request.date_mode == "capture" else "загрузка"
        period = f" ({mode_label}: {bounds})"

    history_id = run_history.create_run(
        kind="ingest",
        mode="manual",
        title=f"Инспектирование: {directory.name}{period}",
        counts={"total": 1},
    )
    job_id = jobs_db.enqueue_ingest(
        str(directory),
        run_history_id=history_id,
        date_from=request.date_from.isoformat() if request.date_from else None,
        date_to=request.date_to.isoformat() if request.date_to else None,
        date_mode=request.date_mode,
    )

    if job_id is None:
        run_history.finish_enqueue(history_id, total=0, skipped=1)
        run_history.update_run(
            history_id,
            status="DONE",
            message="активный ingest этой папки уже запущен; дублирование пропущено",
            finished=True,
        )
    else:
        run_history.add_jobs(history_id, [job_id])
        run_history.finish_enqueue(history_id, total=1)

    return {
        "job_id": job_id,
        "run_history_id": history_id,
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

    from app.runs import coordination
    from app.supervisor import runs as pipeline_runs

    folder = request.folder or sources.current_folder() or None

    if folder:
        folder = str(sources.resolve_directory(folder))

    try:
        with coordination.launch_guard():
            active = coordination.active_operation()

            if active:
                raise HTTPException(
                    status_code=409,
                    detail=coordination.busy_message(active),
                )

            run = pipeline_runs.create_run(
                mode=request.mode,
                folder=folder,
                skip_qwen=request.skip_qwen,
                skip_refine=request.skip_refine,
            )
    except coordination.OperationBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except pipeline_runs.PipelineBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return run


@jobs_router.post(
    "/v1/pipeline/{run_id}/stop",
    dependencies=[Depends(require_scope("jobs:write"))],
)
def stop_pipeline_run(run_id: int, principal=Depends(require_scope("jobs:write"))):
    from app.supervisor import runs as pipeline_runs

    # Имя в журнале: видно, кто приостановил процесс.
    user = principal.get("user") if principal else None
    stopped_by = (user or {}).get("name")

    if not pipeline_runs.request_stop(run_id, stopped_by=stopped_by):
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


@addresses_router.put(
    "/v1/photos/{photo_id}/address",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def set_photo_address(photo_id: str, request: PhotoAddressRequest):
    """Override the recognised legal address of one photo."""

    photo_id = _validate_photo_id(photo_id)

    if repository.get_photo(photo_id) is None:
        raise HTTPException(status_code=404, detail="photo not found")

    address = directory_mod.get_address(request.address_id)

    if address is None:
        raise HTTPException(status_code=404, detail="address not found")

    # The panel lists active legal addresses only; an override to an archived
    # row would be invisible in the panel but still matched by the grid filter.
    if not address.get("active"):
        raise HTTPException(status_code=422, detail="address is inactive")

    return repository.set_photo_address_override(photo_id, request.address_id)


@addresses_router.delete(
    "/v1/photos/{photo_id}/address",
    response_model=None,
    dependencies=[Depends(require_scope("addresses:write"))],
)
def clear_photo_address(photo_id: str):
    """Drop the manual override; the recognition result applies again."""

    photo_id = _validate_photo_id(photo_id)

    if repository.get_photo(photo_id) is None:
        raise HTTPException(status_code=404, detail="photo not found")

    return {
        "photo_id": photo_id,
        "cleared": repository.clear_photo_address_override(photo_id),
    }


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

    before = fingerprints_mod.get_fingerprint(fingerprint_id)

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

    result = dict(updated)

    active_changed = (
        request.active is not None
        and before is not None
        and bool(before.get("active")) != bool(request.active)
    )

    if active_changed:
        # Hiding or re-enabling a fingerprint changes the ranking for every
        # photo, so the stored DINO/HYBRID verdicts must be recalculated.
        try:
            from app.dino.recalc import enqueue_recalculation

            recalc = enqueue_recalculation(
                reason="скрытия" if not request.active else "включения",
                fingerprint_id=fingerprint_id,
            )
            if recalc is not None:
                result["recalc"] = recalc
        except Exception as exc:  # noqa: BLE001 - the toggle itself succeeded
            result["recalc_error"] = type(exc).__name__

    return result


@fingerprints_router.delete(
    "/v1/fingerprints/registry/{fingerprint_id}",
    response_model=None,
    dependencies=[Depends(require_scope("settings:write"))],
)
def delete_fingerprint_registry(fingerprint_id: str):
    """
    Delete one fingerprint: registry row, address link and vector files.

    Admin-only: the operation is irreversible (a fingerprint can be rebuilt,
    but its versions and address mapping are gone). Historical DINO/HYBRID
    results keep the id as text and are not touched.
    """

    try:
        deleted = fingerprints_mod.delete_fingerprint(fingerprint_id)
    except fingerprints_mod.FingerprintError as exc:
        raise _fingerprint_error(exc) from exc

    if deleted is None:
        raise HTTPException(status_code=404, detail="fingerprint not found")

    return deleted


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
        # A replacement of an existing fingerprint makes every stored verdict
        # stale; the builder queues one full DINO+HYBRID pass after publishing
        # the new vectors. A brand-new fingerprint ignores this flag.
        recalculate=True,
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
            recalculate=True,
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

"""
Бэкапы и восстановление из технического раздела («Данные» → «Бэкапы»).

Чтение (пути, расписание, состав архивов) — со scope `read`; всё, что
что-то меняет, — со scope `settings:write`, то есть только Администратор.

Сами бэкапы и восстановления выполняются воркером (виды работ BACKUP и
RESTORE): HTTP-запрос не должен ждать дамп на 50 МБ. Восстановление в
рабочую базу и «на место» дополнительно требуют, чтобы оператор ввёл имя
базы (или слово «на место») — это страховка от промаха, а не от недоверия
к администратору.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import require_scope
from app.backup import service
from app.jobs import database as jobs_db


read_router = APIRouter()
write_router = APIRouter()

# То, что оператор вводит для восстановления поверх рабочей установки.
IN_PLACE_CONFIRM = "на место"


class BackupRunRequest(BaseModel):
    """Ручной бэкап: база данных, файлы данных или всё вместе."""

    parts: list[Literal["database", "data", "models"]] = Field(
        default_factory=lambda: ["database", "data"]
    )
    allow_same_filesystem: bool = False


class BackupRestoreRequest(BaseModel):
    """Восстановление: целиком, по частям или отдельные файлы архива."""

    file: str
    target: Literal["files", "database"] = "files"
    members: list[str] | None = None
    target_dir: str | None = None
    target_db: str | None = None
    in_place: bool = False
    overwrite: bool = False
    allow_production: bool = False
    confirm: str | None = None


class BackupSettingsRequest(BaseModel):
    """Каталог бэкапов и сроки хранения."""

    backup_dir: str | None = None
    retention: dict[str, int] | None = None


@read_router.get(
    "/v1/backup/status",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_backup_status():
    """Пути, расписание, состояние диска и список бэкапов."""

    return service.status()


@read_router.get(
    "/v1/backup/archive/{name}",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_backup_archive(name: str):
    """Состав архива данных — чтобы восстановить отдельные файлы."""

    try:
        members = service.archive_members(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="файл бэкапа не найден") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"file": name, "members": members, "total": len(members)}


@write_router.post(
    "/v1/backup/run",
    response_model=None,
    dependencies=[Depends(require_scope("settings:write"))],
)
def run_backup(request: BackupRunRequest):
    """Поставить ручной бэкап в очередь."""

    if not request.parts:
        raise HTTPException(status_code=422, detail="выберите, что копировать")

    payload = {
        "parts": list(request.parts),
        "allow_same_filesystem": request.allow_same_filesystem,
    }

    job_id = jobs_db.enqueue("BACKUP", payload)

    return {"job_id": job_id, "parts": payload["parts"]}


@write_router.post(
    "/v1/backup/restore",
    response_model=None,
    dependencies=[Depends(require_scope("settings:write"))],
)
def run_restore(request: BackupRestoreRequest):
    """Поставить восстановление в очередь."""

    try:
        service.resolve_artifact(request.file)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="файл бэкапа не найден") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    payload: dict = {"file": request.file, "target": request.target}

    if request.target == "database":
        target_db = (request.target_db or "").strip()

        if not target_db:
            raise HTTPException(status_code=422, detail="укажите базу данных")

        working = service.working_db_name()

        if target_db == working:
            # Рабочая база — только если оператор ввёл её имя.
            if (request.confirm or "").strip() != working:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"для восстановления в рабочую базу {working} введите её имя "
                        "в поле подтверждения"
                    ),
                )
            payload["allow_production"] = True
        else:
            payload["target_db"] = target_db
    else:
        payload["members"] = request.members
        payload["target_dir"] = request.target_dir
        payload["in_place"] = request.in_place
        payload["overwrite"] = request.overwrite

        if request.in_place:
            if (request.confirm or "").strip().lower() != IN_PLACE_CONFIRM:
                raise HTTPException(
                    status_code=409,
                    detail="для восстановления «на место» введите слово «на место»",
                )
            payload["overwrite"] = True

    job_id = jobs_db.enqueue("RESTORE", payload)

    return {"job_id": job_id, "target": request.target, "file": request.file}


@write_router.put(
    "/v1/backup/settings",
    response_model=None,
    dependencies=[Depends(require_scope("settings:write"))],
)
def update_backup_settings(request: BackupSettingsRequest):
    """Каталог бэкапов и сроки хранения (в app_settings)."""

    stored = service.stored_settings()

    if request.backup_dir is not None:
        directory = request.backup_dir.strip()

        if not directory:
            raise HTTPException(status_code=422, detail="каталог не может быть пустым")

        if directory.startswith("~"):
            directory = str(Path(directory).expanduser())

        stored["backup_dir"] = directory

    if request.retention is not None:
        keep = dict(service.retention())

        for key in ("keep_daily", "keep_weekly", "keep_monthly"):
            value = request.retention.get(key)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise HTTPException(status_code=422, detail=f"{key}: нужно целое число ≥ 0")
            if key == "keep_daily" and value < 1:
                raise HTTPException(status_code=422, detail="keep_daily: нужно ≥ 1")
            keep[key] = value

        stored["retention"] = keep

    service.save_settings(stored)

    return service.status()

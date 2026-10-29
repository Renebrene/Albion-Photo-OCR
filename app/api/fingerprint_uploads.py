"""
Временная папка для сборки слепка из фотографий с другого компьютера.

Зачем: эталонные фото лежат на машине менеджера, а сборка слепка идёт на
сервере. Браузер не может отдать папку путём, поэтому файлы приезжают по одному
и складываются в собственную временную папку сервера; сборщик читает её как
обычную папку, а после задания она удаляется.

Правила безопасности (как у загрузки фото в INGEST):

* имя файла очищается, путь строит сервер (`data/inbox/fingerprints/<билет>`),
  клиентский путь не используется никогда;
* ограничены число файлов, размер одного файла и суммарный объём;
* каждый файл проверяется декодером (PIL): не изображение — отказ, файл
  удаляется;
* ничего не перезаписывается: при совпадении имени добавляется суффикс;
* билет — 32 hex-символа, выданный сервером; чужой билет не угадать, а папки
  старше `SCENE_FINGERPRINT_UPLOAD_STALE_HOURS` подметаются при создании
  следующей загрузки.
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from pathlib import Path

from app.api.upload import INBOX
from app.core.image import EXTENSIONS

STAGING_ROOT = INBOX / "fingerprints"

# 150 фото на слепок с запасом покрывают реальные подборки (20-30 снимков), но
# не дают залить на сервер произвольный объём.
MAX_FILES = int(os.getenv("SCENE_FINGERPRINT_UPLOAD_FILES", "150"))
MAX_FILE_BYTES = int(
    os.getenv("SCENE_FINGERPRINT_UPLOAD_FILE_BYTES", str(25 * 1024 * 1024))
)
MAX_TOTAL_BYTES = int(
    os.getenv("SCENE_FINGERPRINT_UPLOAD_TOTAL_BYTES", str(1024 * 1024 * 1024))
)
STALE_HOURS = float(os.getenv("SCENE_FINGERPRINT_UPLOAD_STALE_HOURS", "24"))

_UPLOAD_ID = re.compile(r"^[0-9a-f]{32}$")
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_CHUNK = 1024 * 1024


class UploadError(ValueError):
    """Загрузка отклонена (лимит, имя, содержимое)."""


def _check_id(upload_id: str) -> str:
    if not isinstance(upload_id, str) or not _UPLOAD_ID.match(upload_id):
        raise UploadError("неизвестная загрузка")

    return upload_id


def folder(upload_id: str) -> Path:
    """Папка загрузки; чужой или неизвестный билет — ошибка."""

    target = STAGING_ROOT / _check_id(upload_id)

    if not target.is_dir():
        raise UploadError("загрузка не найдена или уже завершена")

    return target


def _total_bytes(target: Path) -> int:
    return sum(
        entry.stat().st_size
        for entry in os.scandir(target)
        if entry.is_file(follow_symlinks=False)
    )


def _file_count(target: Path) -> int:
    return sum(
        1 for entry in os.scandir(target) if entry.is_file(follow_symlinks=False)
    )


def _safe_name(name: str | None) -> str:
    base = os.path.basename(str(name or "")).strip()
    base = _SAFE_CHARS.sub("_", base)

    if base in {"", ".", ".."}:
        raise UploadError("недопустимое имя файла")

    if Path(base).suffix.lower() not in EXTENSIONS:
        raise UploadError("поддерживаются только изображения")

    return base


def _unique_path(target: Path, name: str) -> Path:
    candidate = target / name

    if not candidate.exists():
        return candidate

    stem, suffix = Path(name).stem, Path(name).suffix
    index = 1

    while True:
        candidate = target / f"{stem}_{index}{suffix}"

        if not candidate.exists():
            return candidate

        index += 1


def _verify_image(path: Path) -> None:
    """Настоящее изображение? Проверяет декодер, а не расширение."""

    from PIL import Image

    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:  # noqa: BLE001 - любой сбой декодера = отказ
        raise UploadError("файл не читается как изображение") from exc


def sweep_stale(now: float | None = None) -> int:
    """Удалить папки брошенных загрузок старше срока. Возвращает число папок."""

    if not STAGING_ROOT.is_dir():
        return 0

    deadline = (now if now is not None else time.time()) - STALE_HOURS * 3600
    removed = 0

    for entry in os.scandir(STAGING_ROOT):
        if not entry.is_dir(follow_symlinks=False):
            continue

        try:
            if entry.stat(follow_symlinks=False).st_mtime < deadline:
                shutil.rmtree(entry.path, ignore_errors=True)
                removed += 1
        except OSError:
            continue

    return removed


def create_session() -> dict:
    """Новая загрузка: билет и лимиты, которые покажет интерфейс."""

    sweep_stale()
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)

    upload_id = uuid.uuid4().hex
    (STAGING_ROOT / upload_id).mkdir(mode=0o700)

    return {
        "upload_id": upload_id,
        "max_files": MAX_FILES,
        "max_file_bytes": MAX_FILE_BYTES,
        "max_total_bytes": MAX_TOTAL_BYTES,
    }


def store_file(upload_id: str, filename: str | None, stream, size: int | None = None) -> dict:
    """
    Сохранить один файл загрузки.

    *stream* — файловый объект с `.read(n)`. Размер проверяется по факту
    (заголовку Content-Length верить нельзя), запись идёт в временный файл и
    переименовывается только после проверки декодером.
    """

    target = folder(upload_id)
    name = _safe_name(filename)

    if _file_count(target) >= MAX_FILES:
        raise UploadError(f"слишком много файлов: не больше {MAX_FILES}")

    if size is not None and size > MAX_FILE_BYTES:
        raise UploadError("файл больше допустимого размера")

    used = _total_bytes(target)

    if used >= MAX_TOTAL_BYTES:
        raise UploadError("превышен общий объём загрузки")

    destination = _unique_path(target, name)
    temporary = destination.with_name(destination.name + ".part")
    written = 0

    try:
        with open(temporary, "wb") as handle:
            while True:
                block = stream.read(_CHUNK)

                if not block:
                    break

                written += len(block)

                if written > MAX_FILE_BYTES or used + written > MAX_TOTAL_BYTES:
                    raise UploadError("превышен предельный размер загрузки")

                handle.write(block)

        _verify_image(temporary)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return {
        "name": destination.name,
        "received": _file_count(target),
        "bytes": written,
        "total_bytes": used + written,
    }


def stats(upload_id: str) -> dict:
    target = folder(upload_id)

    return {
        "upload_id": upload_id,
        "files": _file_count(target),
        "total_bytes": _total_bytes(target),
        "max_files": MAX_FILES,
        "max_total_bytes": MAX_TOTAL_BYTES,
    }


def delete_session(upload_id: str) -> bool:
    """Удалить загрузку (отмена или уборка после сборки)."""

    try:
        target = STAGING_ROOT / _check_id(upload_id)
    except UploadError:
        return False

    if not target.is_dir():
        return False

    shutil.rmtree(target, ignore_errors=True)

    return True

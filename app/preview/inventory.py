"""
Инвентаризация превью: сколько их, сколько места занимают и какие остались без
оригиналов.

Превью — производные файлы: их можно удалить и пересоздать кнопкой
«Пересоздать превью». Пока оригинал на месте, удаление безопасно, но если
оригинал пропал, превью вводит в заблуждение: карточка открывается, а
«посмотреть/скачать» отвечает «оригинал недоступен». Поэтому инспектор
показывает:

* число фото с превью и суммарный вес файлов (SMALL и MIDDLE отдельно);
* превью без оригиналов, разложенные по причинам;
* кнопку очистки — только для тех превью, где оригинал действительно удалён.

Опасные случаи намеренно **не** чистятся:

* ``root_unavailable`` — отмонтирован том, файлы на месте, лечится монтированием
  или переносом путей;
* ``directory_missing`` — нет каталога оригинала: папку переименовали или
  перенесли, чистка стёрла бы годные превью. Лечится
  ``scripts/remap_source_root.py``;
* ``outside_roots`` — путь вне разрешённых корней: ошибка конфигурации.

Удаляются только записи и файлы превью; записи фото и оригиналы не трогаются.
Перед удалением пишется отчёт ``data/reports/previews_orphans_purged_*.json``.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.api.config import ORIGINALS_ROOTS, PREVIEW_ROOT
from app.api.file_access import (
    ORIGINAL_MISSING,
    ORIGINAL_NOT_CONFIGURED,
    ORIGINAL_OK,
    ORIGINAL_OUTSIDE_ROOTS,
    ORIGINAL_ROOT_UNAVAILABLE,
    original_availability,
)
from app.ingest.database import get_connection
from app.preview import formats

SIZES = ("small", "middle")
SAMPLE_LIMIT = 50

PHOTO_MISSING = "photo_missing"
FILE_MISSING = "file_missing"
DIRECTORY_MISSING = "directory_missing"
ROOT_UNAVAILABLE = "root_unavailable"
OUTSIDE_ROOTS = "outside_roots"

REASONS = {
    PHOTO_MISSING: "записи фото нет, превью осталось",
    FILE_MISSING: "оригинал удалён, каталог на месте",
    DIRECTORY_MISSING: "каталог оригинала отсутствует (переименование или переезд)",
    ROOT_UNAVAILABLE: "корень оригиналов не подключён",
    OUTSIDE_ROOTS: "оригинал вне разрешённых корней",
}

# Чистить можно только то, в чём уверены: записи фото нет или файла нет при
# живом каталоге. Остальное — признак отключённого тома или переезда папки.
PURGEABLE = frozenset({PHOTO_MISSING, FILE_MISSING})


def _size_dirs() -> dict[str, Path]:
    root = Path(PREVIEW_ROOT)
    return {size: root / size for size in SIZES}


def _scan_files(directory: Path) -> tuple[dict[str, int], int]:
    """Имена файлов каталога и их размеры; отсутствующий каталог — пусто."""

    files: dict[str, int] = {}
    total = 0

    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
                files[entry.name] = size
                total += size
    except (FileNotFoundError, NotADirectoryError):
        pass
    except OSError:
        pass

    return files, total


def _preview_paths(path_value: str | None) -> list[Path]:
    """Сохранённый путь плюс прежние форматы (JPEG рядом с WebP и наоборот)."""

    if not path_value:
        return []

    path = Path(path_value)
    return [candidate for candidate in formats.candidate_paths(path)]


class _DirectoryCache:
    """
    Статус каталогов оригиналов: `resolve()` на каждую строку — это десятки
    тысяч системных вызовов. Фото лежат в тысячах каталогов, поэтому статус
    каталога (корень подключён, путь внутри корней, каталог существует)
    считается один раз.
    """

    def __init__(self, roots: list[Path]):
        self._roots = roots
        self._status: dict[str, str] = {}
        self._exists: dict[str, bool] = {}

    def classify(self, source_path: str) -> str:
        """Причина для отсутствующего файла (существующие сюда не попадают)."""

        directory = os.path.dirname(str(source_path))

        if directory not in self._status:
            # Пробник в каталоге: нас интересует статус самого каталога и
            # корня, а не конкретного файла.
            probe = os.path.join(directory, ".inventory-probe")
            self._status[directory] = original_availability(probe, self._roots)

            try:
                self._exists[directory] = Path(directory).is_dir()
            except OSError:
                self._exists[directory] = False

        status = self._status[directory]

        if status in (ORIGINAL_ROOT_UNAVAILABLE, ORIGINAL_NOT_CONFIGURED):
            return ROOT_UNAVAILABLE

        if status == ORIGINAL_OUTSIDE_ROOTS:
            return OUTSIDE_ROOTS

        if status != ORIGINAL_MISSING:
            return ROOT_UNAVAILABLE

        # Каталога нет — это переименование/переезд, а не удалённое фото:
        # такие превью не чистим.
        return FILE_MISSING if self._exists[directory] else DIRECTORY_MISSING


def _collect() -> tuple[dict, list[dict]]:
    """Сводка по превью и полный список «сирот» с причинами."""

    files: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {}

    for size, directory in _size_dirs().items():
        files[size], totals[size] = _scan_files(directory)

    known: dict[str, set[str]] = {size: set() for size in SIZES}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.photo_id, v.small_path, v.middle_path,
                       p.photo_id IS NOT NULL AS has_photo,
                       p.source_path
                FROM public.photo_previews AS v
                LEFT JOIN public.photos AS p ON p.photo_id = v.photo_id
                """
            )
            rows = cur.fetchall()

    items: list[dict] = []
    directories = _DirectoryCache(ORIGINALS_ROOTS)

    for photo_id, small_path, middle_path, has_photo, source_path in rows:
        stored = {"small": small_path, "middle": middle_path}
        candidates = {
            size: _preview_paths(stored[size]) for size in SIZES
        }

        for size in SIZES:
            for candidate in candidates[size]:
                known[size].add(candidate.name)

        if not has_photo:
            reason = PHOTO_MISSING
        else:
            try:
                original_present = bool(source_path) and os.path.isfile(
                    str(source_path)
                )
            except OSError:
                original_present = False

            reason = (
                ""
                if original_present
                else directories.classify(str(source_path or ""))
            )

        if not reason:
            continue

        present = [
            candidate
            for size in SIZES
            for candidate in candidates[size]
            if candidate.is_file()
        ]

        items.append(
            {
                "photo_id": str(photo_id),
                "reason": reason,
                "reason_label": REASONS.get(reason, reason),
                "bytes": sum(
                    files[size].get(candidate.name, 0)
                    for size in SIZES
                    for candidate in candidates[size]
                    if candidate.is_file()
                ),
                "files": [str(path) for path in present],
            }
        )

    # Файлы превью, на которые нет записи в photo_previews (например, запись
    # удалили, файл остался). Имя файла — photo_id.
    for size in SIZES:
        for name, size_bytes in files[size].items():
            if name in known[size]:
                continue
            items.append(
                {
                    "photo_id": Path(name).stem,
                    "reason": PHOTO_MISSING,
                    "reason_label": REASONS[PHOTO_MISSING],
                    "bytes": size_bytes,
                    "files": [str(_size_dirs()[size] / name)],
                }
            )

    summary = {
        "previews": {
            "photos": len(rows),
            "files": len(files["small"]) + len(files["middle"]),
            "bytes": totals["small"] + totals["middle"],
            "small": {"files": len(files["small"]), "bytes": totals["small"]},
            "middle": {"files": len(files["middle"]), "bytes": totals["middle"]},
        },
        "orphans": {
            "count": len(items),
            "bytes": sum(item["bytes"] for item in items),
            "purgeable": sum(1 for item in items if item["reason"] in PURGEABLE),
            "purgeable_bytes": sum(
                item["bytes"] for item in items if item["reason"] in PURGEABLE
            ),
            "reasons": {
                reason: sum(1 for item in items if item["reason"] == reason)
                for reason in REASONS
                if any(item["reason"] == reason for item in items)
            },
        },
        "roots": [
            {"path": str(root), "available": root.is_dir()}
            for root in ORIGINALS_ROOTS
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return summary, items


def scan() -> dict:
    """Сводка для инспектора; подробные пути остаются на сервере."""

    summary, items = _collect()

    summary["orphans"]["samples"] = [
        {
            "photo_id": item["photo_id"],
            "reason": item["reason"],
            "reason_label": item["reason_label"],
            "bytes": item["bytes"],
        }
        for item in items[:SAMPLE_LIMIT]
    ]

    return summary


def reports_dir() -> Path:
    data = Path(os.getenv("SCENE_DATA", str(Path(__file__).resolve().parents[2] / "data")))
    return data / "reports"


def _write_report(payload: dict) -> Path:
    """Временный файл → запись → атомарная публикация."""

    directory = reports_dir()
    directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = directory / f"previews_orphans_purged_{stamp}.json"

    handle, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise

    return target


def _inside_preview_root(path: Path) -> bool:
    """Удалять можно только файлы внутри каталога превью."""

    try:
        resolved = path.resolve(strict=False)
        root = Path(PREVIEW_ROOT).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return False

    return resolved == root or root in resolved.parents


def purge_orphans() -> dict:
    """Удалить превью без оригиналов (только безопасные причины)."""

    summary, items = _collect()
    targets = [item for item in items if item["reason"] in PURGEABLE]

    deleted_files = 0
    freed = 0
    removed_photos: list[str] = []

    for item in targets:
        for path_value in item["files"]:
            path = Path(path_value)

            if not _inside_preview_root(path):
                continue

            try:
                size = path.stat().st_size
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                continue

            deleted_files += 1
            freed += size

        removed_photos.append(item["photo_id"])

    if removed_photos:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.photo_previews WHERE photo_id = ANY(%s)",
                    (removed_photos,),
                )

    report = _write_report(
        {
            "generated_at": summary["generated_at"],
            "photos": len(removed_photos),
            "deleted_files": deleted_files,
            "freed_bytes": freed,
            "photo_ids": removed_photos,
            "skipped": {
                reason: count
                for reason in REASONS
                if reason not in PURGEABLE
                and (count := summary["orphans"]["reasons"].get(reason, 0))
            },
        }
    )

    return {
        "photos": len(removed_photos),
        "deleted_files": deleted_files,
        "freed_bytes": freed,
        "skipped": sum(
            1 for item in items if item["reason"] not in PURGEABLE
        ),
        "report": str(report),
    }

"""
Записи видео без файла: поиск и удаление мёртвых строк реестра.

Проверка идёт в двух режимах:

* **по папке** (`scope`) — инспекция просканировала папку, и удаляются только
  строки, чей `source_path` лежит внутри неё. Проверка «файл есть» —
  обычный `os.path.isfile()`: `SCENE_ORIGINALS_ROOTS` отвечает за выдачу
  оригинала API, а не за его наличие на диске, и папка вне этих корней
  инспектируется так же. Шире папки удалять нельзя: у отключённого тома
  файла «нет» ровно так же, как у удалённого, и однажды выключенный диск
  стёр бы весь реестр.
* **по всему реестру** (без `scope`, `scripts/purge_missing_videos.py`) —
  строка считается мёртвой, только если её пути нет ни по одному
  разрешённому корню. Вручную удалять запись, которая существует, но не
  отдаётся API, должен решать человек.

Перед удалением полные строки и связанные производные пишутся в
`data/reports/video_records_removed_<штамп>.json` — это след, а не откат:
восстановить строку можно вставкой в `video_assets`, но идентификаторы
производных и билетов были свои. Производные и билеты удаляются каскадом
внешних ключей.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.api.config import ORIGINALS_ROOTS, VIDEO_DERIVATIVES_ROOT
from app.api.repository import get_connection
from app.video.transcode import derivatives_root

REPORT_DIR = Path(os.getenv("SCENE_DATA", "data")) / "reports"
REPORT_PREFIX = "video_records_removed"


def allowed_roots() -> list[str]:
    """Корни, внутри которых запись считается доступной API."""

    roots = [str(root) for root in ORIGINALS_ROOTS]
    derivative_root = str(derivatives_root() or VIDEO_DERIVATIVES_ROOT)
    if derivative_root not in roots:
        roots.append(derivative_root)
    return roots


def json_ready(row: dict) -> dict:
    """Даты в ISO: след пишется в JSON, а не в SQL-дамп."""

    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }


def exists(source_path: str | None) -> bool:
    return bool(source_path) and os.path.isfile(source_path)


def has_file(source_path: str | None, roots: list[str] | None = None) -> bool:
    """Файл на месте и внутри разрешённого корня? Путь вне корней — «нет»."""

    if not source_path:
        return False

    for root in allowed_roots() if roots is None else roots:
        root = str(root)
        if source_path == root or source_path.startswith(root.rstrip("/") + "/"):
            return os.path.isfile(source_path)

    return False


def inside(source_path: str | None, directory: str) -> bool:
    """`source_path` лежит внутри папки? Сосед `/video-old` — не внутри `/video`."""

    if not source_path:
        return False

    try:
        # commonpath сравнивает сегменты пути, а не префикс строки.
        return os.path.commonpath(
            [os.path.abspath(source_path), directory]
        ) == directory
    except ValueError:
        # Разные диски (Windows) или относительный путь против абсолютного.
        return False


def _rows() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT video_id, filename, source_path, parent_video_id,
                       display_title, size_bytes, duration_seconds, created_at
                FROM public.video_assets
                ORDER BY video_id
                """
            )
            columns = [description[0] for description in cur.description]
            return [
                json_ready(dict(zip(columns, row))) for row in cur.fetchall()
            ]


def _derivatives(video_ids: list[str]) -> list[dict]:
    if not video_ids:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT derivative_id, video_id, profile, status, output_path,
                       output_sha256, created_at
                FROM public.video_derivatives
                WHERE video_id = ANY(%s)
                ORDER BY derivative_id
                """,
                (video_ids,),
            )
            columns = [description[0] for description in cur.description]
            return [
                json_ready(dict(zip(columns, row))) for row in cur.fetchall()
            ]


def _is_missing(
    row: dict,
    *,
    scope: str | None,
    roots: list[str] | None,
) -> bool:
    """Одно правило отбора — им же проверяем строки перед удалением."""

    if scope is not None:
        return inside(row["source_path"], scope) and not exists(row["source_path"])

    return not has_file(row["source_path"], roots)


def _missing_from(
    rows: list[dict],
    *,
    scope: str | None = None,
    roots: list[str] | None = None,
) -> list[dict]:
    directory = os.path.abspath(scope) if scope is not None else None

    return [
        row for row in rows if _is_missing(row, scope=directory, roots=roots)
    ]


def missing_records(
    *,
    scope: str | Path | None = None,
    roots: list[str] | None = None,
) -> list[dict]:
    """Строки реестра, у которых нет файла (по папке или по всему реестру)."""

    return _missing_from(
        _rows(), scope=str(scope) if scope is not None else None, roots=roots
    )


def _report_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"{REPORT_PREFIX}_{stamp}.json"

    # Две инспекции в одну секунду не должны перезаписать чужой след.
    counter = 2
    while path.exists():
        path = REPORT_DIR / f"{REPORT_PREFIX}_{stamp}_{counter}.json"
        counter += 1

    return path


def purge_missing_records(
    *,
    scope: str | Path | None = None,
    apply: bool = True,
    roots: list[str] | None = None,
) -> dict:
    """
    Найти записи без файла и (по `apply`) удалить их.

    Возвращает сводку: сколько проверено, сколько мёртвых, сколько удалено и
    куда сохранён след. Без `apply` ничего не меняет — режим показа.
    """

    scope_value = str(scope) if scope is not None else None
    rows = _rows()
    missing = _missing_from(rows, scope=scope_value, roots=roots)

    payload: dict = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "missing": len(missing),
        "records": missing,
        "scope": scope_value,
    }

    if not missing:
        payload.update(applied=False, deleted=0, report=None)
        return payload

    if not apply:
        payload.update(applied=False, deleted=0, report=None)
        return payload

    # След до удаления: полные строки и связанные производные.
    video_ids = [row["video_id"] for row in missing]
    payload["derivatives"] = _derivatives(video_ids)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _report_path()
    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)

    # Удаляем только те строки, у которых файла нет и сейчас: между показом и
    # удалением том мог вернуться. Правило отбора то же, что выше.
    directory = os.path.abspath(scope_value) if scope_value is not None else None
    still_missing = [
        row["video_id"]
        for row in missing
        if _is_missing(row, scope=directory, roots=roots)
    ]

    deleted: list[str] = []
    if still_missing:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.video_assets"
                    " WHERE video_id = ANY(%s) RETURNING video_id",
                    (still_missing,),
                )
                deleted = [row[0] for row in cur.fetchall()]

    payload.update(applied=True, deleted=len(deleted), report=str(report_path))
    return payload

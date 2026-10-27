"""
Полная пофайловая проверка доступности оригиналов.

Сводка `GET /v1/originals/health` отвечает, подключён ли том, но не говорит,
все ли файлы на месте. Здесь — постраничный обход `photos` с
`original_availability()`: 57 тыс. `stat`, поэтому это задание воркера
(`ORIGINALS_CHECK`), а не HTTP-обработчик. Отчёт пишется в
`<SCENE_DATA>/reports/originals_health_<штамп>.json` и переживает перезапуск
воркера: последний отчёт показывается в техническом разделе.

Тот же обход использует `scripts/check_originals.py` для ручной проверки —
счётчики и причины у них общие, поэтому «в скрипте одно, в панели другое»
получиться не может.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.api.file_access import (
    ORIGINAL_MISSING,
    ORIGINAL_NOT_CONFIGURED,
    ORIGINAL_OK,
    ORIGINAL_OUTSIDE_ROOTS,
    ORIGINAL_ROOT_UNAVAILABLE,
    original_availability,
)
from app.ingest.database import get_connection

REPO = Path(__file__).resolve().parents[2]
PAGE = 2000
SAMPLE_LIMIT = 50

# Причины в том виде, в каком их видит оператор.
REASONS = {
    ORIGINAL_MISSING: "файл не найден",
    ORIGINAL_OUTSIDE_ROOTS: "путь вне разрешённых корней",
    ORIGINAL_ROOT_UNAVAILABLE: "корень оригиналов не подключён",
    ORIGINAL_NOT_CONFIGURED: "SCENE_ORIGINALS_ROOTS не задан",
}


def reports_dir() -> Path:
    """Каталог отчётов рядом с остальными данными (`SCENE_DATA/reports`)."""

    data = Path(os.getenv("SCENE_DATA", str(REPO / "data"))).expanduser()
    return data / "reports"


def _rows(photo_ids: list[str] | None, limit: int):
    """Порциями отдаёт (photo_id, source_path) по всей таблице."""

    cursor = None
    seen = 0

    while True:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if photo_ids:
                    cur.execute(
                        """SELECT photo_id, source_path FROM public.photos
                           WHERE photo_id = ANY(%s) ORDER BY photo_id""",
                        (sorted(set(photo_ids)),),
                    )
                else:
                    cur.execute(
                        """SELECT photo_id, source_path FROM public.photos
                           WHERE (%s::text IS NULL OR photo_id > %s)
                           ORDER BY photo_id LIMIT %s""",
                        (cursor, cursor, PAGE),
                    )
                rows = cur.fetchall()

        if not rows:
            return
        cursor = str(rows[-1][0])
        for photo_id, source_path in rows:
            yield str(photo_id), source_path
            seen += 1
            if limit and seen >= limit:
                return
        if photo_ids:
            return


def _total(photo_ids: list[str] | None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if photo_ids:
                cur.execute(
                    "SELECT count(*) FROM public.photos WHERE photo_id = ANY(%s)",
                    (sorted(set(photo_ids)),),
                )
            else:
                cur.execute("SELECT count(*) FROM public.photos")
            return int(cur.fetchone()[0])


def scan(
    roots: list[Path],
    *,
    photo_ids: list[str] | None = None,
    limit: int = 0,
    progress=None,
) -> dict:
    """
    Обойти записи и посчитать, у каких оригинал недоступен и почему.

    `progress(done, total, stage)` — тот же колбэк, что у остальных заданий;
    он же замечает отмену задания (исключение поднимает вызывающий).
    """

    entries = []
    for root in roots:
        try:
            available = root.is_dir()
        except OSError:
            available = False
        entries.append(
            {"path": str(root), "label": root.name or "Исходники", "available": available}
        )

    total = _total(photo_ids) if progress else 0
    checked = 0
    missing = 0
    outside = 0
    root_unavailable = 0
    samples: list[dict[str, str]] = []

    for photo_id, source_path in _rows(photo_ids, max(0, limit)):
        status = original_availability(source_path, roots)
        checked += 1

        if status == ORIGINAL_OUTSIDE_ROOTS:
            outside += 1
        elif status == ORIGINAL_ROOT_UNAVAILABLE:
            root_unavailable += 1
        elif status != ORIGINAL_OK:
            missing += 1

        if status != ORIGINAL_OK and len(samples) < SAMPLE_LIMIT:
            samples.append({"photo_id": photo_id, "reason": REASONS.get(status, status)})

        if progress:
            progress(checked, total, "проверка оригиналов")

    return {
        "checked": checked,
        "available": checked - missing - outside - root_unavailable,
        "missing": missing,
        "outside_roots": outside,
        "root_unavailable": root_unavailable,
        "roots": entries,
        "samples": samples,
    }


def write_report(report: dict) -> Path:
    """Временный файл → запись → атомарная публикация, как у остальных артефактов."""

    directory = reports_dir()
    directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = directory / f"originals_health_{stamp}.json"

    payload = {**report, "generated_at": datetime.now(timezone.utc).isoformat()}

    handle, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise

    return target


def latest_report() -> dict | None:
    """Последний отчёт (None — проверок ещё не было или файл испорчен)."""

    directory = reports_dir()

    if not directory.is_dir():
        return None

    files = sorted(directory.glob("originals_health_*.json"))

    if not files:
        return None

    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run(*, control=None) -> dict:
    """Задание ORIGINALS_CHECK: обойти корпус, отчёт положить на диск."""

    from app.api.config import ORIGINALS_ROOTS

    if not ORIGINALS_ROOTS:
        raise ValueError(
            "SCENE_ORIGINALS_ROOTS не задан: проверять доступность оригиналов нечего"
        )

    report = scan(ORIGINALS_ROOTS, progress=control)
    path = write_report(report)

    return {**report, "report": str(path)}

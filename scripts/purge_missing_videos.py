#!/usr/bin/env python
"""
Удаление записей видео, у которых нет файла оригинала.

Что делает: находит строки `video_assets`, у которых записанного файла нет ни
по одному из разрешённых корней (`SCENE_ORIGINALS_ROOTS` и корень производных),
и по флагу `--apply` удаляет их вместе с производными и билетами (каскад по
внешним ключам). Без `--apply` — только показывает список: это режим по
умолчанию, запись ничего не меняет.

Зачем: грид видео показывает такие записи с пометкой «файл не найден»
(`available: false`, задание п. 11). Это следы удалённого корпуса и
отключённых томов. Запись без оригинала не восстанавливается сама — путь
починит `scripts/remap_source_root.py` или бэкап, поэтому удалять её нужно
осознанно.

Перед удалением скрипт сохраняет полные строки (и связанные производные) в
JSON рядом с отчётами: `data/reports/video_records_removed_<штамп>.json`.
Это не откат, а след: восстановить запись из него можно вставкой в
`video_assets`, но идентификаторы производных и билетов были свои.

Использование:

    .venv/bin/python scripts/purge_missing_videos.py            # показать
    .venv/bin/python scripts/purge_missing_videos.py --apply    # удалить
    .venv/bin/python scripts/purge_missing_videos.py --apply --json

Код возврата 1, если есть записи без файла (удобно для алерта), 0 — если нет.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.config import ORIGINALS_ROOTS, VIDEO_DERIVATIVES_ROOT  # noqa: E402
from app.api.repository import get_connection  # noqa: E402
from app.video.transcode import derivatives_root  # noqa: E402

REPORT_DIR = "data/reports"


def _allowed_roots() -> list[str]:
    roots = [str(root) for root in ORIGINALS_ROOTS]
    derivative_root = str(derivatives_root() or VIDEO_DERIVATIVES_ROOT)
    if derivative_root not in roots:
        roots.append(derivative_root)
    return roots


def _json_ready(row: dict) -> dict:
    """Даты в ISO: след пишется в JSON, а не в SQL-дамп."""

    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }


def _has_file(source_path: str | None) -> bool:
    """Файл на месте? Пустой путь и путь вне корней считаются отсутствием."""

    if not source_path:
        return False

    for root in _allowed_roots():
        if source_path == root or source_path.startswith(root.rstrip("/") + "/"):
            return os.path.isfile(source_path)

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
                _json_ready(dict(zip(columns, row))) for row in cur.fetchall()
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
                _json_ready(dict(zip(columns, row))) for row in cur.fetchall()
            ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="удалить найденные записи (по умолчанию только показ)",
    )
    parser.add_argument("--json", action="store_true", help="вывод в JSON")
    args = parser.parse_args()

    rows = _rows()
    missing = [row for row in rows if not _has_file(row["source_path"])]

    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "missing": len(missing),
        "records": missing,
    }

    if not missing:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Записей всего {len(rows)}, без файла нет — удалять нечего.")
        return 0

    if not args.apply:
        payload["applied"] = False
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Записей всего {len(rows)}, без файла {len(missing)}:")
            for row in missing:
                print(f"  {row['video_id']}  {row['filename']}  |  {row['source_path']}")
            print("\nНичего не изменено. Удаление — с флагом --apply.")
        return 1

    # След до удаления: полные строки и связанные производные.
    records = [row["video_id"] for row in missing]
    payload["derivatives"] = _derivatives(records)
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"video_records_removed_{stamp}.json")

    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)

    # Удаляем в одной транзакции и только те строки, у которых файла нет и
    # сейчас: между показом и удалением том мог вернуться.
    still_missing = [
        row["video_id"] for row in missing if not _has_file(row["source_path"])
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.video_assets WHERE video_id = ANY(%s) RETURNING video_id",
                (still_missing,),
            )
            deleted = [row[0] for row in cur.fetchall()]

    payload["applied"] = True
    payload["deleted"] = len(deleted)
    payload["report"] = report_path

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Удалено записей: {len(deleted)} (из {len(missing)} найденных).")
        print(f"След сохранён: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

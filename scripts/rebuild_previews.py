#!/usr/bin/env python
"""
Пересоздание превью по photo_id после очистки или потери файлов.

Скрипт не сканирует папку с исходниками: путь к оригиналу берётся из записи
фото в базе (`public.photos.source_path`), а производные строятся по
детерминированным путям от `SCENE_PREVIEW_ROOT`. Поэтому превью можно
восстановить даже когда рабочая папка недоступна из UI.

Что делает:

1. отбирает фото, у которых SMALL/MIDDLE отсутствуют или пусты;
2. проверяет доступность оригинала (том смонтирован? файл на месте?);
3. ставит задание `PHOTO_PREVIEW` только для тех, где оригинал доступен;
4. фото с недоступным оригиналом **не удаляет и не трогает** — сообщает их
   отдельно («оригинал недоступен, используйте превью»).

Использование:

    .venv/bin/python scripts/rebuild_previews.py --dry-run
    .venv/bin/python scripts/rebuild_previews.py --json
    .venv/bin/python scripts/rebuild_previews.py --limit 1000
    .venv/bin/python scripts/rebuild_previews.py --photo-id PH_ab... --photo-id PH_cd...

Код возврата 0 — задания поставлены (или ставить было нечего), 1 — часть фото
пересоздать нельзя из-за недоступного оригинала.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.config import ORIGINALS_ROOTS  # noqa: E402
from app.api.file_access import ORIGINAL_OK, original_availability  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.preview.queue import (  # noqa: E402
    enqueue_missing_previews,
    preview_files_missing,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Пересоздать превью для фото, у которых нет файлов",
    )
    parser.add_argument("--dry-run", action="store_true", help="только посчитать, заданий не ставить")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument("--limit", type=int, default=500, help="сколько заданий поставить за запуск (1..5000)")
    parser.add_argument(
        "--photo-id",
        dest="photo_ids",
        action="append",
        default=None,
        help="только это фото (можно повторить)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not 1 <= args.limit <= 5000:
        print("--limit должен быть от 1 до 5000", file=sys.stderr)
        return 2

    if args.dry_run:
        report = _dry_run(args)
    else:
        result = enqueue_missing_previews(
            limit=args.limit, photo_ids=args.photo_ids
        )
        report = {
            "dry_run": False,
            "missing_files": result["selected"] + result.get("originals_missing", 0),
            "rebuildable": result["selected"],
            "originals_missing": result.get("originals_missing", 0),
            "queued": result["queued"],
            "already_active": result["already_active"],
            "limit": args.limit,
            "photo_ids": args.photo_ids or [],
        }

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"без файлов превью:   {report['missing_files']}")
        print(f"можно пересоздать:   {report['rebuildable']}")
        if report["originals_missing"]:
            print(f"оригинал недоступен: {report['originals_missing']}")
            print(
                "  такие фото не изменяются: запись сохраняется, в гриде "
                "работает превью («оригинал недоступен, используйте превью»)."
            )
        if not args.dry_run:
            print(f"заданий поставлено:  {report.get('queued', 0)}")
            print(f"уже в очереди:       {report.get('already_active', 0)}")
        else:
            print("(dry-run: задания не ставились)")

    return 1 if report["originals_missing"] else 0


def _dry_run(args: argparse.Namespace) -> dict:
    """
    Пересчёт без постановки заданий.

    Отбор тот же, что и в боевом режиме, поэтому «сколько будет поставлено»
    и «сколько нельзя восстановить» видно заранее.
    """

    checked = 0
    rebuildable = 0
    unavailable = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            if args.photo_ids:
                cur.execute(
                    """SELECT p.photo_id, p.source_path, r.small_path, r.middle_path
                       FROM public.photos AS p
                       LEFT JOIN public.photo_previews AS r ON r.photo_id=p.photo_id
                       WHERE p.photo_id = ANY(%s) ORDER BY p.photo_id""",
                    (sorted(set(args.photo_ids)),),
                )
            else:
                cur.execute(
                    """SELECT p.photo_id, p.source_path, r.small_path, r.middle_path
                       FROM public.photos AS p
                       LEFT JOIN public.photo_previews AS r ON r.photo_id=p.photo_id
                       ORDER BY p.photo_id LIMIT %s""",
                    (max(args.limit * 4, 100),),
                )
            rows = cur.fetchall()

    for photo_id, source_path, small_path, middle_path in rows:
        if not preview_files_missing(str(photo_id), small_path, middle_path):
            continue
        checked += 1
        if original_availability(source_path, ORIGINALS_ROOTS) == ORIGINAL_OK:
            rebuildable += 1
        else:
            unavailable += 1

    return {
        "dry_run": True,
        "missing_files": checked,
        "rebuildable": rebuildable,
        "originals_missing": unavailable,
        "limit": args.limit,
        "photo_ids": args.photo_ids or [],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"без файлов превью:   {report['missing_files']}")
        print(f"можно пересоздать:   {report['rebuildable']}")
        if report["originals_missing"]:
            print(f"оригинал недоступен: {report['originals_missing']}")
            print(
                "  такие фото не изменяются: запись сохраняется, в гриде "
                "работает превью («оригинал недоступен, используйте превью»)."
            )
        if not args.dry_run:
            print(f"заданий поставлено:  {report.get('queued', 0)}")
            print(f"уже в очереди:       {report.get('already_active', 0)}")
        else:
            print("(dry-run: задания не ставились)")

    return 1 if report["originals_missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

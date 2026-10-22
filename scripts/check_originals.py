#!/usr/bin/env python
"""
Отчёт о доступности оригиналов: у каких фото файл пропал.

Только чтение: скрипт делает `resolve()` и `is_file()` по пути, сохранённому
в базе, и ничего не меняет — ни запись фото, ни превью, ни оригинал.

Зачем: основная масса данных лежит на сетевом томе. Если том отмонтирован,
уехал или файл удалили руками, фото в гриде остаётся, превью работает, а
«посмотреть/скачать» падает. Скрипт показывает масштаб заранее, до нажатия
кнопки: см. `GET /v1/photos/{photo_id}/original/status` в UI и
`docs/preview.txt`.

Использование:

    .venv/bin/python scripts/check_originals.py --dry-run
    .venv/bin/python scripts/check_originals.py --json --limit 50000
    .venv/bin/python scripts/check_originals.py --photo-id PH_ab... --photo-id PH_cd...

Код возврата 1, если найдены недоступные оригиналы (удобно для алерта),
2 — ошибка конфигурации (не задан SCENE_ORIGINALS_ROOTS).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.config import ORIGINALS_ROOTS  # noqa: E402
from app.api.file_access import (  # noqa: E402
    ORIGINAL_MISSING,
    ORIGINAL_NOT_CONFIGURED,
    ORIGINAL_OK,
    ORIGINAL_OUTSIDE_ROOTS,
    original_availability,
)
from app.ingest.database import get_connection  # noqa: E402

_PAGE = 2000
_SAMPLE_LIMIT = 20

REASONS = {
    ORIGINAL_MISSING: "файл не найден",
    ORIGINAL_OUTSIDE_ROOTS: "путь вне разрешённых корней",
    ORIGINAL_NOT_CONFIGURED: "SCENE_ORIGINALS_ROOTS не задан",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверить, доступны ли оригиналы зарегистрированных фото",
    )
    parser.add_argument("--dry-run", action="store_true", help="ничего не менять (по умолчанию и так только чтение)")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument("--limit", type=int, default=0, help="проверить не больше N фото (0 — все)")
    parser.add_argument(
        "--photo-id",
        dest="photo_ids",
        action="append",
        default=None,
        help="проверить только это фото (можно повторить)",
    )
    return parser.parse_args(argv)


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
                        (cursor, cursor, _PAGE),
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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not ORIGINALS_ROOTS:
        print(
            "SCENE_ORIGINALS_ROOTS не задан: оригиналы не отдаются, "
            "проверять нечего",
            file=sys.stderr,
        )
        return 2

    checked = 0
    missing = 0
    outside = 0
    samples: list[dict[str, str]] = []

    for photo_id, source_path in _rows(args.photo_ids, max(0, args.limit)):
        status = original_availability(source_path, ORIGINALS_ROOTS)
        checked += 1
        if status == ORIGINAL_OK:
            continue
        if status == ORIGINAL_OUTSIDE_ROOTS:
            outside += 1
        else:
            missing += 1
        if len(samples) < _SAMPLE_LIMIT:
            samples.append({"photo_id": photo_id, "reason": REASONS.get(status, status)})

    report = {
        "checked": checked,
        "available": checked - missing - outside,
        "missing": missing,
        "outside_roots": outside,
        "roots": len(ORIGINALS_ROOTS),
        "samples": samples,
        "dry_run": True,
        "limit": max(0, args.limit),
        "photo_ids": args.photo_ids or [],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"проверено: {report['checked']}")
        print(f"доступно:  {report['available']}")
        print(f"не найдено: {missing}")
        if outside:
            print(f"вне разрешённых корней: {outside}")
        for sample in samples:
            print(f"  {sample['photo_id']}: {sample['reason']}")
        if missing or outside:
            print(
                "\nЗаписи фото не удаляются: в гриде доступно превью, "
                "а «посмотреть/скачать» покажет «оригинал недоступен»."
            )

    return 1 if (missing or outside) else 0


if __name__ == "__main__":
    raise SystemExit(main())

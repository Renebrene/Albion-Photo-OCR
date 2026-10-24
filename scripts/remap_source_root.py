#!/usr/bin/env python
"""
Перенести зарегистрированные пути источников на новый корень (NAS, копия).

Когда фотографии и видео переезжают с одного тома на другой (например,
с локального диска на NAS), в базе остаются старые source_path. Скрипт
заменяет только префикс пути и не читает и не изменяет сами файлы.

По умолчанию — dry-run: показывает, сколько строк и какие примеры изменятся.
Для записи нужен явный --confirm. После переноса не забудьте добавить новый
корень в SCENE_ORIGINALS_ROOTS, иначе API будет считать оригиналы
недоступными.

    .venv/bin/python scripts/remap_source_root.py \
        --from /media/alexice/TEST/БАЗАФОТО \
        --to /media/alexice/Win10/БАЗАФОТО

    .venv/bin/python scripts/remap_source_root.py ... --confirm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingest.database import get_connection  # noqa: E402

TABLES = (
    ("photos", "photo_id"),
    ("video_assets", "video_id"),
)


def _prefix(value: str) -> str:
    return value.rstrip("/")


def plan(cur, old: str, new: str) -> dict:
    report = {"old": old, "new": new, "tables": []}

    for table, key in TABLES:
        cur.execute(
            f"SELECT count(*) FROM public.{table} WHERE source_path LIKE %s",
            (old + "/%",),
        )
        total = int(cur.fetchone()[0])

        cur.execute(
            f"SELECT {key}, source_path FROM public.{table} "
            "WHERE source_path LIKE %s ORDER BY source_path LIMIT 5",
            (old + "/%",),
        )
        samples = [
            {"id": row[0], "from": row[1], "to": new + row[1][len(old):]}
            for row in cur.fetchall()
        ]

        report["tables"].append(
            {"table": table, "rows": total, "samples": samples}
        )

    return report


def apply(cur, old: str, new: str) -> dict:
    changed = {}

    for table, _key in TABLES:
        cur.execute(
            f"UPDATE public.{table} "
            f"SET source_path = %s || substr(source_path, %s) "
            "WHERE source_path LIKE %s",
            (new, len(old) + 1, old + "/%"),
        )
        changed[table] = cur.rowcount

    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="old", required=True)
    parser.add_argument("--to", dest="new", required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    old = _prefix(args.old)
    new = _prefix(args.new)

    if not old or not new:
        raise SystemExit("--from и --to не должны быть пустыми")

    if old == new:
        raise SystemExit("--from и --to совпадают")

    if not Path(new).is_dir():
        raise SystemExit(f"новый корень не найден: {new}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            report = plan(cur, old, new)

            if args.confirm:
                with conn.transaction():
                    report["changed"] = apply(cur, old, new)
            else:
                report["changed"] = None

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"перенос путей: {old} -> {new}")
    print("режим:", "ЗАПИСЬ" if args.confirm else "dry-run")
    for item in report["tables"]:
        print(f"  {item['table']}: {item['rows']} строк")
        for sample in item["samples"]:
            print(f"    {sample['from']}\n      -> {sample['to']}")

    if args.confirm:
        print("изменено:", report["changed"])
        print("не забудьте добавить новый корень в SCENE_ORIGINALS_ROOTS")
    else:
        print("ничего не изменено; для записи добавьте --confirm")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

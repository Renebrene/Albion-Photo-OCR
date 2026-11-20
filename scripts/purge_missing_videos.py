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

С той же логикой инспекция папки (`app/ingest/runner.py`) удаляет записи,
чей файл пропал внутри проинспектированной папки: общий код —
`app/video/maintenance.py`. Скрипт остаётся ручным режимом по всему реестру и
действует осторожнее: строка вне разрешённых корней тоже считается мёртвой,
даже если файл где-то есть.

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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.video import maintenance  # noqa: E402

# Тесты подменяют `_allowed_roots`, поэтому `_has_file` берёт корни оттуда, а
# не напрямую из общего модуля.
def _allowed_roots() -> list[str]:
    return maintenance.allowed_roots()


def _has_file(source_path: str | None) -> bool:
    return maintenance.has_file(source_path, _allowed_roots())


_json_ready = maintenance.json_ready


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="удалить найденные записи (по умолчанию только показ)",
    )
    parser.add_argument("--json", action="store_true", help="вывод в JSON")
    args = parser.parse_args()

    payload = maintenance.purge_missing_records(apply=args.apply)
    missing = payload["missing"]

    if not missing:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Записей всего {payload['total']}, без файла нет — удалять нечего.")
        return 0

    if not args.apply:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Записей всего {payload['total']}, без файла {missing}:")
            for row in payload["records"]:
                print(f"  {row['video_id']}  {row['filename']}  |  {row['source_path']}")
            print("\nНичего не изменено. Удаление — с флагом --apply.")
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Удалено записей: {payload['deleted']} (из {missing} найденных).")
        print(f"След сохранён: {payload['report']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

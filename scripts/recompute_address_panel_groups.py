#!/usr/bin/env python
"""
Пересчёт закладки кнопки верхней панели у адресов (schema/056).

Закладка (`panel_group`) хранится в `address_directory` и заполняется при
разборе XLS. Скрипт нужен после применения миграции (колонка появляется пустой),
после правки самого правила `directory.address_tab` и для строк, созданных мимо
импорта. Он идемпотентен: считает правило заново и обновляет только то, что
разошлось.

Использование:

    .venv/bin/python scripts/recompute_address_panel_groups.py            # показ
    .venv/bin/python scripts/recompute_address_panel_groups.py --apply    # запись
    .venv/bin/python scripts/recompute_address_panel_groups.py --json

Без `--apply` ничего не пишется: на 1500 адресах ошибка в правиле иначе сразу
разъехалась бы по всей базе. Код возврата 0 — всё сходится, 1 — есть расхождения.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import directory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="записать пересчитанные закладки (по умолчанию только показ)",
    )
    parser.add_argument("--json", action="store_true", help="вывод в JSON")
    args = parser.parse_args()

    result = directory.recompute_panel_groups(dry_run=not args.apply)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["changed"] else 0

    print(f"Адресов всего: {result['total']}")
    print("По закладкам: " + ", ".join(
        f"{tab}={count}" for tab, count in result["counts"].items() if count
    ))

    if not result["changed"]:
        print("Расхождений нет — закладки совпадают с правилом.")
        return 0

    if args.apply:
        print(f"Обновлено строк: {result['changed']}")
        return 0

    print(f"Разошлось строк: {result['changed']}. Ничего не изменено."
          " Запись — с флагом --apply.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

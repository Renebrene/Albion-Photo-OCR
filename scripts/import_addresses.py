"""
Import the legal-address directory from a spreadsheet.

    set -a && . ~/.config/scene-fingerprint.env && set +a
    python scripts/import_addresses.py "~/Desktop/Без имени 1.xlsx"

The file is the same one the web window accepts (POST /v1/addresses/import):
first column - the legal address, second - the short name (alias); a header row
is optional, recognised column titles are matched to the right columns.

Re-running after an edit is safe: rows are matched by the legal name (case- and
whitespace-insensitive), so existing addresses keep their id and any fingerprint
mappings, only new rows are added and changed short names refreshed. Use
--dry-run to see what the file parses into without touching the database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.api.directory import (
    DirectoryError,
    import_addresses,
    list_addresses,
    parse_address_table,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="import the address directory")
    parser.add_argument("path", help="an .xlsx, .xlsm, .csv or .tsv file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse and print the rows, write nothing",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        help="how many rows to print in --dry-run mode (default 10)",
    )
    args = parser.parse_args()

    path = Path(args.path).expanduser()

    if not path.is_file():
        print(f"файл не найден: {path}", file=sys.stderr)
        return 2

    try:
        items = parse_address_table(path.read_bytes(), path.name)
    except DirectoryError as exc:
        print(f"файл не разобран: {exc}", file=sys.stderr)
        return 2

    print(f"строк с адресами в файле: {len(items)}")

    if args.dry_run:
        for item in items[: max(0, args.show)]:
            print(f"  {item['legal_address']}  |  {item['simple_address']}")

        if len(items) > args.show:
            print(f"  ... ещё {len(items) - args.show}")

        return 0

    result = import_addresses(items)

    print(
        f"создано: {result['created']}, обновлено: {result['updated']}, "
        f"пропущено: {result['skipped']}"
    )

    for error in result["errors"]:
        print(f"  ошибка: {error}")

    print(f"всего в справочнике: {len(list_addresses())}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

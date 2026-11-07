#!/usr/bin/env python3
"""Read-only audit: address directory vs addresses written in filenames.

For every active address it counts how many corpus photos are labelled with
that address (using the same `expected_address()` matcher as the evaluation
scripts), and reports:

* covered addresses with no labelled photos;
* uncovered addresses that do have labelled photos;
* duplicate token sets (A/B sides, renamed rows) that can make matching
  ambiguous;
* the most common unmatched filename prefixes.

    .venv/bin/python scripts/address_label_audit.py

Outputs:
    data/experiments/address_audit/report.json
    data/experiments/address_audit/addresses.csv
    data/reports/address_label_audit_YYYYMMDD.md
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    _address_tokens,
    expected_address,
    fingerprint_addresses,
    load_addresses,
)

OUT = Path("data/experiments/address_audit")
REPORT = Path(f"data/reports/address_label_audit_{date.today():%Y%m%d}.md")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    addresses = load_addresses()
    covered = set(fingerprint_addresses().values())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT photo_id, filename FROM public.photos")
            photos = cur.fetchall()

    counts: Counter = Counter()
    examples: dict[int, list[str]] = defaultdict(list)
    unmatched: list[str] = []

    for _photo_id, filename in photos:
        address_id = expected_address(str(filename), addresses)
        if address_id is None:
            unmatched.append(str(filename))
        else:
            counts[address_id] += 1
            if len(examples[address_id]) < 3:
                examples[address_id].append(str(filename))

    duplicate_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for address_id, _normalized in addresses:
        tokens = tuple(
            sorted(set(_address_tokens(ADDRESS_NAMES.get(address_id, ""))))
        )
        if tokens:
            duplicate_groups[tokens].append(address_id)

    unmatched_prefixes: Counter = Counter()
    for filename in unmatched:
        stem = re.sub(
            r"[\s_\-]*\(?\d{1,4}\)?$", "", filename.rsplit(".", 1)[0]
        )
        tokens = _address_tokens(stem)
        unmatched_prefixes[" ".join(tokens[:3])] += 1

    address_rows = []
    for address_id, normalized in addresses:
        tokens = sorted(set(_address_tokens(ADDRESS_NAMES.get(address_id, ""))))
        address_rows.append(
            {
                "address_id": address_id,
                "name": ADDRESS_NAMES.get(address_id, ""),
                "normalized": normalized,
                "tokens": tokens,
                "covered": address_id in covered,
                "photos": counts[address_id],
                "examples": examples.get(address_id, []),
            }
        )

    covered_without_photos = [
        row for row in address_rows if row["covered"] and row["photos"] == 0
    ]
    uncovered_with_photos = sorted(
        (
            row
            for row in address_rows
            if not row["covered"] and row["photos"] > 0
        ),
        key=lambda row: -row["photos"],
    )
    duplicate_rows = []
    for tokens, ids in duplicate_groups.items():
        if len(ids) <= 1:
            continue
        if not any(counts[address_id] > 0 for address_id in ids):
            continue
        duplicate_rows.append(
            {
                "tokens": list(tokens),
                "addresses": [
                    {
                        "address_id": address_id,
                        "name": ADDRESS_NAMES.get(address_id, ""),
                        "photos": counts[address_id],
                        "covered": address_id in covered,
                    }
                    for address_id in ids
                ],
            }
        )
    duplicate_rows.sort(
        key=lambda row: -sum(item["photos"] for item in row["addresses"])
    )

    report = {
        "photos": len(photos),
        "labelled": len(photos) - len(unmatched),
        "unmatched": len(unmatched),
        "active_addresses": len(addresses),
        "covered_addresses": len(covered),
        "labelled_addresses": len(counts),
        "covered_without_photos": covered_without_photos,
        "uncovered_with_photos": uncovered_with_photos,
        "duplicate_groups": duplicate_rows,
        "top_matched": sorted(
            (
                {
                    "address_id": address_id,
                    "name": ADDRESS_NAMES.get(address_id, ""),
                    "photos": count,
                    "covered": address_id in covered,
                }
                for address_id, count in counts.items()
            ),
            key=lambda row: -row["photos"],
        )[:30],
        "unmatched_prefixes": unmatched_prefixes.most_common(40),
        "intersections": {
            str(address_id): {
                "name": ADDRESS_NAMES.get(address_id, ""),
                "photos": counts[address_id],
                "examples": examples.get(address_id, []),
            }
            for address_id in (144, 211, 2413)
        },
    }
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (OUT / "addresses.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "address_id",
                "name",
                "normalized",
                "covered",
                "photos",
                "tokens",
            ],
        )
        writer.writeheader()
        for row in address_rows:
            writer.writerow(
                {
                    "address_id": row["address_id"],
                    "name": row["name"],
                    "normalized": row["normalized"],
                    "covered": int(row["covered"]),
                    "photos": row["photos"],
                    "tokens": " ".join(row["tokens"]),
                }
            )

    lines = [
        "# Аудит: справочник адресов против подписей файлов",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only.",
        "",
        f"Фото всего: **{len(photos)}**; с адресом в имени: "
        f"**{len(photos) - len(unmatched)}**; без сопоставления: "
        f"**{len(unmatched)}**.",
        "",
        f"Активных адресов: **{len(addresses)}**; со слепком: "
        f"**{len(covered)}**; адресов, встретившихся в подписях: "
        f"**{len(counts)}**.",
        "",
        "## Слепок есть, подписанных фото нет",
        "",
        "| ID | Адрес |",
        "|---:|---|",
    ]
    for row in covered_without_photos:
        lines.append(f"| {row['address_id']} | {row['name']} |")

    lines += [
        "",
        "## Подписанные фото есть, слепка нет",
        "",
        "| ID | Адрес | Фото |",
        "|---:|---|---:|",
    ]
    for row in uncovered_with_photos[:25]:
        lines.append(
            f"| {row['address_id']} | {row['name']} | {row['photos']} |"
        )

    lines += [
        "",
        "## Топ адресов по подписанным фото",
        "",
        "| ID | Адрес | Фото | Слепок |",
        "|---:|---|---:|---|",
    ]
    for row in report["top_matched"]:
        lines.append(
            f"| {row['address_id']} | {row['name']} | {row['photos']} | "
            f"{'да' if row['covered'] else 'нет'} |"
        )

    lines += [
        "",
        "## Дубли по набору слов (стороны A/B и переименования)",
        "",
        "| Слова | Адреса |",
        "|---|---|",
    ]
    for row in duplicate_rows[:20]:
        values = "; ".join(
            f"{item['address_id']} — {item['name']} ({item['photos']})"
            for item in row["addresses"]
        )
        lines.append(f"| {' '.join(row['tokens'])} | {values} |")

    lines += [
        "",
        "## Топ несовпавших префиксов имён",
        "",
        "| Префикс | Фото |",
        "|---|---:|",
    ]
    for prefix, count in report["unmatched_prefixes"][:25]:
        lines.append(f"| {prefix} | {count} |")

    lines += [
        "",
        "## Проверка пересечений",
        "",
        "| ID | Адрес | Фото | Пример |",
        "|---:|---|---:|---|",
    ]
    for address_id, item in report["intersections"].items():
        example = item["examples"][0] if item["examples"] else ""
        lines.append(
            f"| {address_id} | {item['name']} | {item['photos']} | {example} |"
        )

    lines += [
        "",
        "## Ограничения",
        "",
        "- Сопоставление консервативное: при неоднозначности (например, "
        "«Космонавтов 14-16» без стороны A/B) адрес не угадывается.",
        "- Часть несовпадений — реально отсутствующие в справочнике адреса "
        "или другие названия, а не ошибка нормализации.",
        "- Слепки учитываются только активные.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"[audit] photos={len(photos)} labelled={len(photos)-len(unmatched)} "
        f"unmatched={len(unmatched)} addresses={len(addresses)} "
        f"covered={len(covered)}",
        flush=True,
    )
    print(f"[audit] report: {REPORT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

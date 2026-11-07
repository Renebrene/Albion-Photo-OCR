#!/usr/bin/env python3
"""Per-address table for labelled photos: volume, fingerprint size, errors.

    .venv/bin/python scripts/labeled_error_table.py --run-id 4

Outputs:
    data/reports/labeled_error_table_YYYYMMDD_runN.md
    data/experiments/labeled_error_table/runN.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402
from scripts import hybrid_weight_experiment as hwe  # noqa: E402
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    fingerprint_addresses,
)

OUT = Path("data/experiments/labeled_error_table")


def fingerprint_sizes() -> dict[int, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT af.address_id, f.fingerprint_id,
                       f.images_count, f.active
                FROM public.address_fingerprints AS af
                JOIN public.fingerprints AS f
                  ON f.fingerprint_id = af.fingerprint_id
                WHERE af.active AND f.active
                """
            )
            rows = cur.fetchall()

    sizes: dict[int, int] = defaultdict(int)
    for address_id, _fingerprint_id, images, _active in rows:
        address_id = hwe.CANONICAL_ADDRESS.get(int(address_id), int(address_id))
        sizes[address_id] += int(images or 0)
    return sizes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, default=4)
    args = parser.parse_args(argv)

    expected = hwe.labeled_context()
    fp = fingerprint_addresses()
    sizes = fingerprint_sizes()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, hybrid_final_id
                FROM public.hybrid_results
                WHERE hybrid_run_id = %s AND status = 'DONE'
                """,
                (args.run_id,),
            )
            finals = {
                str(row[0]): str(row[1]) if row[1] else None
                for row in cur.fetchall()
            }

    totals: Counter = Counter()
    correct: Counter = Counter()
    unknown: Counter = Counter()
    confusion: dict[int, Counter] = defaultdict(Counter)

    for photo_id, expected_id in expected.items():
        if expected_id is None:
            continue
        expected_id = hwe.CANONICAL_ADDRESS.get(
            int(expected_id), int(expected_id)
        )
        totals[expected_id] += 1

        fingerprint_id = finals.get(photo_id)
        predicted = fp.get(fingerprint_id) if fingerprint_id else None
        if predicted is not None:
            predicted = hwe.CANONICAL_ADDRESS.get(
                int(predicted), int(predicted)
            )

        if predicted is None:
            unknown[expected_id] += 1
        elif predicted == expected_id:
            correct[expected_id] += 1
        else:
            confusion[expected_id][predicted] += 1

    rows = []
    for address_id, total in totals.items():
        wrong = sum(confusion[address_id].values())
        rows.append(
            {
                "address_id": address_id,
                "name": ADDRESS_NAMES.get(address_id, ""),
                "photos": total,
                "fingerprint_photos": sizes.get(address_id, 0),
                "correct": correct[address_id],
                "wrong": wrong,
                "unknown": unknown[address_id],
                "error_rate": wrong / total * 100 if total else 0.0,
                "confusions": confusion[address_id].most_common(3),
            }
        )

    rows.sort(key=lambda item: (-item["wrong"], -item["photos"], item["address_id"]))

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / f"run{args.run_id}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "address_id",
                "address",
                "photos",
                "fingerprint_photos",
                "correct",
                "wrong",
                "unknown",
                "error_rate",
                "top_confusion",
                "top_confusion_count",
            ]
        )
        for row in rows:
            top = row["confusions"][0] if row["confusions"] else (None, 0)
            writer.writerow(
                [
                    row["address_id"],
                    row["name"],
                    row["photos"],
                    row["fingerprint_photos"],
                    row["correct"],
                    row["wrong"],
                    row["unknown"],
                    f"{row['error_rate']:.2f}",
                    ADDRESS_NAMES.get(top[0], "") if top[0] else "",
                    top[1],
                ]
            )

    total_photos = sum(totals.values())
    total_wrong = sum(row["wrong"] for row in rows)
    total_unknown = sum(row["unknown"] for row in rows)
    report = Path(
        f"data/reports/labeled_error_table_{date.today():%Y%m%d}"
        f"_run{args.run_id}.md"
    )
    report.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Подписанные фото по адресам — HYBRID run {args.run_id}",
        "",
        f"Всего подписанных фото: **{total_photos}**; ошибок: "
        f"**{total_wrong}** ({total_wrong / total_photos * 100:.2f}%); "
        f"без результата: {total_unknown}.",
        "",
        "«Фото в слепке» — сумма активных эталонных фото для адреса; "
        "0 означает, что активного слепка нет.",
        "",
        "| Адрес | Фото | В слепке | Ошибок | % ошибок | С кем путается |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        confusions = "; ".join(
            f"{ADDRESS_NAMES.get(address_id, address_id)} ({count})"
            for address_id, count in row["confusions"]
        ) or "—"
        lines.append(
            f"| {row['address_id']} {row['name']} | {row['photos']} | "
            f"{row['fingerprint_photos']} | {row['wrong']} | "
            f"{row['error_rate']:.1f}% | {confusions} |"
        )

    lines += [
        "",
        "## Итог",
        "",
        f"- ошибок среди покрытых адресов: "
        f"{total_wrong - sum(row['wrong'] for row in rows if row['fingerprint_photos'] == 0)};",
        f"- ошибок среди адресов без слепка: "
        f"{sum(row['wrong'] for row in rows if row['fingerprint_photos'] == 0)};",
        f"- адресов в таблице: {len(rows)}.",
    ]

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[table] report: {report}", flush=True)
    print(f"[table] csv: {csv_path}", flush=True)
    print(
        f"[table] photos={total_photos} wrong={total_wrong} "
        f"unknown={total_unknown}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

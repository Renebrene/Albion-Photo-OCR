#!/usr/bin/env python3
"""Labelled accuracy with address-name variants normalized.

A photo is correct when HYBRID predicts the expected address or one of its
documented spelling/side variants (data/experiments/label_variants_run4.json).
Strict and normalized answers are printed side by side.

    .venv/bin/python scripts/normalized_labeled_report.py --run-id 4
"""

from __future__ import annotations

import argparse
import csv
import json
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
from scripts.labeled_error_table import fingerprint_sizes  # noqa: E402

ROOT = Path("data/experiments/labeled_normalized")
VARIANTS = Path("data/experiments/label_variants_run4.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, default=4)
    parser.add_argument("--variants", type=Path, default=VARIANTS)
    args = parser.parse_args(argv)

    variants_raw = json.loads(args.variants.read_text(encoding="utf-8"))
    variants = {
        int(expected): {int(value) for value in accepted}
        for expected, accepted in variants_raw.items()
    }

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

    strict_ok = normalized_ok = unknown = converted = 0
    totals: Counter = Counter()
    strict_wrong: Counter = Counter()
    normalized_wrong: Counter = Counter()
    strict_confusion: dict[int, Counter] = defaultdict(Counter)
    normalized_confusion: dict[int, Counter] = defaultdict(Counter)

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

        accepted = variants.get(expected_id, {expected_id})
        if predicted is None:
            unknown += 1
            continue

        strict = predicted == expected_id
        normalized = predicted in accepted
        strict_ok += int(strict)
        normalized_ok += int(normalized)

        if not strict:
            strict_wrong[expected_id] += 1
            strict_confusion[expected_id][predicted] += 1
            if normalized:
                converted += 1
        if not normalized:
            normalized_wrong[expected_id] += 1
            normalized_confusion[expected_id][predicted] += 1

    total = sum(totals.values())
    report = {
        "run_id": args.run_id,
        "total": total,
        "strict_correct": strict_ok,
        "strict_wrong": total - strict_ok - unknown,
        "unknown": unknown,
        "normalized_correct": normalized_ok,
        "normalized_wrong": total - normalized_ok - unknown,
        "converted_variants": converted,
        "variants": str(args.variants),
    }

    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / f"run{args.run_id}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rows = []
    for address_id, photos in totals.items():
        rows.append(
            {
                "address_id": address_id,
                "name": ADDRESS_NAMES.get(address_id, ""),
                "photos": photos,
                "fingerprint_photos": sizes.get(address_id, 0),
                "strict_wrong": strict_wrong[address_id],
                "normalized_wrong": normalized_wrong[address_id],
                "strict_rate": strict_wrong[address_id] / photos * 100,
                "normalized_rate": normalized_wrong[address_id] / photos * 100,
                "strict_confusions": strict_confusion[address_id].most_common(3),
                "normalized_confusions": normalized_confusion[
                    address_id
                ].most_common(3),
            }
        )
    rows.sort(
        key=lambda item: (
            -item["normalized_wrong"],
            -item["strict_wrong"],
            -item["photos"],
            item["address_id"],
        )
    )

    csv_path = ROOT / f"run{args.run_id}_addresses.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "address_id",
                "address",
                "photos",
                "fingerprint_photos",
                "strict_wrong",
                "normalized_wrong",
                "normalized_error_rate",
                "top_confusion",
            ]
        )
        for row in rows:
            top = row["normalized_confusions"][0] if row["normalized_confusions"] else (None, 0)
            writer.writerow(
                [
                    row["address_id"],
                    row["name"],
                    row["photos"],
                    row["fingerprint_photos"],
                    row["strict_wrong"],
                    row["normalized_wrong"],
                    f"{row['normalized_rate']:.2f}",
                    ADDRESS_NAMES.get(top[0], "") if top[0] else "",
                ]
            )

    report_path = Path(
        f"data/reports/labeled_normalized_{date.today():%Y%m%d}"
        f"_run{args.run_id}.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Подписанные фото с нормализацией вариантов — run {args.run_id}",
        "",
        f"Всего подписанных: **{total}**; без результата: **{unknown}**.",
        "",
        "| Вариант подсчёта | Верно | Ошибок | % ошибок |",
        "|---|---:|---:|---:|",
        f"| Строгий (как было) | {strict_ok} | "
        f"{total - strict_ok - unknown} | "
        f"{(total - strict_ok - unknown) / total * 100:.2f}% |",
        f"| **С вариантами названий** | **{normalized_ok}** | "
        f"**{total - normalized_ok - unknown}** | "
        f"**{(total - normalized_ok - unknown) / total * 100:.2f}%** |",
        "",
        f"Вариантами признаны **{converted}** фото: они были ошибочными "
        "только из-за написания/стороны адреса.",
        "",
        "## Ошибки по адресам после нормализации",
        "",
        "| Адрес | Фото | В слепке | Ошибок | % ошибок | С кем путается |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        confusions = "; ".join(
            f"{ADDRESS_NAMES.get(address_id, address_id)} ({count})"
            for address_id, count in row["normalized_confusions"]
        ) or "—"
        lines.append(
            f"| {row['address_id']} {row['name']} | {row['photos']} | "
            f"{row['fingerprint_photos']} | {row['normalized_wrong']} | "
            f"{row['normalized_rate']:.1f}% | {confusions} |"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[normalized] report: {report_path}", flush=True)
    print(f"[normalized] csv: {csv_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

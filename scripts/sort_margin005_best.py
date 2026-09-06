#!/usr/bin/env python3

import csv
import shutil
from pathlib import Path
from collections import Counter


PROJECT = Path(__file__).resolve().parent.parent

INPUT_CSV = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

SOURCE_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "output/visual_check_margin005"

CHANGED_DIR = OUTPUT_DIR / "_CHANGED"

MARGIN_THRESHOLD = 0.005


def safe_copy(src, dst_dir):
    dst_dir.mkdir(parents=True, exist_ok=True)

    dst = dst_dir / src.name

    if not dst.exists():
        shutil.copy2(src, dst)
        return dst

    stem = src.stem
    suffix = src.suffix

    n = 2

    while True:
        candidate = dst_dir / f"{stem}__{n}{suffix}"

        if not candidate.exists():
            shutil.copy2(src, candidate)
            return candidate

        n += 1


def main():

    print("=" * 80)
    print("MARGIN < 0.005 + BEST VISUAL TEST")
    print("=" * 80)

    print("CSV   :", INPUT_CSV)
    print("SOURCE:", SOURCE_DIR)
    print("OUTPUT:", OUTPUT_DIR)
    print()

    if not INPUT_CSV.exists():
        raise FileNotFoundError(INPUT_CSV)

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(SOURCE_DIR)

    # Clean only our test output.
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True)

    rows = []

    with INPUT_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    print(f"CSV rows: {len(rows)}")
    print()

    counters = Counter()
    changed = []
    low_margin = []

    for row in rows:

        image = row["image"]

        current_first = row["current_first"]
        current_second = row["current_second"]

        final_margin = float(row["final_margin"])
        best_diff = float(row["best_diff"])

        # --------------------------------------------------
        # DECISION
        # --------------------------------------------------

        assigned = current_first
        reason = "FIRST"

        if final_margin < MARGIN_THRESHOLD:

            low_margin.append(row)

            if best_diff > 0:

                assigned = current_second
                reason = "BEST"

            else:

                reason = "FIRST_BEST_LOSES"

        # --------------------------------------------------
        # SOURCE
        # --------------------------------------------------

        src = SOURCE_DIR / image

        if not src.exists():

            print(
                f"[WARNING] source not found: {src}"
            )

            continue

        # --------------------------------------------------
        # DESTINATION
        # --------------------------------------------------

        folder = assigned.replace("_v33", "")

        dst_dir = OUTPUT_DIR / folder

        safe_copy(src, dst_dir)

        counters[folder] += 1

        # --------------------------------------------------
        # CHANGED
        # --------------------------------------------------

        if assigned != current_first:

            changed.append({
                "image": image,
                "old": current_first,
                "new": assigned,
                "margin": final_margin,
                "best_diff": best_diff,
            })

            # Put an additional copy into _CHANGED.
            safe_copy(src, CHANGED_DIR)

    # ------------------------------------------------------
    # REPORT
    # ------------------------------------------------------

    report = OUTPUT_DIR / "decision_report.csv"

    with report.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        fields = [
            "image",
            "old",
            "new",
            "margin",
            "best_diff",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerows(changed)

    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(
        f"Total images:        {len(rows)}"
    )

    print(
        f"Margin < 0.005:      {len(low_margin)}"
    )

    print(
        f"Changed by BEST:     {len(changed)}"
    )

    print()

    print("CHANGED:")
    print("-" * 80)

    for x in changed:

        print(
            f'{x["image"]}'
        )

        print(
            f'    {x["old"]} -> {x["new"]}'
        )

        print(
            f'    margin={x["margin"]:.6f}'
            f'  best_diff={x["best_diff"]:+.6f}'
        )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for folder in sorted(
        counters,
        key=lambda x: int(x)
    ):

        print(
            f"{folder:10s} {counters[folder]:4d}"
        )

    print("-" * 80)
    print(
        f"{'TOTAL':10s} {sum(counters.values()):4d}"
    )

    print()
    print("OUTPUT:")
    print(
        f"  sorted : {OUTPUT_DIR}"
    )

    print(
        f"  changed: {CHANGED_DIR}"
    )

    print(
        f"  report : {report}"
    )


if __name__ == "__main__":
    main()

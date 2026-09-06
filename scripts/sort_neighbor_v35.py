#!/usr/bin/env python3

import csv
import shutil
from pathlib import Path
from collections import Counter

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"

SOURCE_CSV = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

OUTPUT_DIR = PROJECT / "output/visual_check_neighbor_v35"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005
NEIGHBOR_RADIUS = 2


def load_rows():
    rows = []

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        for row in csv.DictReader(f):
            if (INPUT_DIR / row["image"]).exists():
                rows.append(row)

    return rows


def clean_id(value):
    if not value:
        return None

    return value.replace("_v33", "")


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = load_rows()

    decisions = []
    changed = []

    counters = Counter()

    low_margin_count = 0

    for i, row in enumerate(rows):

        image = row["image"]

        current = clean_id(
            row.get("current_first")
        )

        second = clean_id(
            row.get("current_second")
        )

        margin = float(
            row["final_margin"]
        )

        final_id = current

        reason = "V33"

        second_neighbors = []
        current_neighbors = []

        # --------------------------------------------------
        # Только сомнительные случаи
        # --------------------------------------------------

        if margin < MARGIN_LIMIT:

            low_margin_count += 1

            start = max(
                0,
                i - NEIGHBOR_RADIUS
            )

            end = min(
                len(rows),
                i + NEIGHBOR_RADIUS + 1
            )

            for j in range(start, end):

                if j == i:
                    continue

                neighbor = rows[j]

                neighbor_id = clean_id(
                    neighbor.get("current_first")
                )

                if not neighbor_id:
                    continue

                distance = j - i

                sign = "+" if distance > 0 else "-"

                label = (
                    f"{sign}{abs(distance)}:"
                    f"{neighbor['image']}"
                )

                if neighbor_id == second:
                    second_neighbors.append(
                        label
                    )

                elif neighbor_id == current:
                    current_neighbors.append(
                        label
                    )

            second_count = len(
                second_neighbors
            )

            current_count = len(
                current_neighbors
            )

            # --------------------------------------------------
            # Безопасное решение
            #
            # Меняем только если:
            #
            # 1. второй кандидат поддержан
            #    минимум двумя соседями
            #
            # 2. текущий кандидат не поддержан
            #    ни одним соседом
            #
            # Иначе сохраняем v33.
            # --------------------------------------------------

            if (
                second
                and second_count >= 2
                and current_count == 0
            ):

                final_id = second

                reason = (
                    "SECOND_SUPPORTED_BY_2+_NEIGHBORS"
                )

            elif (
                second
                and second_count > 0
                and current_count > 0
            ):

                reason = (
                    "CONFLICT_KEEP_V33"
                )

            elif (
                second
                and second_count == 1
            ):

                reason = (
                    "ONE_NEIGHBOR_KEEP_V33"
                )

            else:

                reason = (
                    "NO_NEIGHBOR_EVIDENCE"
                )

        # --------------------------------------------------
        # Statistics
        # --------------------------------------------------

        counters[final_id] += 1

        # --------------------------------------------------
        # Record
        # --------------------------------------------------

        if final_id != current:

            changed.append({
                "image": image,
                "from": current,
                "to": final_id,
                "margin": margin,
                "second_neighbors": "; ".join(
                    second_neighbors
                ),
                "current_neighbors": "; ".join(
                    current_neighbors
                ),
                "reason": reason,
            })

        decisions.append({
            "image": image,
            "v33": current,
            "second": second,
            "final": final_id,
            "margin": margin,
            "second_neighbor_count":
                len(second_neighbors),
            "current_neighbor_count":
                len(current_neighbors),
            "reason": reason,
            "second_neighbors":
                "; ".join(second_neighbors),
            "current_neighbors":
                "; ".join(current_neighbors),
        })

    # --------------------------------------------------
    # Save sorted result
    # --------------------------------------------------

    for item in decisions:

        folder = item["final"]

        if not folder:
            folder = "NO_CANDIDATE"

        destination_dir = (
            OUTPUT_DIR / folder
        )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        source = (
            INPUT_DIR / item["image"]
        )

        destination = (
            destination_dir / source.name
        )

        if destination.exists():

            stem = destination.stem
            suffix = destination.suffix

            n = 2

            while True:

                candidate = (
                    destination_dir
                    / f"{stem}__{n}{suffix}"
                )

                if not candidate.exists():
                    destination = candidate
                    break

                n += 1

        shutil.copy2(
            source,
            destination
        )

    # --------------------------------------------------
    # CSV
    # --------------------------------------------------

    fields = [
        "image",
        "v33",
        "second",
        "final",
        "margin",
        "second_neighbor_count",
        "current_neighbor_count",
        "reason",
        "second_neighbors",
        "current_neighbors",
    ]

    with REPORT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(decisions)

    # --------------------------------------------------
    # Console
    # --------------------------------------------------

    print()
    print("=" * 80)
    print("NEIGHBOR CONTEXT V35")
    print("=" * 80)

    print(
        f"Input images : {len(rows)}"
    )

    print(
        f"Margin limit : {MARGIN_LIMIT}"
    )

    print(
        f"Neighbor +/- : {NEIGHBOR_RADIUS}"
    )

    print()
    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(
        f"Total images:        {len(rows)}"
    )

    print(
        f"Margin < 0.005:      "
        f"{low_margin_count}"
    )

    print(
        f"Changed by neighbors:"
        f"{len(changed):8d}"
    )

    if changed:

        print()
        print("CHANGED")
        print("-" * 80)

        for item in changed:

            print(
                item["image"]
            )

            print(
                f"    {item['from']} "
                f"-> {item['to']}"
            )

            print(
                f"    margin="
                f"{item['margin']:.6f}"
            )

            print(
                f"    reason="
                f"{item['reason']}"
            )

            if item["second_neighbors"]:

                print(
                    f"    second: "
                    f"{item['second_neighbors']}"
                )

            if item["current_neighbors"]:

                print(
                    f"    current: "
                    f"{item['current_neighbors']}"
                )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for n in range(78, 96):

        key = str(n)

        print(
            f"{key:10s} "
            f"{counters[key]:4d}"
        )

    print("-" * 80)

    print(
        f"TOTAL       "
        f"{sum(counters.values()):4d}"
    )

    print()
    print("OUTPUT:")
    print(
        "  sorted :",
        OUTPUT_DIR
    )

    print(
        "  report :",
        REPORT_CSV
    )


if __name__ == "__main__":
    main()

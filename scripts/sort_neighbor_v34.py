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

OUTPUT_DIR = PROJECT / "output/visual_check_neighbor_v34"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005
NEIGHBOR_RADIUS = 2

# Минимальный score соседнего кадра,
# чтобы считать его уверенным.
NEIGHBOR_SCORE_MIN = 0.80

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".JPG",
    ".JPEG",
    ".png",
    ".PNG",
}


def load_files():
    """
    Получаем порядок фотографий так,
    как они реально находятся в test.
    """

    files = [
        p
        for p in INPUT_DIR.iterdir()
        if p.is_file()
        and p.suffix in IMAGE_EXTENSIONS
    ]

    # Естественная сортировка по имени.
    # Для наших серий это предпочтительнее обычной
    # лексикографической сортировки.
    import re

    def natural_key(path):
        parts = re.split(r"(\d+)", path.name)

        return [
            int(x) if x.isdigit() else x.lower()
            for x in parts
        ]

    files.sort(key=natural_key)

    return files


def load_results():
    results = {}

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        for row in csv.DictReader(f):
            results[row["image"]] = row

    return results


def ffloat(value):
    try:
        return float(value)
    except Exception:
        return None


def main():

    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            f"Не найден CSV: {SOURCE_CSV}"
        )

    files = load_files()
    results = load_results()

    print("=" * 80)
    print("NEIGHBOR CONTEXT V34")
    print("=" * 80)

    print(f"Input images : {len(files)}")
    print(f"Recognition  : {len(results)}")
    print(f"Margin limit : {MARGIN_LIMIT}")
    print(f"Neighbor ±   : {NEIGHBOR_RADIUS}")
    print()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []
    changed = []
    counters = Counter()

    for index, path in enumerate(files):

        name = path.name
        r = results.get(name)

        if r is None:
            continue

        original = r.get("current_first", "")
        second = r.get("current_second", "")

        margin = ffloat(r.get("final_margin"))

        # По умолчанию ничего не меняем.
        final_id = original
        decision = "KEEP"
        reason = "margin>=0.005"

        neighbors = []

        # --------------------------------------------------
        # ONLY LOW-MARGIN CASES
        # --------------------------------------------------

        if (
            margin is not None
            and margin < MARGIN_LIMIT
            and second
        ):

            reason = "low_margin_no_neighbor_support"

            # --------------------------------------------------
            # LOOK ±2
            # --------------------------------------------------

            for delta in range(
                -NEIGHBOR_RADIUS,
                NEIGHBOR_RADIUS + 1,
            ):

                if delta == 0:
                    continue

                pos = index + delta

                if pos < 0 or pos >= len(files):
                    continue

                neighbor_path = files[pos]
                neighbor_result = results.get(
                    neighbor_path.name
                )

                if not neighbor_result:
                    continue

                neighbor_id = (
                    neighbor_result.get("current_first")
                    or ""
                )

                neighbor_score = ffloat(
                    neighbor_result.get("final_first")
                )

                neighbor_margin = ffloat(
                    neighbor_result.get("final_margin")
                )

                neighbors.append({
                    "delta": delta,
                    "file": neighbor_path.name,
                    "id": neighbor_id,
                    "score": neighbor_score,
                    "margin": neighbor_margin,
                })

            # --------------------------------------------------
            # CHECK WHETHER SECOND CANDIDATE
            # APPEARS AMONG NEIGHBORS
            # --------------------------------------------------

            second_votes = []

            for n in neighbors:

                if n["id"] != second:
                    continue

                if (
                    n["score"] is not None
                    and n["score"] >= NEIGHBOR_SCORE_MIN
                ):
                    second_votes.append(n)

            # --------------------------------------------------
            # DECISION
            # --------------------------------------------------

            if second_votes:

                # Второй кандидат подтверждён хотя бы
                # одним уверенным соседним кадром.
                final_id = second
                decision = "SWITCH_TO_SECOND"

                vote_text = ", ".join(
                    f'{x["delta"]:+d}:{x["file"]}'
                    for x in second_votes
                )

                reason = (
                    "second_supported_by_neighbors:"
                    + vote_text
                )

                changed.append({
                    "image": name,
                    "original": original,
                    "second": second,
                    "margin": margin,
                    "reason": reason,
                })

            else:
                reason = (
                    "low_margin_but_no_second_neighbor_support"
                )

        # --------------------------------------------------
        # COPY
        # --------------------------------------------------

        destination_dir = (
            OUTPUT_DIR / final_id
        )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            destination_dir / path.name
        )

        shutil.copy2(
            path,
            destination,
        )

        counters[final_id] += 1

        # --------------------------------------------------
        # REPORT ROW
        # --------------------------------------------------

        row = {
            "image": name,
            "index": index,
            "original_first": original,
            "second_candidate": second,
            "margin": margin,
            "final_decision": final_id,
            "decision_type": decision,
            "reason": reason,

            "prev2": "",
            "prev2_id": "",
            "prev2_score": "",

            "prev1": "",
            "prev1_id": "",
            "prev1_score": "",

            "next1": "",
            "next1_id": "",
            "next1_score": "",

            "next2": "",
            "next2_id": "",
            "next2_score": "",
        }

        for n in neighbors:

            if n["delta"] == -2:
                row["prev2"] = n["file"]
                row["prev2_id"] = n["id"]
                row["prev2_score"] = n["score"]

            elif n["delta"] == -1:
                row["prev1"] = n["file"]
                row["prev1_id"] = n["id"]
                row["prev1_score"] = n["score"]

            elif n["delta"] == 1:
                row["next1"] = n["file"]
                row["next1_id"] = n["id"]
                row["next1_score"] = n["score"]

            elif n["delta"] == 2:
                row["next2"] = n["file"]
                row["next2_id"] = n["id"]
                row["next2_score"] = n["score"]

        rows.append(row)

    # ------------------------------------------------------
    # CSV
    # ------------------------------------------------------

    fields = [
        "image",
        "index",
        "original_first",
        "second_candidate",
        "margin",
        "final_decision",
        "decision_type",
        "reason",

        "prev2",
        "prev2_id",
        "prev2_score",

        "prev1",
        "prev1_id",
        "prev1_score",

        "next1",
        "next1_id",
        "next1_score",

        "next2",
        "next2_id",
        "next2_score",
    ]

    with REPORT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)

    # ------------------------------------------------------
    # REPORT
    # ------------------------------------------------------

    low_margin = [
        r
        for r in rows
        if r["margin"] is not None
        and r["margin"] < MARGIN_LIMIT
    ]

    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(
        f"Total images:        {len(rows)}"
    )

    print(
        f"Margin < {MARGIN_LIMIT:.3f}:      "
        f"{len(low_margin)}"
    )

    print(
        f"Changed by neighbors: {len(changed)}"
    )

    if changed:

        print()
        print("CHANGED")
        print("-" * 80)

        for x in changed:

            print(
                f'{x["image"]}'
            )

            print(
                f'    {x["original"]} -> '
                f'{x["second"]}'
            )

            print(
                f'    margin={x["margin"]:.6f}'
            )

            print(
                f'    {x["reason"]}'
            )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for k in sorted(
        counters,
        key=lambda x: int(
            "".join(
                c for c in x
                if c.isdigit()
            ) or 9999
        ),
    ):

        print(
            f"{k:10s} {counters[k]:4d}"
        )

    print("-" * 80)
    print(
        f"TOTAL      {sum(counters.values()):4d}"
    )

    print()
    print("OUTPUT:")
    print(f"  sorted : {OUTPUT_DIR}")
    print(f"  report : {REPORT_CSV}")


if __name__ == "__main__":
    main()

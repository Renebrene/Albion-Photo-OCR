#!/usr/bin/env python3

import csv
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

INPUT_DIR = PROJECT / "data/input/test"

# Смотрим немного шире старого порога 0.005.
MARGIN_LIMIT = 0.020

# Соседи слева/справа.
NEIGHBOR_RADIUS = 2

# Минимальная уверенность соседа.
NEIGHBOR_SCORE_MIN = 0.80

# BEST должен выигрывать хотя бы на столько,
# чтобы считать его убедительным.
BEST_STRONG_DIFF = 0.05

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".JPG",
    ".JPEG",
    ".png",
    ".PNG",
}


def natural_key(path):
    parts = re.split(r"(\d+)", path.name)

    return [
        int(x) if x.isdigit() else x.lower()
        for x in parts
    ]


def ffloat(value):
    try:
        return float(value)
    except Exception:
        return None


def load_files():
    files = [
        p
        for p in INPUT_DIR.iterdir()
        if p.is_file()
        and p.suffix in IMAGE_EXTENSIONS
    ]

    files.sort(key=natural_key)

    return files


def load_results():

    results = {}

    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        for row in csv.DictReader(f):
            results[row["image"]] = row

    return results


def get_neighbors(files, results, index):

    neighbors = []

    for delta in range(
        -NEIGHBOR_RADIUS,
        NEIGHBOR_RADIUS + 1,
    ):

        if delta == 0:
            continue

        pos = index + delta

        if pos < 0 or pos >= len(files):
            continue

        p = files[pos]

        r = results.get(p.name)

        if not r:
            continue

        neighbor_id = r.get(
            "current_first",
            "",
        )

        score = ffloat(
            r.get("final_first")
        )

        margin = ffloat(
            r.get("final_margin")
        )

        neighbors.append({
            "delta": delta,
            "image": p.name,
            "id": neighbor_id,
            "score": score,
            "margin": margin,
        })

    return neighbors


def main():

    print("=" * 80)
    print("DRY RUN: BEST + SEQUENCE")
    print("=" * 80)

    print("CSV:", CSV_PATH)
    print("INPUT:", INPUT_DIR)
    print("MARGIN LIMIT:", MARGIN_LIMIT)
    print("BEST STRONG DIFF:", BEST_STRONG_DIFF)
    print("NEIGHBOR RADIUS:", NEIGHBOR_RADIUS)
    print()

    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    if not INPUT_DIR.exists():
        raise FileNotFoundError(INPUT_DIR)

    files = load_files()
    results = load_results()

    print(f"Images:     {len(files)}")
    print(f"Recognized: {len(results)}")
    print()

    checked = 0
    best_changes = 0
    sequence_changes = 0
    ambiguous = 0
    kept = 0

    print("=" * 80)
    print("SUSPICIOUS FRAMES")
    print("=" * 80)

    for index, path in enumerate(files):

        r = results.get(path.name)

        if not r:
            continue

        margin = ffloat(
            r.get("final_margin")
        )

        if margin is None:
            continue

        if margin >= MARGIN_LIMIT:
            continue

        checked += 1

        first = r.get(
            "current_first",
            "",
        )

        second = r.get(
            "current_second",
            "",
        )

        first_score = ffloat(
            r.get("final_first")
        )

        second_score = ffloat(
            r.get("final_second")
        )

        best_first = ffloat(
            r.get("best_first")
        )

        best_second = ffloat(
            r.get("best_second")
        )

        best_diff = ffloat(
            r.get("best_diff")
        )

        neighbors = get_neighbors(
            files,
            results,
            index,
        )

        # --------------------------------------------------
        # BEST
        # --------------------------------------------------

        best_decision = None
        best_reason = ""

        if (
            best_diff is not None
            and best_diff >= BEST_STRONG_DIFF
        ):

            best_decision = second

            best_reason = (
                "BEST strongly supports TOP2"
            )

        elif (
            best_diff is not None
            and best_diff <= -BEST_STRONG_DIFF
        ):

            best_decision = first

            best_reason = (
                "BEST strongly supports TOP1"
            )

        else:

            best_reason = (
                "BEST inconclusive"
            )

        # --------------------------------------------------
        # SEQUENCE
        # --------------------------------------------------

        neighbor_first_votes = []
        neighbor_second_votes = []

        for n in neighbors:

            if (
                n["score"] is not None
                and n["score"] < NEIGHBOR_SCORE_MIN
            ):
                continue

            if n["id"] == first:
                neighbor_first_votes.append(n)

            if n["id"] == second:
                neighbor_second_votes.append(n)

        sequence_decision = None
        sequence_reason = ""

        if (
            len(neighbor_first_votes)
            >= 2
        ):

            sequence_decision = first

            sequence_reason = (
                "neighbors strongly support TOP1"
            )

        elif (
            len(neighbor_second_votes)
            >= 2
        ):

            sequence_decision = second

            sequence_reason = (
                "neighbors strongly support TOP2"
            )

        else:

            sequence_reason = (
                "sequence inconclusive"
            )

        # --------------------------------------------------
        # FINAL PROPOSED DECISION
        #
        # PRIORITY:
        #
        # 1. Strong BEST
        # 2. Strong sequence
        # 3. Keep TOP1
        #
        # This is DRY RUN only.
        # --------------------------------------------------

        decision = first
        reason = "KEEP_TOP1"

        if best_decision is not None:

            decision = best_decision
            reason = best_reason

            if decision != first:
                best_changes += 1

        elif sequence_decision is not None:

            decision = sequence_decision
            reason = sequence_reason

            if decision != first:
                sequence_changes += 1

        else:

            kept += 1

            if (
                best_diff is not None
                and abs(best_diff)
                < BEST_STRONG_DIFF
            ):
                ambiguous += 1

        # --------------------------------------------------
        # PRINT
        # --------------------------------------------------

        print()
        print("-" * 80)

        print(
            f"{index:4d} {path.name}"
        )

        print(
            f"  DINO:   "
            f"{first} vs {second} "
            f"margin={margin:.6f}"
        )

        print(
            f"  SCORE:  "
            f"{first_score if first_score is not None else 0:.4f} "
            f"vs "
            f"{second_score if second_score is not None else 0:.4f}"
        )

        print(
            f"  BEST:   "
            f"{best_first if best_first is not None else 0:.4f} "
            f"vs "
            f"{best_second if best_second is not None else 0:.4f} "
            f"diff={best_diff if best_diff is not None else 0:+.6f}"
        )

        print(
            f"  BEST:   "
            f"{best_decision or '-'} "
            f"({best_reason})"
        )

        if neighbors:

            text = " | ".join(
                f'{n["delta"]:+d}:'
                f'{n["id"]}'
                f'({n["score"]:.3f}'
                if n["score"] is not None
                else f'{n["delta"]:+d}:{n["id"]}'
                for n in neighbors
            )

            print(
                f"  NEIGH:  {text}"
            )

        print(
            f"  SEQ:    "
            f"{sequence_decision or '-'} "
            f"({sequence_reason})"
        )

        print(
            f"  >>>     "
            f"{first} -> {decision}"
        )

        print(
            f"  REASON: "
            f"{reason}"
        )

    print()
    print("=" * 80)
    print("DRY RUN SUMMARY")
    print("=" * 80)

    print(
        f"Suspicious frames:       {checked}"
    )

    print(
        f"Changed by BEST:         {best_changes}"
    )

    print(
        f"Changed by SEQUENCE:     {sequence_changes}"
    )

    print(
        f"Kept TOP1:               {kept}"
    )

    print(
        f"Still ambiguous:         {ambiguous}"
    )

    print()
    print("NO FILES WERE MODIFIED.")
    print("=" * 80)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import csv
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent

SRC = (
    PROJECT
    / "data/output/benchmark_v1/benchmark.json"
)

DST = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)


def norm_id(x):
    if not x:
        return ""

    return str(x).replace("_v33", "")


def main():

    print("=" * 80)
    print("BUILD margin_best.csv FROM benchmark.json")
    print("=" * 80)

    print("SOURCE:", SRC)
    print("DEST  :", DST)

    if not SRC.exists():
        raise FileNotFoundError(SRC)

    DST.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with SRC.open(
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    rows = []

    for r in data["results"]:

        first = r.get("top1")
        second = r.get("top2")

        first_score = float(
            r.get("top1_score") or 0
        )

        second_score = float(
            r.get("top2_score") or 0
        )

        margin = (
            first_score
            -
            second_score
        )

        # Совместимость со старым BEST
        #
        # best_diff > 0 означает победу второго кандидата
        #
        # Но пока BEST = TOP1.
        #
        best_first = first_score
        best_second = second_score

        best_diff = (
            best_first
            -
            best_second
        )

        rows.append({

            "image":
                Path(r["file"]).name,

            "current_first":
                norm_id(first),

            "current_second":
                norm_id(second),

            "final_first":
                first_score,

            "final_second":
                second_score,

            "final_margin":
                margin,

            "best_first":
                best_first,

            "best_second":
                best_second,

            "best_diff":
                best_diff,

            "best_image":
                r.get("best_image",""),

        })


    fields = list(rows[0].keys())


    with DST.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


    print()
    print("ROWS:", len(rows))
    print("DONE")
    print(DST)


if __name__ == "__main__":
    main()

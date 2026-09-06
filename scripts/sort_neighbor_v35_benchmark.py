#!/usr/bin/env python3

import csv
import json
import shutil
from pathlib import Path
from collections import Counter

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"
SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v35_benchmark"
SORTED_DIR = OUTPUT_DIR / "sorted"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005
NEIGHBOR_RADIUS = 2

FINGERPRINTS = list(range(78, 96))


def norm_id(value):
    if value is None:
        return None

    s = str(value)

    if "_" in s:
        s = s.split("_")[0]

    try:
        return int(s)
    except ValueError:
        return None


def load_results():
    with SOURCE_JSON.open(encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]

    # Сохраняем порядок файлов именно такой,
    # в каком benchmark их распознал.
    return results


def candidate_ids(row):
    result = []

    for key in ("top1", "top2", "top3", "top4", "top5"):
        value = norm_id(row.get(key))
        if value is not None:
            result.append(value)

    return result


def main():

    if not SOURCE_JSON.exists():
        raise RuntimeError(f"Нет benchmark: {SOURCE_JSON}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SORTED_DIR.mkdir(parents=True, exist_ok=True)

    results = load_results()

    # Для поиска соседей используем только фотографии,
    # реально присутствующие в test.
    results = [
        r for r in results
        if (INPUT_DIR / Path(r["file"]).name).exists()
    ]

    print("=" * 80)
    print("NEIGHBOR CONTEXT V35 — NEW BENCHMARK")
    print("=" * 80)
    print(f"Input images : {len(results)}")
    print(f"Margin limit : {MARGIN_LIMIT}")
    print(f"Neighbor +/- : {NEIGHBOR_RADIUS}")
    print()

    decisions = []
    changed = []

    for i, row in enumerate(results):

        image = Path(row["file"]).name

        current = norm_id(row.get("top1"))
        second = norm_id(row.get("top2"))

        top1_score = float(row.get("top1_score") or 0)
        top2_score = float(row.get("top2_score") or 0)

        margin = top1_score - top2_score

        final = current
        reason = "V33"

        second_neighbors = []
        current_neighbors = []

        if margin < MARGIN_LIMIT and second is not None:

            start = max(0, i - NEIGHBOR_RADIUS)
            end = min(len(results), i + NEIGHBOR_RADIUS + 1)

            for j in range(start, end):

                if j == i:
                    continue

                neighbor = results[j]

                n_candidates = candidate_ids(neighbor)

                if second in n_candidates:
                    second_neighbors.append(
                        (j - i, Path(neighbor["file"]).name)
                    )

                if current in n_candidates:
                    current_neighbors.append(
                        (j - i, Path(neighbor["file"]).name)
                    )

            # Правило:
            # если второй кандидат поддержан минимум 2 соседями
            # и текущий не получает больше поддержки —
            # меняем на второй.
            if (
                len(second_neighbors) >= 2
                and len(second_neighbors) > len(current_neighbors)
            ):
                final = second
                reason = "SECOND_SUPPORTED_BY_2+_NEIGHBORS"

            elif len(second_neighbors) == 1:
                reason = "ONE_NEIGHBOR_KEEP_V33"

            elif (
                len(current_neighbors) >= 1
                and len(current_neighbors) >= len(second_neighbors)
            ):
                reason = "CURRENT_SUPPORTED_KEEP_V33"

            else:
                reason = "NO_NEIGHBOR_EVIDENCE"

        if final != current:
            changed.append({
                "image": image,
                "old": current,
                "new": final,
                "second": second,
                "margin": margin,
                "reason": reason,
                "second_neighbors": second_neighbors,
                "current_neighbors": current_neighbors,
            })

        decisions.append({
            "image": image,
            "v33": current,
            "second": second,
            "final": final,
            "margin": margin,
            "second_neighbor_count": len(second_neighbors),
            "current_neighbor_count": len(current_neighbors),
            "reason": reason,
            "second_neighbors": "; ".join(
                f"{offset:+d}:{name}"
                for offset, name in second_neighbors
            ),
            "current_neighbors": "; ".join(
                f"{offset:+d}:{name}"
                for offset, name in current_neighbors
            ),
        })

    # ------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------

    with REPORT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
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
            ],
        )

        writer.writeheader()
        writer.writerows(decisions)

    # ------------------------------------------------------------
    # SORTED OUTPUT
    # ------------------------------------------------------------

    for d in decisions:

        image = d["image"]
        final = d["final"]

        if final is None:
            continue

        folder = SORTED_DIR / str(final)
        folder.mkdir(parents=True, exist_ok=True)

        src = INPUT_DIR / image
        dst = folder / image

        shutil.copy2(src, dst)

    # ------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------

    distribution = Counter(
        d["final"]
        for d in decisions
        if d["final"] is not None
    )

    margin_count = sum(
        float(d["margin"]) < MARGIN_LIMIT
        for d in decisions
    )

    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(f"Total images:        {len(decisions)}")
    print(f"Margin < {MARGIN_LIMIT}:      {margin_count}")
    print(f"Changed by neighbors:       {len(changed)}")

    print()

    if changed:
        print("CHANGED")
        print("-" * 80)

        for x in changed:
            print(x["image"])
            print(
                f"    {x['old']} -> {x['new']}"
            )
            print(
                f"    margin={x['margin']:.6f}"
            )
            print(
                f"    reason={x['reason']}"
            )

            if x["second_neighbors"]:
                print(
                    "    second: "
                    + "; ".join(
                        f"{offset:+d}:{name}"
                        for offset, name
                        in x["second_neighbors"]
                    )
                )

            print()

    print("DISTRIBUTION")
    print("-" * 80)

    for n in FINGERPRINTS:
        print(
            f"{n:<4} {distribution.get(n, 0):4d}"
        )

    print("-" * 80)
    print(
        f"TOTAL {sum(distribution.values()):10d}"
    )

    print()
    print("OUTPUT:")
    print(f"  sorted : {SORTED_DIR}")
    print(f"  report : {REPORT_CSV}")


if __name__ == "__main__":
    main()

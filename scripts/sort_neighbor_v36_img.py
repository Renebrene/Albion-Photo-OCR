#!/usr/bin/env python3

import json
import csv
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test_img"
SOURCE_JSON = PROJECT / "data/output/benchmark_img/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v36_img"
SORTED_DIR = OUTPUT_DIR / "sorted"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005


def normalize_id(x):
    if not x:
        return ""
    return str(x).replace("_v33", "")


def get_candidates(row):
    result = []

    for c in row.get("candidates", []):
        cid = normalize_id(c.get("id"))
        score = c.get("score")

        if cid:
            result.append((cid, float(score or 0)))

    # benchmark.json может содержать уже распакованные top1/top2...
    if not result:
        for i in range(1, 6):
            cid = normalize_id(row.get(f"top{i}"))
            score = row.get(f"top{i}_score")

            if cid:
                result.append((cid, float(score or 0)))

    return result


def candidate_in_neighbor(row, candidate):
    """
    Считаем, что сосед поддерживает candidate,
    если candidate находится в его TOP-2.
    """

    candidates = get_candidates(row)

    for cid, score in candidates[:2]:
        if cid == candidate:
            return True, score

    return False, 0.0


def main():

    if not SOURCE_JSON.exists():
        raise RuntimeError(f"Нет {SOURCE_JSON}")

    with SOURCE_JSON.open(encoding="utf-8") as f:
        data = json.load(f)

    rows = data["results"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SORTED_DIR.mkdir(parents=True, exist_ok=True)

    decisions = []
    changed = []

    for i, row in enumerate(rows):

        filename = Path(row["file"]).name

        candidates = get_candidates(row)

        if not candidates:
            continue

        current = candidates[0][0]
        second = candidates[1][0] if len(candidates) > 1 else ""

        current_score = candidates[0][1]
        second_score = candidates[1][1] if len(candidates) > 1 else 0.0

        margin = current_score - second_score

        final = current
        reason = "V33"

        next_support = []
        prev_support = []

        # ------------------------------------------------------------
        # Только сомнительные изображения
        # ------------------------------------------------------------

        if margin < MARGIN_LIMIT and second:

            # ========================================================
            # 1. СНАЧАЛА СМОТРИМ +1 и +2
            # ========================================================

            for j in (i + 1, i + 2):

                if j >= len(rows):
                    continue

                ok, score = candidate_in_neighbor(
                    rows[j],
                    second,
                )

                if ok:
                    next_support.append(
                        (j, Path(rows[j]["file"]).name, score)
                    )

            # ========================================================
            # Правило:
            #
            # +1 или +2 поддерживает кандидата 2
            #
            # Но если оба следующие явно указывают на текущего
            # кандидата, не меняем.
            # ========================================================

            if next_support:

                current_next = 0

                for j in (i + 1, i + 2):

                    if j >= len(rows):
                        continue

                    ok, _ = candidate_in_neighbor(
                        rows[j],
                        current,
                    )

                    if ok:
                        current_next += 1

                if current_next == 0:

                    final = second
                    reason = "SECOND_SUPPORTED_FORWARD"

                elif len(next_support) > current_next:

                    final = second
                    reason = "SECOND_FORWARD_STRONGER"

                else:

                    reason = "FORWARD_CONFLICT_KEEP_V33"

            # ========================================================
            # 2. Если вперёд кандидат 2 НЕ найден —
            #    смотрим -1 и -2
            # ========================================================

            if not next_support:

                for j in (i - 1, i - 2):

                    if j < 0:
                        continue

                    ok, score = candidate_in_neighbor(
                        rows[j],
                        second,
                    )

                    if ok:
                        prev_support.append(
                            (j, Path(rows[j]["file"]).name, score)
                        )

                if prev_support:

                    current_prev = 0

                    for j in (i - 1, i - 2):

                        if j < 0:
                            continue

                        ok, _ = candidate_in_neighbor(
                            rows[j],
                            current,
                        )

                        if ok:
                            current_prev += 1

                    if current_prev == 0:

                        final = second
                        reason = "SECOND_SUPPORTED_BACKWARD"

                    elif len(prev_support) > current_prev:

                        final = second
                        reason = "SECOND_BACKWARD_STRONGER"

                    else:

                        reason = "BACKWARD_CONFLICT_KEEP_V33"

                else:

                    reason = "NO_NEIGHBOR_SUPPORT"

        item = {
            "index": i,
            "image": filename,
            "v33": current,
            "second": second,
            "final": final,
            "margin": margin,
            "reason": reason,
            "forward_support": len(next_support),
            "backward_support": len(prev_support),
            "forward_neighbors": "; ".join(
                f"+{j-i}:{name}"
                for j, name, score in next_support
            ),
            "backward_neighbors": "; ".join(
                f"{j-i}:{name}"
                for j, name, score in prev_support
            ),
        }

        decisions.append(item)

        if final != current:
            changed.append(item)

    # ================================================================
    # Копирование
    # ================================================================

    for item in decisions:

        filename = item["image"]
        final = item["final"]

        src = INPUT_DIR / filename

        if not src.exists():
            continue

        folder = SORTED_DIR / final
        folder.mkdir(parents=True, exist_ok=True)

        shutil.copy2(
            src,
            folder / filename,
        )

    # ================================================================
    # CSV
    # ================================================================

    fields = [
        "index",
        "image",
        "v33",
        "second",
        "final",
        "margin",
        "reason",
        "forward_support",
        "backward_support",
        "forward_neighbors",
        "backward_neighbors",
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
        writer.writerows(decisions)

    # ================================================================
    # OUTPUT
    # ================================================================

    print("=" * 80)
    print("NEIGHBOR CONTEXT V36")
    print("=" * 80)

    print(f"Input images : {len(rows)}")
    print(f"Margin limit : {MARGIN_LIMIT}")
    print("Neighbor logic : +1,+2 -> -1,-2")
    print("Neighbor match : TOP-2")
    print()

    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    uncertain = sum(
        1
        for x in decisions
        if x["margin"] < MARGIN_LIMIT
    )

    print(f"Total images:        {len(decisions)}")
    print(f"Margin < {MARGIN_LIMIT}:      {uncertain}")
    print(f"Changed by neighbors:       {len(changed)}")

    if changed:

        print()
        print("CHANGED")
        print("-" * 80)

        for x in changed:

            print(x["image"])
            print(
                f"    {x['v33']} -> {x['final']}"
            )
            print(
                f"    margin={x['margin']:.6f}"
            )
            print(
                f"    reason={x['reason']}"
            )

            if x["forward_neighbors"]:
                print(
                    f"    forward: {x['forward_neighbors']}"
                )

            if x["backward_neighbors"]:
                print(
                    f"    backward: {x['backward_neighbors']}"
                )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    from collections import Counter

    dist = Counter(
        x["final"]
        for x in decisions
    )

    for n in range(78, 96):
        print(
            f"{n:<4} {dist[str(n)]:5}"
        )

    print("-" * 80)
    print(
        f"TOTAL {sum(dist.values()):10}"
    )

    print()
    print("OUTPUT:")
    print(f"  sorted : {SORTED_DIR}")
    print(f"  report : {REPORT_CSV}")


if __name__ == "__main__":
    main()

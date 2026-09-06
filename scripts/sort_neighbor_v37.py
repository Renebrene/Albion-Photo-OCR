#!/usr/bin/env python3

import csv
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/new"
SOURCE_JSON = PROJECT / "data/output/benchmark_img/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v37"
SORTED_DIR = OUTPUT_DIR / "sorted"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005


def normalize_id(x):
    try:
        return int(str(x).replace("_v33", ""))
    except Exception:
        return None


def get_results(item):
    """
    Поддерживаем возможные варианты структуры benchmark.json.
    """
    results = (
        item.get("results")
        or item.get("predictions")
        or item.get("candidates")
        or item.get("top_k")
    )

    if isinstance(results, dict):
        results = list(results.items())

    if not isinstance(results, list):
        return []

    out = []

    for r in results:
        if isinstance(r, dict):
            fp = (
                r.get("fingerprint")
                or r.get("id")
                or r.get("label")
                or r.get("name")
            )
            score = (
                r.get("score")
                if r.get("score") is not None
                else r.get("similarity")
            )

            if fp is not None:
                try:
                    score = float(score)
                except Exception:
                    score = 0.0
                out.append((normalize_id(fp), score))

        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            out.append((normalize_id(r[0]), float(r[1])))

    return [(fp, score) for fp, score in out if fp is not None]


def get_image(item):
    for key in ("image", "filename", "file", "path", "name"):
        value = item.get(key)
        if value:
            return Path(str(value)).name
    return None


with open(SOURCE_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict):
    items = (
        data.get("results")
        or data.get("images")
        or data.get("items")
        or data.get("data")
    )
else:
    items = data

if not isinstance(items, list):
    raise RuntimeError("Не удалось найти список результатов в benchmark.json")


records = []

for item in items:
    image = get_image(item)
    results = get_results(item)

    if not image or not results:
        continue

    top1 = results[0][0]
    top1_score = results[0][1]

    top2 = results[1][0] if len(results) > 1 else None
    top2_score = results[1][1] if len(results) > 1 else None

    margin = (
        top1_score - top2_score
        if top2_score is not None
        else 999.0
    )

    records.append({
        "image": image,
        "top1": top1,
        "top1_score": top1_score,
        "top2": top2,
        "top2_score": top2_score,
        "margin": margin,
    })


# Очень важно:
# сортируем по реальному имени img_000, img_001...
# а не по порядку JSON.
def image_number(r):
    name = Path(r["image"]).stem
    digits = "".join(c for c in name if c.isdigit())
    return int(digits) if digits else 10**9


records.sort(key=image_number)

changed = []
rows = []

for i, rec in enumerate(records):

    v33 = rec["top1"]
    second = rec["top2"]
    margin = rec["margin"]

    final = v33
    reason = "V33"

    forward_support = []
    backward_support = []

    forward_neighbors = []
    backward_neighbors = []

    # Работаем только с сомнительными кадрами.
    if margin < MARGIN_LIMIT and second is not None:

        # ------------------------------------------------------------
        # 1. СНАЧАЛА СМОТРИМ ВПЕРЕД
        # ------------------------------------------------------------
        for offset in (1, 2):
            j = i + offset

            if j >= len(records):
                continue

            neighbor = records[j]
            nid = neighbor["top1"]

            forward_neighbors.append(
                f"+{offset}:{neighbor['image']}={nid}"
            )

            if nid == second:
                forward_support.append(offset)

        # Если хотя бы один из следующих двух кадров
        # подтверждает кандидата №2 — выбираем его.
        if forward_support:
            final = second
            reason = "FORWARD_SUPPORT_TOP2"

        else:

            # --------------------------------------------------------
            # 2. ЕСЛИ ВПЕРЕДИ НЕ ПОДТВЕРДИЛОСЬ — СМОТРИМ НАЗАД
            # --------------------------------------------------------
            for offset in (1, 2):
                j = i - offset

                if j < 0:
                    continue

                neighbor = records[j]
                nid = neighbor["top1"]

                backward_neighbors.append(
                    f"-{offset}:{neighbor['image']}={nid}"
                )

                if nid == second:
                    backward_support.append(offset)

            if backward_support:
                final = second
                reason = "BACKWARD_SUPPORT_TOP2"
            else:
                reason = "NO_NEIGHBOR_SUPPORT"

    if final != v33:
        changed.append({
            "image": rec["image"],
            "v33": v33,
            "second": second,
            "final": final,
            "margin": margin,
            "reason": reason,
            "forward_support": forward_support,
            "backward_support": backward_support,
        })

    rows.append({
        "index": i,
        "image": rec["image"],
        "v33": v33,
        "second": second,
        "final": final,
        "margin": margin,
        "reason": reason,
        "forward_support": ",".join(map(str, forward_support)),
        "backward_support": ",".join(map(str, backward_support)),
        "forward_neighbors": "; ".join(forward_neighbors),
        "backward_neighbors": "; ".join(backward_neighbors),
    })


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if SORTED_DIR.exists():
    shutil.rmtree(SORTED_DIR)

SORTED_DIR.mkdir(parents=True)

for row in rows:
    src = INPUT_DIR / row["image"]

    if not src.exists():
        continue

    destination = SORTED_DIR / str(row["final"])
    destination.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, destination / src.name)


with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
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
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


print("=" * 80)
print("NEIGHBOR CONTEXT V37")
print("=" * 80)
print(f"Input images : {len(records)}")
print(f"Margin limit : {MARGIN_LIMIT}")
print("Neighbor logic : +1,+2 -> -1,-2")
print("Neighbor match : TOP-1 of neighbor == TOP-2 of current")
print()

print("=" * 80)
print("RESULT")
print("=" * 80)

ambiguous = sum(1 for r in rows if r["margin"] < MARGIN_LIMIT)

print(f"Total images:        {len(rows)}")
print(f"Margin < 0.005:      {ambiguous}")
print(f"Changed by neighbors:{len(changed):8d}")

if changed:
    print()
    print("CHANGED")
    print("-" * 80)

    for x in changed:
        print(
            f"{x['image']}: "
            f"{x['v33']} -> {x['final']} "
            f"(second={x['second']}, "
            f"margin={x['margin']:.6f}, "
            f"{x['reason']})"
        )

print()
print("DISTRIBUTION")
print("-" * 80)

distribution = {}

for row in rows:
    distribution[row["final"]] = distribution.get(row["final"], 0) + 1

for fp in sorted(distribution):
    print(f"{fp:<8} {distribution[fp]:>4}")

print("-" * 80)
print(f"TOTAL    {len(rows):>8}")

print()
print("OUTPUT:")
print(f"  sorted : {SORTED_DIR}")
print(f"  report : {REPORT_CSV}")

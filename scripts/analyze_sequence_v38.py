#!/usr/bin/env python3

import csv
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPORT = PROJECT / "output/neighbor_v37/neighbor_decision.csv"

with open(REPORT, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Реальный порядок img_000, img_001...
rows.sort(key=lambda r: int(
    "".join(c for c in Path(r["image"]).stem if c.isdigit())
))

print("=" * 80)
print("SEQUENCE ANALYSIS V38")
print("=" * 80)
print(f"Images: {len(rows)}")
print()

# ------------------------------------------------------------
# Ищем места, где TOP-1 меняется между соседними кадрами
# ------------------------------------------------------------

changes = []

for i in range(1, len(rows)):
    prev = int(rows[i - 1]["v33"])
    cur = int(rows[i]["v33"])

    if prev != cur:
        changes.append(i)


print("=" * 80)
print("ADDRESS TRANSITIONS")
print("=" * 80)

if not changes:
    print("No transitions.")
else:
    for i in changes:
        print()
        print(
            f"TRANSITION BEFORE {rows[i]['image']}: "
            f"{rows[i-1]['v33']} -> {rows[i]['v33']}"
        )

        start = max(0, i - 3)
        end = min(len(rows), i + 4)

        for j in range(start, end):
            r = rows[j]

            marker = "   "

            if j == i:
                marker = ">>>"
            elif j == i - 1:
                marker = "---"

            print(
                f"{marker} "
                f"{j:3d} "
                f"{r['image']:15s} "
                f"TOP1={r['v33']:>2} "
                f"TOP2={r['second']:>2} "
                f"margin={float(r['margin']):.6f}"
            )


# ------------------------------------------------------------
# Сомнительные кадры
# ------------------------------------------------------------

print()
print("=" * 80)
print("UNCERTAIN ZONES")
print("=" * 80)

uncertain = [
    i for i, r in enumerate(rows)
    if float(r["margin"]) < 0.005
]

if not uncertain:
    print("No uncertain images.")
else:

    printed_zones = set()

    for i in uncertain:

        # Группируем близкие сомнительные кадры
        zone_start = max(0, i - 2)
        zone_end = min(len(rows) - 1, i + 2)

        key = (zone_start, zone_end)

        if key in printed_zones:
            continue

        printed_zones.add(key)

        print()
        print(
            f"ZONE around {rows[i]['image']} "
            f"(index {i})"
        )
        print("-" * 80)

        start = max(0, i - 4)
        end = min(len(rows), i + 5)

        for j in range(start, end):
            r = rows[j]

            mark = "   "

            if j == i:
                mark = ">>>"

            print(
                f"{mark} "
                f"{j:3d} "
                f"{r['image']:15s} "
                f"TOP1={r['v33']:>2} "
                f"TOP2={r['second']:>2} "
                f"margin={float(r['margin']):.6f}"
            )


# ------------------------------------------------------------
# Серии одинакового TOP-1
# ------------------------------------------------------------

print()
print("=" * 80)
print("SEQUENTIAL GROUPS")
print("=" * 80)

groups = []

start = 0
current = int(rows[0]["v33"])

for i in range(1, len(rows)):

    value = int(rows[i]["v33"])

    if value != current:

        groups.append((start, i - 1, current))
        start = i
        current = value

groups.append((start, len(rows) - 1, current))

for start, end, fp in groups:

    size = end - start + 1

    # Показываем короткие группы — именно они наиболее интересны
    if size <= 3:

        print(
            f"{start:3d}-{end:3d} "
            f"size={size} "
            f"FP={fp}"
        )

        for i in range(start, end + 1):
            r = rows[i]

            print(
                f"       {r['image']:15s} "
                f"TOP1={r['v33']} "
                f"TOP2={r['second']} "
                f"margin={float(r['margin']):.6f}"
            )


print()
print("=" * 80)
print("DONE")
print("=" * 80)

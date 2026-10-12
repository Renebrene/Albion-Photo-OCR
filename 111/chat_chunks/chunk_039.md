## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 12:40:59

Да. Давай сделаем отдельный анализ **всех 262 фото**, без изменения основного алгоритма.

Скрипт будет брать уже готовый:

```text
output/benchmark_components/components.csv
```

и для каждой фотографии определять:

- `SAFE` — большой отрыв первого кандидата;
- `BORDERLINE` — маленький `FINAL_MARGIN`;
- `BEST_CONFLICT` — второй кандидат выигрывает по `BEST`;
- `STRONG_BEST_CONFLICT` — второй кандидат выигрывает по `BEST` существенно;
- отдельно соберём **все пары `FIRST → SECOND`**;
- отдельно — **TOP-50 конфликтов**;
- отдельно — случаи, где `BEST` реально предлагает другого кандидата.

Создай скрипт:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/analyze_all_262.py <<'PY'
from pathlib import Path
import csv
from collections import Counter, defaultdict

INPUT = Path("output/benchmark_components/components.csv")
OUTDIR = Path("output/benchmark_components/full_analysis_262")
OUTDIR.mkdir(parents=True, exist_ok=True)

REPORT = OUTDIR / "all_262_analysis.txt"
CSV_OUT = OUTDIR / "all_262_analysis.csv"

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded rows: {len(rows)}")

# ------------------------------------------------------------
# GROUP BY IMAGE
# ------------------------------------------------------------

groups = defaultdict(list)

for row in rows:
    groups[row["image"]].append(row)

data = {}

for image, items in groups.items():

    items.sort(key=lambda x: int(x["rank"]))

    if len(items) < 2:
        continue

    first = items[0]
    second = items[1]

    final1 = float(first["final"])
    final2 = float(second["final"])

    best1 = float(first["BEST"])
    best2 = float(second["BEST"])

    margin = final1 - final2
    best_diff = best2 - best1

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if margin < 0.003:
        margin_class = "VERY_BORDERLINE"
    elif margin < 0.005:
        margin_class = "BORDERLINE"
    elif margin < 0.010:
        margin_class = "LOW_MARGIN"
    elif margin < 0.020:
        margin_class = "MEDIUM_MARGIN"
    else:
        margin_class = "SAFE"

    if best_diff >= 0.050:
        conflict_class = "STRONG_BEST_CONFLICT"
    elif best_diff >= 0.020:
        conflict_class = "BEST_CONFLICT"
    elif best_diff > 0:
        conflict_class = "WEAK_BEST_CONFLICT"
    else:
        conflict_class = "NO_BEST_CONFLICT"

    data[image] = {
        "first": first,
        "second": second,
        "margin": margin,
        "best_diff": best_diff,
        "margin_class": margin_class,
        "conflict_class": conflict_class,
    }

print(f"Images: {len(data)}")

# ------------------------------------------------------------
# CSV
# ------------------------------------------------------------

with CSV_OUT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "image",
        "first",
        "second",
        "final_first",
        "final_second",
        "final_margin",
        "best_first",
        "best_second",
        "best_diff",
        "margin_class",
        "conflict_class",
    ])

    for image, d in data.items():

        a = d["first"]
        b = d["second"]

        writer.writerow([
            image,
            a["id"],
            b["id"],
            a["final"],
            b["final"],
            f'{d["margin"]:.6f}',
            a["BEST"],
            b["BEST"],
            f'{d["best_diff"]:.6f}',
            d["margin_class"],
            d["conflict_class"],
        ])

# ============================================================
# REPORT
# ============================================================

with REPORT.open("w", encoding="utf-8") as out:

    out.write("=" * 120 + "\n")
    out.write("FULL ANALYSIS — ALL 262 IMAGES\n")
    out.write("=" * 120 + "\n")
    out.write(f"Images: {len(data)}\n")
    out.write("\n")

    # ========================================================
    # 1. MARGIN DISTRIBUTION
    # ========================================================

    out.write("=" * 120 + "\n")
    out.write("1. FINAL MARGIN DISTRIBUTION\n")
    out.write("=" * 120 + "\n")

    margin_limits = [
        ("< 0.001", 0.001),
        ("< 0.002", 0.002),
        ("< 0.003", 0.003),
        ("< 0.005", 0.005),
        ("< 0.010", 0.010),
        ("< 0.020", 0.020),
        ("< 0.030", 0.030),
    ]

    for label, limit in margin_limits:
        count = sum(
            1 for d in data.values()
            if d["margin"] < limit
        )

        pct = 100 * count / len(data)

        out.write(
            f"{label:<12} "
            f"{count:>4} / {len(data)} "
            f"({pct:>6.2f}%)\n"
        )

    # ========================================================
    # 2. MARGIN CLASSES
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("2. MARGIN CLASSES\n")
    out.write("=" * 120 + "\n")

    margin_counter = Counter(
        d["margin_class"]
        for d in data.values()
    )

    order = [
        "VERY_BORDERLINE",
        "BORDERLINE",
        "LOW_MARGIN",
        "MEDIUM_MARGIN",
        "SAFE",
    ]

    for key in order:

        count = margin_counter[key]
        pct = 100 * count / len(data)

        out.write(
            f"{key:<20} "
            f"{count:>4} "
            f"({pct:>6.2f}%)\n"
        )

    # ========================================================
    # 3. BEST CONFLICT DISTRIBUTION
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("3. BEST CONFLICT DISTRIBUTION\n")
    out.write("=" * 120 + "\n")

    conflict_counter = Counter(
        d["conflict_class"]
        for d in data.values()
    )

    order = [
        "STRONG_BEST_CONFLICT",
        "BEST_CONFLICT",
        "WEAK_BEST_CONFLICT",
        "NO_BEST_CONFLICT",
    ]

    for key in order:

        count = conflict_counter[key]
        pct = 100 * count / len(data)

        out.write(
            f"{key:<25} "
            f"{count:>4} "
            f"({pct:>6.2f}%)\n"
        )

    # ========================================================
    # 4. BEST CONFLICT + LOW MARGIN
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("4. BEST CONFLICT + LOW FINAL MARGIN\n")
    out.write("=" * 120 + "\n")

    thresholds = [
        (0.003, 0.020),
        (0.005, 0.020),
        (0.010, 0.020),
        (0.020, 0.020),
        (0.005, 0.050),
        (0.010, 0.050),
    ]

    for margin_limit, best_limit in thresholds:

        matches = [
            d for d in data.values()
            if d["margin"] < margin_limit
            and d["best_diff"] >= best_limit
        ]

        pct = 100 * len(matches) / len(data)

        out.write(
            f"MARGIN < {margin_limit:.3f} "
            f"AND BEST_DIFF >= {best_limit:.3f}: "
            f"{len(matches):>3} "
            f"({pct:.2f}%)\n"
        )

    # ========================================================
    # 5. TOP 50 BEST CONFLICTS
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("5. TOP 50 BEST CONFLICTS\n")
    out.write("=" * 120 + "\n")

    conflicts = sorted(
        data.items(),
        key=lambda x: x[1]["best_diff"],
        reverse=True
    )

    for image, d in conflicts[:50]:

        a = d["first"]
        b = d["second"]

        out.write(
            f"BEST_DIFF={d['best_diff']:+.6f} "
            f"FINAL_MARGIN={d['margin']:.6f} | "
            f"{a['id']} / {b['id']} | "
            f"{image}\n"
        )

    # ========================================================
    # 6. ALL POSITIVE BEST CONFLICTS
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("6. ALL POSITIVE BEST CONFLICTS\n")
    out.write("=" * 120 + "\n")

    positive = [
        (image, d)
        for image, d in data.items()
        if d["best_diff"] > 0
    ]

    positive.sort(
        key=lambda x: x[1]["best_diff"],
        reverse=True
    )

    out.write(
        f"Total: {len(positive)} / {len(data)} "
        f"({100 * len(positive) / len(data):.2f}%)\n\n"
    )

    for image, d in positive:

        a = d["first"]
        b = d["second"]

        out.write(
            f"{image}\n"
            f"  FINAL : {a['id']} = {a['final']}  "
            f"{b['id']} = {b['final']}\n"
            f"  MARGIN: {d['margin']:.6f}\n"
            f"  BEST  : {a['id']} = {a['BEST']}  "
            f"{b['id']} = {b['BEST']}\n"
            f"  DIFF  : {d['best_diff']:+.6f}\n"
            f"  CLASS : {d['margin_class']} / "
            f"{d['conflict_class']}\n"
            "\n"
        )

    # ========================================================
    # 7. TRANSITION MATRIX
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("7. FIRST -> SECOND TRANSITION MATRIX\n")
    out.write("=" * 120 + "\n")

    transitions = Counter(
        f"{d['first']['id']} -> {d['second']['id']}"
        for d in data.values()
    )

    for transition, count in transitions.most_common():

        out.write(
            f"{count:>4}  {transition}\n"
        )

    # ========================================================
    # 8. BEST-CONFLICT TRANSITIONS
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("8. BEST-CONFLICT TRANSITIONS\n")
    out.write("=" * 120 + "\n")

    conflict_transitions = Counter(
        f"{d['first']['id']} -> {d['second']['id']}"
        for d in data.values()
        if d["best_diff"] > 0
    )

    for transition, count in conflict_transitions.most_common():

        out.write(
            f"{count:>4}  {transition}\n"
        )

    # ========================================================
    # 9. TOP LOW MARGIN CASES
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("9. TOP 50 LOWEST FINAL MARGINS\n")
    out.write("=" * 120 + "\n")

    lowest = sorted(
        data.items(),
        key=lambda x: x[1]["margin"]
    )

    for image, d in lowest[:50]:

        a = d["first"]
        b = d["second"]

        out.write(
            f"{d['margin']:.6f} | "
            f"{a['id']} / {b['id']} | "
            f"BEST_DIFF={d['best_diff']:+.6f} | "
            f"{image}\n"
        )

    # ========================================================
    # 10. STRONGEST CASES WHERE BEST DISAGREES
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("10. STRONGEST BEST DISAGREEMENTS\n")
    out.write("=" * 120 + "\n")

    strong = sorted(
        [
            (image, d)
            for image, d in data.items()
            if d["best_diff"] >= 0.020
        ],
        key=lambda x: x[1]["best_diff"],
        reverse=True
    )

    for image, d in strong:

        a = d["first"]
        b = d["second"]

        out.write(
            f"{image}\n"
            f"  CURRENT = {a['id']}\n"
            f"  SECOND  = {b['id']}\n"
            f"  MARGIN  = {d['margin']:.6f}\n"
            f"  BEST    = {d['best_diff']:+.6f}\n"
            f"  CLASS   = {d['margin_class']} / "
            f"{d['conflict_class']}\n\n"
        )

    # ========================================================
    # END
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("END\n")
    out.write("=" * 120 + "\n")

print()
print("=" * 120)
print("DONE")
print("=" * 120)
print(f"CSV    : {CSV_OUT}")
print(f"REPORT : {REPORT}")
PY
```

Запускаем:

```bash
uv run python /tmp/analyze_all_262.py
```

Потом сразу покажи мне:

```bash
cat output/benchmark_components/full_analysis_262/all_262_analysis.txt
```

Если отчёт большой — достаточно сначала:

```bash
grep -A20 "2. MARGIN CLASSES" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt

grep -A20 "3. BEST CONFLICT DISTRIBUTION" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt

grep -A30 "4. BEST CONFLICT + LOW FINAL MARGIN" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt

grep -A60 "8. BEST-CONFLICT TRANSITIONS" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt
```

И отдельно самое важное:

```bash
grep -A55 "5. TOP 50 BEST CONFLICTS" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt
```

По этому уже можно будет решить, **нужен ли вообще `BEST` в финальном распознавании и при каком пороге его безопасно подключать**.

---

### 👤 **User** — 2026-08-15 12:42:02

FULL ANALYSIS — ALL 262 IMAGES
========================================================================================================================
Images: 262

========================================================================================================================
1. FINAL MARGIN DISTRIBUTION
========================================================================================================================
< 0.001       257 / 262 ( 98.09%)
< 0.002       262 / 262 (100.00%)
< 0.003       262 / 262 (100.00%)
< 0.005       262 / 262 (100.00%)
< 0.010       262 / 262 (100.00%)
< 0.020       262 / 262 (100.00%)
< 0.030       262 / 262 (100.00%)

========================================================================================================================
2. MARGIN CLASSES
========================================================================================================================
VERY_BORDERLINE       262 (100.00%)
BORDERLINE              0 (  0.00%)
LOW_MARGIN              0 (  0.00%)
MEDIUM_MARGIN           0 (  0.00%)
SAFE                    0 (  0.00%)

========================================================================================================================
3. BEST CONFLICT DISTRIBUTION
========================================================================================================================
STRONG_BEST_CONFLICT         1 (  0.38%)
BEST_CONFLICT                0 (  0.00%)
WEAK_BEST_CONFLICT           0 (  0.00%)
NO_BEST_CONFLICT           261 ( 99.62%)

========================================================================================================================
4. BEST CONFLICT + LOW FINAL MARGIN
========================================================================================================================
MARGIN < 0.003 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.010 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.020 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.050:   1 (0.38%)
MARGIN < 0.010 AND BEST_DIFF >= 0.050:   1 (0.38%)

========================================================================================================================
5. TOP 50 BEST CONFLICTS
========================================================================================================================
BEST_DIFF=+0.057438 FINAL_MARGIN=0.000000 | 87_v33 / 84_v33 | Ленина 125-127 А (14).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000186 | 78_v33 / 78_v33 | 00 (1).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000201 | 78_v33 / 78_v33 | 00 (10).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000109 | 78_v33 / 78_v33 | 00 (11).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000013 | 78_v33 / 78_v33 | 00 (12).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000336 | 78_v33 / 78_v33 | 00 (2).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000043 | 78_v33 / 78_v33 | 00 (3).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000037 | 78_v33 / 78_v33 | 00 (4).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000159 | 78_v33 / 78_v33 | 00 (5).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000295 | 78_v33 / 78_v33 | 00 (6).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000096 | 78_v33 / 78_v33 | 00 (7).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000425 | 79_v33 / 79_v33 | 00 (8).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000377 | 78_v33 / 78_v33 | 00 (9).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000009 | 78_v33 / 78_v33 | 001.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000067 | 78_v33 / 78_v33 | 002.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000075 | 78_v33 / 78_v33 | 003.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000039 | 78_v33 / 78_v33 | 004.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000141 | 78_v33 / 78_v33 | 005.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000653 | 80_v33 / 80_v33 | 006.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000636 | 80_v33 / 80_v33 | 007.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000248 | 83_v33 / 83_v33 | 008.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000197 | 92_v33 / 92_v33 | 009.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000410 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (1).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000386 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (10).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000663 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (11).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000340 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (12).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000833 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (35).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000762 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (36).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000507 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (37).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000242 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (38).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000384 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (39).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000197 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (6).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000546 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (7).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000405 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (8).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000472 | 81_v33 / 81_v33 | 1 Конной Армии 32 А (9).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000322 | 81_v33 / 81_v33 | 1 Конной Армии А (16).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000270 | 81_v33 / 81_v33 | 1 Конной Армии А (17).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000394 | 81_v33 / 81_v33 | 1 Конной Армии А (18).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000481 | 95_v33 / 95_v33 | Вавилова 52 А (1).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000058 | 95_v33 / 95_v33 | Вавилова 52 А (10).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000401 | 95_v33 / 95_v33 | Вавилова 52 А (11).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000181 | 95_v33 / 95_v33 | Вавилова 52 А (12).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000924 | 95_v33 / 95_v33 | Вавилова 52 А (14).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000288 | 95_v33 / 95_v33 | Вавилова 52 А (16).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000417 | 95_v33 / 95_v33 | Вавилова 52 А (17).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000491 | 95_v33 / 95_v33 | Вавилова 52 А (18).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000634 | 95_v33 / 95_v33 | Вавилова 52 А (20).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000644 | 95_v33 / 95_v33 | Вавилова 52 А (21).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000274 | 95_v33 / 95_v33 | Вавилова 52 А (23).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000625 | 95_v33 / 95_v33 | Вавилова 52 А (25).JPG

========================================================================================================================
6. ALL POSITIVE BEST CONFLICTS
========================================================================================================================
Total: 1 / 262 (0.38%)

Ленина 125-127 А (14).JPG
  FINAL : 87_v33 = 0.888650  84_v33 = 0.888650
  MARGIN: 0.000000
  BEST  : 87_v33 = 0.883096  84_v33 = 0.940534
  DIFF  : +0.057438
  CLASS : VERY_BORDERLINE / STRONG_BEST_CONFLICT

========================================================================================================================
7. FIRST -> SECOND TRANSITION MATRIX
========================================================================================================================
  24  94_v33 -> 94_v33
  20  78_v33 -> 78_v33
  20  89_v33 -> 89_v33
  19  87_v33 -> 87_v33
  18  83_v33 -> 83_v33
  18  92_v33 -> 92_v33
  17  95_v33 -> 95_v33
  17  85_v33 -> 85_v33
  16  81_v33 -> 81_v33
  16  88_v33 -> 88_v33
  15  86_v33 -> 86_v33
  13  91_v33 -> 91_v33
  12  93_v33 -> 93_v33
   9  82_v33 -> 82_v33
   8  79_v33 -> 79_v33
   8  80_v33 -> 80_v33
   8  84_v33 -> 84_v33
   3  90_v33 -> 90_v33
   1  87_v33 -> 84_v33

========================================================================================================================
8. BEST-CONFLICT TRANSITIONS
========================================================================================================================
   1  87_v33 -> 84_v33

========================================================================================================================
9. TOP 50 LOWEST FINAL MARGINS
========================================================================================================================
-0.003341 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева 8 РИИЖТ (25).JPG
-0.002211 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (1).JPG
-0.002088 | 88_v33 / 88_v33 | BEST_DIFF=+0.000000 | Малиновского 9 А (23).JPG
-0.001433 | 91_v33 / 91_v33 | BEST_DIFF=+0.000000 | Нагибина Рубиновый А (52).JPG
-0.001223 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (1).JPG
-0.001141 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (15).JPG
-0.001135 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (12).JPG
-0.001038 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (59).JPG
-0.000991 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (16).JPG
-0.000965 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (11).JPG
-0.000952 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (63).JPG
-0.000946 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (13).JPG
-0.000924 | 95_v33 / 95_v33 | BEST_DIFF=+0.000000 | Вавилова 52 А (14).JPG
-0.000923 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (61).JPG
-0.000920 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (9).JPG
-0.000908 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (17).JPG
-0.000839 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (60).JPG
-0.000837 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева 8 РИИЖТ (21).JPG
-0.000691 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (21).JPG
-0.000653 | 80_v33 / 80_v33 | BEST_DIFF=+0.000000 | 006.JPG
-0.000636 | 80_v33 / 80_v33 | BEST_DIFF=+0.000000 | 007.JPG
-0.000563 | 88_v33 / 88_v33 | BEST_DIFF=+0.000000 | Малиновского 9 А (9).JPG
-0.000433 | 89_v33 / 89_v33 | BEST_DIFF=+0.000000 | Ленина Ашхабадский А (7).JPG
-0.000414 | 89_v33 / 89_v33 | BEST_DIFF=+0.000000 | Малиновского 25 к Доватора А (32).JPG
-0.000410 | 86_v33 / 86_v33 | BEST_DIFF=+0.000000 | менжин (3).JPG
-0.000394 | 81_v33 / 81_v33 | BEST_DIFF=+0.000000 | 1 Конной Армии А (18).JPG
-0.000322 | 81_v33 / 81_v33 | BEST_DIFF=+0.000000 | 1 Конной Армии А (16).JPG
-0.000301 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (38).JPG
-0.000295 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (6).JPG
-0.000287 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (8).JPG
-0.000280 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  A (33).JPG
-0.000270 | 81_v33 / 81_v33 | BEST_DIFF=+0.000000 | 1 Конной Армии А (17).JPG
-0.000267 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (12).JPG
-0.000228 | 91_v33 / 91_v33 | BEST_DIFF=+0.000000 | Нагибина Рубиновый А (8).JPG
-0.000223 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (34).JPG
-0.000221 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (6).JPG
-0.000218 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (13).JPG
-0.000206 | 92_v33 / 92_v33 | BEST_DIFF=+0.000000 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (18).JPG
-0.000197 | 88_v33 / 88_v33 | BEST_DIFF=+0.000000 | Малиновского 9 А (8).JPG
-0.000186 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (1).JPG
-0.000181 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева 8 РИИЖТ (1).JPG
-0.000171 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (33).JPG
-0.000156 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (32).JPG
-0.000147 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  B (22).JPG
-0.000141 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 005.JPG
-0.000141 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | Космонавтов 13 Комарова А (9).JPG
-0.000133 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (31).JPG
-0.000109 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (11).JPG
-0.000098 | 89_v33 / 89_v33 | BEST_DIFF=+0.000000 | Малиновского 25 к Доватора (17).JPG
-0.000096 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (7).JPG

========================================================================================================================
10. STRONGEST BEST DISAGREEMENTS
========================================================================================================================
Ленина 125-127 А (14).JPG
  CURRENT = 87_v33
  SECOND  = 84_v33
  MARGIN  = 0.000000
  BEST    = +0.057438
  CLASS   = VERY_BORDERLINE / STRONG_BEST_CONFLICT

========================================================================================================================
END
========================================================================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -A20 "2. MARGIN CLASSES" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt

grep -A20 "3. BEST CONFLICT DISTRIBUTION" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt

grep -A30 "4. BEST CONFLICT + LOW FINAL MARGIN" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt

grep -A60 "8. BEST-CONFLICT TRANSITIONS" \
output/benchmark_components/full_analysis_262/all_262_analysis.txt
2. MARGIN CLASSES
========================================================================================================================
VERY_BORDERLINE       262 (100.00%)
BORDERLINE              0 (  0.00%)
LOW_MARGIN              0 (  0.00%)
MEDIUM_MARGIN           0 (  0.00%)
SAFE                    0 (  0.00%)

========================================================================================================================
3. BEST CONFLICT DISTRIBUTION
========================================================================================================================
STRONG_BEST_CONFLICT         1 (  0.38%)
BEST_CONFLICT                0 (  0.00%)
WEAK_BEST_CONFLICT           0 (  0.00%)
NO_BEST_CONFLICT           261 ( 99.62%)

========================================================================================================================
4. BEST CONFLICT + LOW FINAL MARGIN
========================================================================================================================
MARGIN < 0.003 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.020:   1 (0.38%)
3. BEST CONFLICT DISTRIBUTION
========================================================================================================================
STRONG_BEST_CONFLICT         1 (  0.38%)
BEST_CONFLICT                0 (  0.00%)
WEAK_BEST_CONFLICT           0 (  0.00%)
NO_BEST_CONFLICT           261 ( 99.62%)

========================================================================================================================
4. BEST CONFLICT + LOW FINAL MARGIN
========================================================================================================================
MARGIN < 0.003 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.010 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.020 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.050:   1 (0.38%)
MARGIN < 0.010 AND BEST_DIFF >= 0.050:   1 (0.38%)

========================================================================================================================
5. TOP 50 BEST CONFLICTS
========================================================================================================================
BEST_DIFF=+0.057438 FINAL_MARGIN=0.000000 | 87_v33 / 84_v33 | Ленина 125-127 А (14).JPG
4. BEST CONFLICT + LOW FINAL MARGIN
========================================================================================================================
MARGIN < 0.003 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.010 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.020 AND BEST_DIFF >= 0.020:   1 (0.38%)
MARGIN < 0.005 AND BEST_DIFF >= 0.050:   1 (0.38%)
MARGIN < 0.010 AND BEST_DIFF >= 0.050:   1 (0.38%)

========================================================================================================================
5. TOP 50 BEST CONFLICTS
========================================================================================================================
BEST_DIFF=+0.057438 FINAL_MARGIN=0.000000 | 87_v33 / 84_v33 | Ленина 125-127 А (14).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000186 | 78_v33 / 78_v33 | 00 (1).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000201 | 78_v33 / 78_v33 | 00 (10).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000109 | 78_v33 / 78_v33 | 00 (11).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000013 | 78_v33 / 78_v33 | 00 (12).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000336 | 78_v33 / 78_v33 | 00 (2).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000043 | 78_v33 / 78_v33 | 00 (3).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000037 | 78_v33 / 78_v33 | 00 (4).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000159 | 78_v33 / 78_v33 | 00 (5).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000295 | 78_v33 / 78_v33 | 00 (6).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000096 | 78_v33 / 78_v33 | 00 (7).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000425 | 79_v33 / 79_v33 | 00 (8).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000377 | 78_v33 / 78_v33 | 00 (9).JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000009 | 78_v33 / 78_v33 | 001.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000067 | 78_v33 / 78_v33 | 002.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000075 | 78_v33 / 78_v33 | 003.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=0.000039 | 78_v33 / 78_v33 | 004.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000141 | 78_v33 / 78_v33 | 005.JPG
BEST_DIFF=+0.000000 FINAL_MARGIN=-0.000653 | 80_v33 / 80_v33 | 006.JPG
8. BEST-CONFLICT TRANSITIONS
========================================================================================================================
   1  87_v33 -> 84_v33

========================================================================================================================
9. TOP 50 LOWEST FINAL MARGINS
========================================================================================================================
-0.003341 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева 8 РИИЖТ (25).JPG
-0.002211 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (1).JPG
-0.002088 | 88_v33 / 88_v33 | BEST_DIFF=+0.000000 | Малиновского 9 А (23).JPG
-0.001433 | 91_v33 / 91_v33 | BEST_DIFF=+0.000000 | Нагибина Рубиновый А (52).JPG
-0.001223 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (1).JPG
-0.001141 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (15).JPG
-0.001135 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (12).JPG
-0.001038 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (59).JPG
-0.000991 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (16).JPG
-0.000965 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (11).JPG
-0.000952 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (63).JPG
-0.000946 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (13).JPG
-0.000924 | 95_v33 / 95_v33 | BEST_DIFF=+0.000000 | Вавилова 52 А (14).JPG
-0.000923 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (61).JPG
-0.000920 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (9).JPG
-0.000908 | 84_v33 / 84_v33 | BEST_DIFF=+0.000000 | Ленина 125-127 А (17).JPG
-0.000839 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (60).JPG
-0.000837 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева 8 РИИЖТ (21).JPG
-0.000691 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (21).JPG
-0.000653 | 80_v33 / 80_v33 | BEST_DIFF=+0.000000 | 006.JPG
-0.000636 | 80_v33 / 80_v33 | BEST_DIFF=+0.000000 | 007.JPG
-0.000563 | 88_v33 / 88_v33 | BEST_DIFF=+0.000000 | Малиновского 9 А (9).JPG
-0.000433 | 89_v33 / 89_v33 | BEST_DIFF=+0.000000 | Ленина Ашхабадский А (7).JPG
-0.000414 | 89_v33 / 89_v33 | BEST_DIFF=+0.000000 | Малиновского 25 к Доватора А (32).JPG
-0.000410 | 86_v33 / 86_v33 | BEST_DIFF=+0.000000 | менжин (3).JPG
-0.000394 | 81_v33 / 81_v33 | BEST_DIFF=+0.000000 | 1 Конной Армии А (18).JPG
-0.000322 | 81_v33 / 81_v33 | BEST_DIFF=+0.000000 | 1 Конной Армии А (16).JPG
-0.000301 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (38).JPG
-0.000295 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (6).JPG
-0.000287 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (8).JPG
-0.000280 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  A (33).JPG
-0.000270 | 81_v33 / 81_v33 | BEST_DIFF=+0.000000 | 1 Конной Армии А (17).JPG
-0.000267 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (12).JPG
-0.000228 | 91_v33 / 91_v33 | BEST_DIFF=+0.000000 | Нагибина Рубиновый А (8).JPG
-0.000223 | 82_v33 / 82_v33 | BEST_DIFF=+0.000000 | Добровольского 17 А (34).JPG
-0.000221 | 94_v33 / 94_v33 | BEST_DIFF=+0.000000 | Вавилова Радиаторный А (6).JPG
-0.000218 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (13).JPG
-0.000206 | 92_v33 / 92_v33 | BEST_DIFF=+0.000000 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (18).JPG
-0.000197 | 88_v33 / 88_v33 | BEST_DIFF=+0.000000 | Малиновского 9 А (8).JPG
-0.000186 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (1).JPG
-0.000181 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева 8 РИИЖТ (1).JPG
-0.000171 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (33).JPG
-0.000156 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (32).JPG
-0.000147 | 87_v33 / 87_v33 | BEST_DIFF=+0.000000 | Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  B (22).JPG
-0.000141 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 005.JPG
-0.000141 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | Космонавтов 13 Комарова А (9).JPG
-0.000133 | 83_v33 / 83_v33 | BEST_DIFF=+0.000000 | Нагибина 24 А (31).JPG
-0.000109 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (11).JPG
-0.000098 | 89_v33 / 89_v33 | BEST_DIFF=+0.000000 | Малиновского 25 к Доватора (17).JPG
-0.000096 | 78_v33 / 78_v33 | BEST_DIFF=+0.000000 | 00 (7).JPG

========================================================================================================================
10. STRONGEST BEST DISAGREEMENTS
========================================================================================================================

---

### 🤖 **Assistant** — 2026-08-15 12:42:05

Да. Теперь картина понятна, и **это уже не проблема алгоритма — это проблема диагностического скрипта**.

Главный признак:

```text
24  94_v33 -> 94_v33
20  78_v33 -> 78_v33
19  87_v33 -> 87_v33
...
```

Это невозможно трактовать как «первый кандидат → второй кандидат». Скрипт сейчас берет **две строки одного и того же адреса из разных `weight_set` либо повторяет один и тот же ID**, поэтому `FINAL_MARGIN` почти всегда около нуля.

При этом единственный реальный конфликт мы уже нашли:

```text
Ленина 125-127 А (14).JPG

CURRENT = 87_v33
SECOND  = 84_v33

FINAL = 0.888650 / 0.888650
BEST  = 0.883096 / 0.940534
BEST_DIFF = +0.057438
```

И раньше мы видели аналогичные реальные случаи:

```text
Ленина 125-127 А (8)   87 -> 84   BEST_DIFF +0.068202
Ленина 125-127 А (10)  87 -> 84   BEST_DIFF +0.053755
```

То есть **84 действительно представляет серьезного конкурента для 87**, но текущий `full_analysis_262` смешивает это с неправильным расчетом margin.

### Что делаем сейчас

Нужно не чинить этот отчет кусками, а сделать диагностику правильно:

**Для каждой фотографии:**

1. Берем только `weight_set=A_CURRENT`.
2. Сортируем кандидатов по `final`.
3. `rank=1` → CURRENT.
4. `rank=2` → SECOND.
5. Считаем:

```text
FINAL_MARGIN = final_1 - final_2
BEST_DIFF     = BEST_2 - BEST_1
```

6. Проверяем **только разные ID**:
   ```text
   first_id != second_id
   ```
7. Отдельно считаем:
   - обычные уверенные случаи;
   - малый FINAL_MARGIN;
   - когда `BEST_SECOND` существенно выше `BEST_FIRST`;
   - реальные переходы `87 -> 84`, `84 -> 87` и т.д.

И самое важное: **не надо считать одинаковый `87 -> 87` конфликтом вообще**.

---

### Сейчас дай команду

Сначала покажи начало скрипта — там как раз находится ошибка формирования `data`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,90p' /tmp/test_margin_best.py
```

И ещё:

```bash
grep -n "weight_set\|rank\|items\|data\[" /tmp/test_margin_best.py
```

Пришли вывод.

После этого я дам **один цельный исправленный скрипт**, а не будем дальше латать `KeyError`. Он сразу построит корректный анализ всех 262 фотографий и покажет нам реальное количество случаев типа:

```text
87 -> 84
84 -> 87
89 -> 92
...
```

И тогда уже решим, **нужно ли вообще вводить правило второго кандидата**, или достаточно оставить v33 как есть и использовать второй кандидат только как триггер для OCR.

---

### 👤 **User** — 2026-08-15 12:43:00

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,90p' /tmp/test_margin_best.py
from pathlib import Path
import csv
from collections import Counter, defaultdict

# ============================================================
# CONFIG
# ============================================================

INPUT = Path("output/benchmark_components/components.csv")

OUTPUT_DIR = Path("output/benchmark_components/full_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = OUTPUT_DIR / "margin_best.txt"
CSV_OUT = OUTPUT_DIR / "margin_best.csv"

BEST_WEIGHTS = [
    0.00,
    0.02,
    0.05,
    0.10,
    0.15,
    0.20,
]

MARGINS = [
    0.001,
    0.002,
    0.003,
    0.005,
    0.010,
    0.015,
    0.020,
    0.030,
]

BEST_DIFFS = [
    0.005,
    0.010,
    0.020,
    0.030,
    0.040,
    0.050,
    0.060,
]

# ============================================================
# LOAD CSV
# ============================================================

with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    rows = list(csv.DictReader(f))

print(f"Loaded rows: {len(rows)}")

# ============================================================
# GROUP BY IMAGE
# ============================================================

groups = defaultdict(list)

for row in rows:
    groups[row["image"]].append(row)

print(f"Images: {len(groups)}")

# ============================================================
# CONVERT
# ============================================================

def num(row, key):
    return float(row[key])

# ============================================================
# BUILD DATA
# ============================================================

data = {}

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "weight_set\|rank\|items\|data\[" /tmp/test_margin_best.py
91:for image, items in groups.items():
95:        r for r in items
96:        if r["weight_set"] == "A_CURRENT"
116:    data[image] = {
153:    for image, d in data.items():
221:        for image, d in data.items():
278:    for bw, changes in all_changes.items():
288:            d = data[image]
360:        data.items(),
387:        data.items(),
414:        for image, d in data.items()
450:    for image, d in data.items():
463:    for pair, entries in pairs.items():
512:    for image, d in data.items():
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 12:43:01

Да, теперь видно, где проблема. Давай **не латать старый скрипт**, а сразу заменить его на чистую версию.

Причина: в `components.csv` для одного изображения есть строки разных `weight_set`, а старый анализ местами смешивал структуру данных. Нам нужен только `A_CURRENT`, и внутри него строго `rank=1` и `rank=2`.

Сделаем новый диагностический скрипт.

### 1. Создай его

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/analyze_v33_correct.py <<'PY'
from pathlib import Path
import csv
from collections import defaultdict, Counter

INPUT = Path("output/benchmark_components/components.csv")
OUT_DIR = Path("output/benchmark_components/correct_analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = OUT_DIR / "analysis.txt"
CSV_OUT = OUT_DIR / "analysis.csv"

# ============================================================
# LOAD
# ============================================================

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded rows: {len(rows)}")

# ============================================================
# ONLY A_CURRENT
# ============================================================

current = [
    r for r in rows
    if r["weight_set"] == "A_CURRENT"
]

print(f"A_CURRENT rows: {len(current)}")

# ============================================================
# GROUP
# ============================================================

groups = defaultdict(list)

for r in current:
    groups[r["image"]].append(r)

print(f"Images: {len(groups)}")

# ============================================================
# BUILD CORRECT DATA
# ============================================================

data = {}

for image, items in groups.items():

    items = sorted(
        items,
        key=lambda r: int(r["rank"])
    )

    if len(items) < 2:
        continue

    first = items[0]
    second = items[1]

    first_id = first["id"]
    second_id = second["id"]

    # Ignore duplicate same-ID candidates.
    if first_id == second_id:
        continue

    final1 = float(first["final"])
    final2 = float(second["final"])

    best1 = float(first["BEST"])
    best2 = float(second["BEST"])

    data[image] = {
        "first": first,
        "second": second,

        "first_id": first_id,
        "second_id": second_id,

        "final1": final1,
        "final2": final2,

        "best1": best1,
        "best2": best2,

        "margin": final1 - final2,
        "best_diff": best2 - best1,
    }

print(f"Usable different-ID images: {len(data)}")

# ============================================================
# REPORT
# ============================================================

with REPORT.open("w", encoding="utf-8") as out:

    out.write("=" * 120 + "\n")
    out.write("CORRECT V33 ANALYSIS — A_CURRENT ONLY\n")
    out.write("=" * 120 + "\n\n")

    out.write(f"CSV rows: {len(rows)}\n")
    out.write(f"A_CURRENT rows: {len(current)}\n")
    out.write(f"Images: {len(groups)}\n")
    out.write(f"Different-ID comparisons: {len(data)}\n\n")

# ========================================================
    # REAL TRANSITIONS
    # ========================================================

    pairs = Counter(
        f"{d['first_id']} -> {d['second_id']}"
        for d in data.values()
    )

    out.write("=" * 120 + "\n")
    out.write("FIRST -> SECOND TRANSITIONS\n")
    out.write("=" * 120 + "\n")

    for pair, count in pairs.most_common():
        out.write(f"{count:4d}  {pair}\n")

# ========================================================
    # LOW MARGIN
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("LOW FINAL MARGIN\n")
    out.write("=" * 120 + "\n")

    thresholds = [
        0.001,
        0.002,
        0.003,
        0.005,
        0.010,
        0.015,
        0.020,
        0.030,
    ]

    for t in thresholds:

        n = sum(
            d["margin"] < t
            for d in data.values()
        )

        out.write(
            f"MARGIN < {t:.3f}: "
            f"{n:3d} / {len(data)} "
            f"({100*n/len(data):6.2f}%)\n"
        )

# ========================================================
    # BEST CONFLICTS
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("BEST CONFLICTS\n")
    out.write("=" * 120 + "\n")

    conflicts = [
        (image, d)
        for image, d in data.items()
        if d["best_diff"] > 0
    ]

    conflicts.sort(
        key=lambda x: x[1]["best_diff"],
        reverse=True
    )

    out.write(
        f"Positive BEST conflicts: "
        f"{len(conflicts)} / {len(data)}\n\n"
    )

    for image, d in conflicts[:50]:

        out.write(
            f"BEST_DIFF={d['best_diff']:+.6f} "
            f"FINAL_MARGIN={d['margin']:+.6f} | "
            f"{d['first_id']} / {d['second_id']} | "
            f"{image}\n"
        )

# ========================================================
    # STRONG CONFLICTS
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("STRONG BEST CONFLICTS\n")
    out.write("=" * 120 + "\n")

    strong = [
        (image, d)
        for image, d in data.items()
        if d["margin"] < 0.010
        and d["best_diff"] >= 0.020
    ]

    strong.sort(
        key=lambda x: x[1]["best_diff"],
        reverse=True
    )

    out.write(
        f"Count: {len(strong)}\n\n"
    )

    for image, d in strong:

        out.write(
            f"{image}\n"
            f"  FIRST  = {d['first_id']}\n"
            f"  SECOND = {d['second_id']}\n"
            f"  FINAL  = "
            f"{d['final1']:.6f} / {d['final2']:.6f}\n"
            f"  MARGIN = {d['margin']:+.6f}\n"
            f"  BEST   = "
            f"{d['best1']:.6f} / {d['best2']:.6f}\n"
            f"  DIFF   = {d['best_diff']:+.6f}\n\n"
        )

# ========================================================
    # SPECIAL 84 / 87
    # ========================================================

    out.write("=" * 120 + "\n")
    out.write("SPECIAL: 84_V33 VS 87_V33\n")
    out.write("=" * 120 + "\n")

    special = []

    for image, d in data.items():

        ids = {d["first_id"], d["second_id"]}

        if ids == {"84_v33", "87_v33"}:
            special.append((image, d))

    special.sort()

    for image, d in special:

        out.write(
            f"{image}\n"
            f"  FIRST={d['first_id']}\n"
            f"  SECOND={d['second_id']}\n"
            f"  FINAL_MARGIN={d['margin']:+.6f}\n"
            f"  BEST_DIFF={d['best_diff']:+.6f}\n"
            f"  BEST={d['best1']:.6f} / {d['best2']:.6f}\n\n"
        )

# ========================================================
    # TOP LOWEST MARGINS
    # ========================================================

    out.write("=" * 120 + "\n")
    out.write("TOP 50 LOWEST FINAL MARGINS\n")
    out.write("=" * 120 + "\n")

    lowest = sorted(
        data.items(),
        key=lambda x: x[1]["margin"]
    )

    for image, d in lowest[:50]:

        out.write(
            f"{d['margin']:+.6f} | "
            f"{d['first_id']} / {d['second_id']} | "
            f"BEST_DIFF={d['best_diff']:+.6f} | "
            f"{image}\n"
        )

# ========================================================
    # RECOMMENDED OCR TRIGGERS
    # ========================================================

    out.write("\n")
    out.write("=" * 120 + "\n")
    out.write("RECOMMENDED OCR TRIGGERS\n")
    out.write("=" * 120 + "\n")

    triggers = [
        (image, d)
        for image, d in data.items()
        if d["margin"] < 0.010
        and d["best_diff"] >= 0.020
    ]

    triggers.sort(
        key=lambda x: (
            -x[1]["best_diff"],
            x[1]["margin"]
        )
    )

    out.write(
        f"Potential OCR cases: {len(triggers)}\n\n"
    )

    for image, d in triggers:

        out.write(
            f"{image}\n"
            f"  CURRENT={d['first_id']}\n"
            f"  CANDIDATE={d['second_id']}\n"
            f"  MARGIN={d['margin']:+.6f}\n"
            f"  BEST_DIFF={d['best_diff']:+.6f}\n\n"
        )

# ============================================================
# CSV
# ============================================================

with CSV_OUT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "image",
        "first_id",
        "second_id",
        "final1",
        "final2",
        "margin",
        "best1",
        "best2",
        "best_diff",
        "first_best_image",
        "second_best_image",
    ])

    for image, d in sorted(
        data.items(),
        key=lambda x: x[1]["margin"]
    ):

        writer.writerow([
            image,
            d["first_id"],
            d["second_id"],
            f"{d['final1']:.6f}",
            f"{d['final2']:.6f}",
            f"{d['margin']:.6f}",
            f"{d['best1']:.6f}",
            f"{d['best2']:.6f}",
            f"{d['best_diff']:.6f}",
            d["first"].get("best_image", ""),
            d["second"].get("best_image", ""),
        ])

print()
print("=" * 80)
print("DONE")
print("=" * 80)
print(f"Report: {REPORT}")
print(f"CSV   : {CSV_OUT}")
print()
PY
```

### 2. Запусти

```bash
uv run python /tmp/analyze_v33_correct.py
```

### 3. Сразу покажи самое важное

```bash
cat output/benchmark_components/correct_analysis/analysis.txt
```

---

И вот здесь будет принципиальная проверка.

Мы ожидаем увидеть что-то вроде:

```text
FIRST -> SECOND TRANSITIONS

...
3   87_v33 -> 84_v33
...
```

а **не**:

```text
87_v33 -> 87_v33
94_v33 -> 94_v33
84_v33 -> 84_v33
```

Потому что одинаковые ID теперь вообще исключены из сравнения.

### Что особенно важно

Если после исправления окажется, что:

```text
87 -> 84
```

встречается, например, только в 3–5 фотографиях из 262, причём именно на серии:

```text
Ленина 125-127 А
```

то это очень хороший результат.

Тогда я бы **не менял основной алгоритм v33**.

Мы сделаем второй кандидат не заменой первого, а **сигналом неопределённости**:

```text
DINO v33
   │
   ├── уверенный первый кандидат ──> присвоить адрес
   │
   └── близкий второй кандидат
          │
          └── BEST второго существенно лучше
                    │
                    └── OCR таблички
                              │
                              └── уточнить адрес
```

То есть DINO остаётся основным распознавателем, а OCR включается только на действительно спорных кадрах. Это как раз соответствует тому, что мы обсуждали раньше: **OCR не нужен на всех 200–300 фотографиях в день, он нужен как дорогой арбитр для небольшого числа сложных случаев.**

---

### 👤 **User** — 2026-08-15 12:44:00

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cat output/benchmark_components/correct_analysis/analysis.txt
========================================================================================================================
CORRECT V33 ANALYSIS — A_CURRENT ONLY
========================================================================================================================

CSV rows: 7860
A_CURRENT rows: 1310
Images: 262
Different-ID comparisons: 262

========================================================================================================================
FIRST -> SECOND TRANSITIONS
========================================================================================================================
  13  95_v33 -> 94_v33
  12  81_v33 -> 84_v33
  12  94_v33 -> 91_v33
   8  84_v33 -> 87_v33
   8  89_v33 -> 92_v33
   8  88_v33 -> 92_v33
   8  83_v33 -> 91_v33
   7  78_v33 -> 91_v33
   7  85_v33 -> 91_v33
   7  93_v33 -> 92_v33
   7  87_v33 -> 79_v33
   6  92_v33 -> 83_v33
   6  94_v33 -> 95_v33
   6  82_v33 -> 86_v33
   6  79_v33 -> 87_v33
   6  91_v33 -> 93_v33
   5  85_v33 -> 93_v33
   4  78_v33 -> 92_v33
   4  80_v33 -> 82_v33
   4  92_v33 -> 93_v33
   4  85_v33 -> 94_v33
   4  87_v33 -> 85_v33
   4  87_v33 -> 92_v33
   4  86_v33 -> 82_v33
   3  78_v33 -> 95_v33
   3  78_v33 -> 83_v33
   3  78_v33 -> 93_v33
   3  83_v33 -> 92_v33
   3  95_v33 -> 78_v33
   3  88_v33 -> 89_v33
   3  82_v33 -> 80_v33
   3  80_v33 -> 79_v33
   3  87_v33 -> 84_v33
   3  89_v33 -> 93_v33
   3  90_v33 -> 89_v33
   3  83_v33 -> 87_v33
   3  83_v33 -> 93_v33
   3  91_v33 -> 92_v33
   3  93_v33 -> 91_v33
   3  86_v33 -> 92_v33
   2  79_v33 -> 92_v33
   2  81_v33 -> 93_v33
   2  94_v33 -> 85_v33
   2  94_v33 -> 92_v33
   2  86_v33 -> 89_v33
   2  92_v33 -> 91_v33
   2  89_v33 -> 85_v33
   2  89_v33 -> 94_v33
   2  89_v33 -> 80_v33
   2  89_v33 -> 90_v33
   2  88_v33 -> 87_v33
   2  91_v33 -> 94_v33
   2  92_v33 -> 87_v33
   2  92_v33 -> 86_v33
   2  92_v33 -> 89_v33
   2  86_v33 -> 94_v33
   2  86_v33 -> 78_v33
   2  86_v33 -> 95_v33
   1  81_v33 -> 92_v33
   1  81_v33 -> 79_v33
   1  94_v33 -> 93_v33
   1  80_v33 -> 91_v33
   1  85_v33 -> 92_v33
   1  89_v33 -> 86_v33
   1  94_v33 -> 89_v33
   1  88_v33 -> 80_v33
   1  88_v33 -> 82_v33
   1  88_v33 -> 86_v33
   1  83_v33 -> 81_v33
   1  91_v33 -> 85_v33
   1  91_v33 -> 83_v33
   1  93_v33 -> 83_v33
   1  93_v33 -> 95_v33
   1  95_v33 -> 92_v33
   1  87_v33 -> 81_v33
   1  87_v33 -> 83_v33

========================================================================================================================
LOW FINAL MARGIN
========================================================================================================================
MARGIN < 0.001:   0 / 262 (  0.00%)
MARGIN < 0.002:   3 / 262 (  1.15%)
MARGIN < 0.003:   4 / 262 (  1.53%)
MARGIN < 0.005:   7 / 262 (  2.67%)
MARGIN < 0.010:  14 / 262 (  5.34%)
MARGIN < 0.015:  23 / 262 (  8.78%)
MARGIN < 0.020:  32 / 262 ( 12.21%)
MARGIN < 0.030:  50 / 262 ( 19.08%)

========================================================================================================================
BEST CONFLICTS
========================================================================================================================
Positive BEST conflicts: 11 / 262

BEST_DIFF=+0.068202 FINAL_MARGIN=+0.005768 | 87_v33 / 84_v33 | Ленина 125-127 А (8).JPG
BEST_DIFF=+0.057438 FINAL_MARGIN=+0.001037 | 87_v33 / 84_v33 | Ленина 125-127 А (14).JPG
BEST_DIFF=+0.053755 FINAL_MARGIN=+0.001876 | 87_v33 / 84_v33 | Ленина 125-127 А (10).JPG
BEST_DIFF=+0.051273 FINAL_MARGIN=+0.017624 | 89_v33 / 92_v33 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (10).JPG
BEST_DIFF=+0.038996 FINAL_MARGIN=+0.012795 | 87_v33 / 92_v33 | Шеболдаева 8 РИИЖТ (25).JPG
BEST_DIFF=+0.022570 FINAL_MARGIN=+0.013838 | 95_v33 / 92_v33 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (20).jpg
BEST_DIFF=+0.012026 FINAL_MARGIN=+0.017470 | 91_v33 / 93_v33 | Нагибина Рубиновый А (52).JPG
BEST_DIFF=+0.011953 FINAL_MARGIN=+0.006481 | 86_v33 / 89_v33 | Вавилова ул. - Радиаторный пер.  A (63).JPG
BEST_DIFF=+0.008918 FINAL_MARGIN=+0.015792 | 89_v33 / 92_v33 | Стачки Зорге А (25).JPG
BEST_DIFF=+0.004149 FINAL_MARGIN=+0.003229 | 88_v33 / 89_v33 | Вавилова ул. - Радиаторный пер.  A (70).JPG
BEST_DIFF=+0.003729 FINAL_MARGIN=+0.001418 | 83_v33 / 92_v33 | 008.JPG

========================================================================================================================
STRONG BEST CONFLICTS
========================================================================================================================
Count: 3

Ленина 125-127 А (8).JPG
  FIRST  = 87_v33
  SECOND = 84_v33
  FINAL  = 0.887508 / 0.881740
  MARGIN = +0.005768
  BEST   = 0.882709 / 0.950911
  DIFF   = +0.068202

Ленина 125-127 А (14).JPG
  FIRST  = 87_v33
  SECOND = 84_v33
  FINAL  = 0.888650 / 0.887613
  MARGIN = +0.001037
  BEST   = 0.883096 / 0.940534
  DIFF   = +0.057438

Ленина 125-127 А (10).JPG
  FIRST  = 87_v33
  SECOND = 84_v33
  FINAL  = 0.896861 / 0.894985
  MARGIN = +0.001876
  BEST   = 0.893826 / 0.947581
  DIFF   = +0.053755

========================================================================================================================
SPECIAL: 84_V33 VS 87_V33
========================================================================================================================
Ленина 125-127 А (1).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.024210
  BEST_DIFF=-0.083674
  BEST=0.944307 / 0.860633

Ленина 125-127 А (10).JPG
  FIRST=87_v33
  SECOND=84_v33
  FINAL_MARGIN=+0.001876
  BEST_DIFF=+0.053755
  BEST=0.893826 / 0.947581

Ленина 125-127 А (11).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.006080
  BEST_DIFF=-0.060998
  BEST=0.948665 / 0.887667

Ленина 125-127 А (12).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.012485
  BEST_DIFF=-0.077314
  BEST=0.946145 / 0.868831

Ленина 125-127 А (13).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.013271
  BEST_DIFF=-0.063361
  BEST=0.948489 / 0.885128

Ленина 125-127 А (14).JPG
  FIRST=87_v33
  SECOND=84_v33
  FINAL_MARGIN=+0.001037
  BEST_DIFF=+0.057438
  BEST=0.883096 / 0.940534

Ленина 125-127 А (15).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.023178
  BEST_DIFF=-0.083085
  BEST=0.942905 / 0.859820

Ленина 125-127 А (16).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.008709
  BEST_DIFF=-0.068154
  BEST=0.941929 / 0.873775

Ленина 125-127 А (17).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.002587
  BEST_DIFF=-0.058846
  BEST=0.942105 / 0.883259

Ленина 125-127 А (8).JPG
  FIRST=87_v33
  SECOND=84_v33
  FINAL_MARGIN=+0.005768
  BEST_DIFF=+0.068202
  BEST=0.882709 / 0.950911

Ленина 125-127 А (9).JPG
  FIRST=84_v33
  SECOND=87_v33
  FINAL_MARGIN=+0.004802
  BEST_DIFF=-0.057634
  BEST=0.943069 / 0.885435

========================================================================================================================
TOP 50 LOWEST FINAL MARGINS
========================================================================================================================
+0.001037 | 87_v33 / 84_v33 | BEST_DIFF=+0.057438 | Ленина 125-127 А (14).JPG
+0.001418 | 83_v33 / 92_v33 | BEST_DIFF=+0.003729 | 008.JPG
+0.001876 | 87_v33 / 84_v33 | BEST_DIFF=+0.053755 | Ленина 125-127 А (10).JPG
+0.002587 | 84_v33 / 87_v33 | BEST_DIFF=-0.058846 | Ленина 125-127 А (17).JPG
+0.003229 | 88_v33 / 89_v33 | BEST_DIFF=+0.004149 | Вавилова ул. - Радиаторный пер.  A (70).JPG
+0.004476 | 92_v33 / 83_v33 | BEST_DIFF=-0.005546 | 009.JPG
+0.004802 | 84_v33 / 87_v33 | BEST_DIFF=-0.057634 | Ленина 125-127 А (9).JPG
+0.005768 | 87_v33 / 84_v33 | BEST_DIFF=+0.068202 | Ленина 125-127 А (8).JPG
+0.006080 | 84_v33 / 87_v33 | BEST_DIFF=-0.060998 | Ленина 125-127 А (11).JPG
+0.006481 | 86_v33 / 89_v33 | BEST_DIFF=+0.011953 | Вавилова ул. - Радиаторный пер.  A (63).JPG
+0.007073 | 94_v33 / 89_v33 | BEST_DIFF=-0.011586 | Малиновского 25 к Доватора А (7).JPG
+0.008709 | 84_v33 / 87_v33 | BEST_DIFF=-0.068154 | Ленина 125-127 А (16).JPG
+0.009377 | 86_v33 / 89_v33 | BEST_DIFF=-0.041481 | менжин (7).JPG
+0.009692 | 91_v33 / 93_v33 | BEST_DIFF=-0.014178 | Нагибина Рубиновый А (1).JPG
+0.011073 | 83_v33 / 91_v33 | BEST_DIFF=-0.041538 | Нагибина 24 А (12).JPG
+0.011105 | 94_v33 / 93_v33 | BEST_DIFF=-0.024734 | Вавилова Радиаторный А (1).JPG
+0.011276 | 89_v33 / 85_v33 | BEST_DIFF=-0.104528 | Ленина Ашхабадский А (7).JPG
+0.012399 | 95_v33 / 94_v33 | BEST_DIFF=-0.000884 | Вавилова 52 А (20).JPG
+0.012485 | 84_v33 / 87_v33 | BEST_DIFF=-0.077314 | Ленина 125-127 А (12).JPG
+0.012795 | 87_v33 / 92_v33 | BEST_DIFF=+0.038996 | Шеболдаева 8 РИИЖТ (25).JPG
+0.013271 | 84_v33 / 87_v33 | BEST_DIFF=-0.063361 | Ленина 125-127 А (13).JPG
+0.013838 | 95_v33 / 92_v33 | BEST_DIFF=+0.022570 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (20).jpg
+0.014957 | 91_v33 / 94_v33 | BEST_DIFF=-0.000400 | Шеболдаева 95 А (8).JPG
+0.015100 | 94_v33 / 92_v33 | BEST_DIFF=-0.035188 | Вавилова ул. - Радиаторный пер.  A (34).JPG
+0.015792 | 89_v33 / 92_v33 | BEST_DIFF=+0.008918 | Стачки Зорге А (25).JPG
+0.017470 | 91_v33 / 93_v33 | BEST_DIFF=+0.012026 | Нагибина Рубиновый А (52).JPG
+0.017624 | 89_v33 / 92_v33 | BEST_DIFF=+0.051273 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (10).JPG
+0.018237 | 83_v33 / 81_v33 | BEST_DIFF=-0.070424 | Нагибина 24 А (13).JPG
+0.018574 | 92_v33 / 83_v33 | BEST_DIFF=-0.016185 | Комарова Добровольского А (8).JPG
+0.018835 | 95_v33 / 94_v33 | BEST_DIFF=-0.019621 | Вавилова 52 А (14).JPG
+0.019112 | 94_v33 / 95_v33 | BEST_DIFF=-0.036113 | Вавилова Радиаторный А (29).JPG
+0.019226 | 93_v33 / 95_v33 | BEST_DIFF=-0.017148 | Стачки 41 А (43).JPG
+0.020841 | 94_v33 / 92_v33 | BEST_DIFF=-0.013005 | Вавилова ул. - Радиаторный пер.  A (38).JPG
+0.021242 | 89_v33 / 90_v33 | BEST_DIFF=-0.022454 | Малиновского 25 к Стачки А (3).JPG
+0.021743 | 95_v33 / 78_v33 | BEST_DIFF=-0.051360 | Вавилова 52 А (10).JPG
+0.021962 | 92_v33 / 91_v33 | BEST_DIFF=-0.010215 | Комарова Добровольского А (1).JPG
+0.022421 | 91_v33 / 93_v33 | BEST_DIFF=-0.049885 | Нагибина Рубиновый А (8).JPG
+0.022948 | 92_v33 / 93_v33 | BEST_DIFF=-0.031653 | Комарова Добровольского А (42).JPG
+0.023178 | 84_v33 / 87_v33 | BEST_DIFF=-0.083085 | Ленина 125-127 А (15).JPG
+0.023587 | 90_v33 / 89_v33 | BEST_DIFF=-0.062209 | Малиновского 25 к Стачки А (4).JPG
+0.024210 | 84_v33 / 87_v33 | BEST_DIFF=-0.083674 | Ленина 125-127 А (1).JPG
+0.024909 | 89_v33 / 90_v33 | BEST_DIFF=-0.021769 | Малиновского 25 к Стачки А (5).JPG
+0.024985 | 92_v33 / 89_v33 | BEST_DIFF=-0.080618 | Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (18).JPG
+0.025068 | 89_v33 / 94_v33 | BEST_DIFF=-0.084426 | Малиновского 25 к Доватора (17).JPG
+0.025984 | 90_v33 / 89_v33 | BEST_DIFF=-0.079680 | Малиновского 25 к Стачки А (2).JPG
+0.026987 | 95_v33 / 94_v33 | BEST_DIFF=-0.049251 | Вавилова 52 А (8).JPG
+0.028498 | 79_v33 / 92_v33 | BEST_DIFF=-0.058804 | Комарова 20 Добровольского Б (4).JPG
+0.028809 | 81_v33 / 79_v33 | BEST_DIFF=-0.039384 | 1 Конной Армии 32 А (38).JPG
+0.029241 | 91_v33 / 93_v33 | BEST_DIFF=-0.044383 | Нагибина Рубиновый А (7).JPG
+0.029956 | 92_v33 / 89_v33 | BEST_DIFF=-0.054752 | Стачки Зорге А (48).JPG

========================================================================================================================
RECOMMENDED OCR TRIGGERS
========================================================================================================================
Potential OCR cases: 3

Ленина 125-127 А (8).JPG
  CURRENT=87_v33
  CANDIDATE=84_v33
  MARGIN=+0.005768
  BEST_DIFF=+0.068202

Ленина 125-127 А (14).JPG
  CURRENT=87_v33
  CANDIDATE=84_v33
  MARGIN=+0.001037
  BEST_DIFF=+0.057438

Ленина 125-127 А (10).JPG
  CURRENT=87_v33
  CANDIDATE=84_v33
  MARGIN=+0.001876
  BEST_DIFF=+0.053755

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 12:44:01

Да. Теперь картина стала **корректной**, и она довольно показательная.

### Что мы видим

На реальном `A_CURRENT` из 262 фотографий:

- **251/262** имеют margin ≥ 0.020 — то есть основная масса распознаётся уверенно.
- **50/262 (19.1%)** имеют margin < 0.030.
- **14/262 (5.34%)** — margin < 0.010.
- Только **7/262 (2.67%)** — margin < 0.005.

Но самое важное — `BEST` действительно нашёл **11 конфликтов**, а не один.

Из них:

**3 случая — очень сильный конфликт:**

```text
Ленина 125-127 А (8)   87 -> 84   BEST_DIFF +0.0682
Ленина 125-127 А (14)  87 -> 84   BEST_DIFF +0.0574
Ленина 125-127 А (10)  87 -> 84   BEST_DIFF +0.0538
```

И это не случайность: **все три относятся к одной паре адресов 84 ↔ 87**.

Причём остальные фотографии этой же серии практически однозначно показывают 84:

```text
(1)   84 -> 87   BEST_DIFF -0.0837
(11)  84 -> 87   BEST_DIFF -0.0610
(12)  84 -> 87   BEST_DIFF -0.0773
(13)  84 -> 87   BEST_DIFF -0.0634
(15)  84 -> 87   BEST_DIFF -0.0831
(16)  84 -> 87   BEST_DIFF -0.0682
(17)  84 -> 87   BEST_DIFF -0.0588
(9)   84 -> 87   BEST_DIFF -0.0576
```

То есть здесь **BEST явно содержит дополнительную информацию**, которую текущий `FINAL` не использует достаточно хорошо.

---

## Я бы сейчас НЕ менял основной алгоритм

Это важный момент.

Мы уже видим, что простое правило:

```text
если BEST второго выше BEST первого → выбираем второго
```

**слишком агрессивное**.

Потому что всего конфликтов 11, а сильных — 3. И нельзя автоматически перекидывать все 11.

А вот правило:

```text
если FINAL почти равен
И BEST второго значительно выше BEST первого
→ отправить фотографию на OCR
```

выглядит очень логично.

### Причём порог уже практически найден экспериментально

Для сильных случаев:

```text
FINAL_MARGIN < 0.006
BEST_DIFF > 0.05
```

получаем ровно:

```text
3 фотографии
```

То есть:

```text
Ленина 125-127 А (8)
Ленина 125-127 А (10)
Ленина 125-127 А (14)
```

Это именно те случаи, где DINO говорит:

> «два адреса практически равны, но характерный лучший образец второго адреса значительно лучше».

---

# Следующий шаг

Я предлагаю **не вмешиваться пока в распознавание**, а сделать отдельный тест:

```text
DINO
  ↓
FINAL
  ↓
если FINAL_MARGIN < 0.006
и BEST_DIFF > 0.05
  ↓
OCR
  ↓
номер таблички
  ↓
SQL/база адресов
  ↓
финальное имя
```

И сначала прогнать OCR **только на этих 3 фотографиях**.

Это очень хороший контрольный эксперимент: если OCR правильно определит 84 для всех трёх, мы получим доказательство, что архитектура:

**DINO → BEST conflict → OCR → адрес**

действительно работает.

После этого можно расширить триггер, например:

```text
FINAL_MARGIN < 0.010
AND BEST_DIFF > 0.020
```

Это даст нам уже несколько потенциально сложных случаев, но не будем запускать OCR на всех 262 фотографиях.

**Я бы сейчас сделал именно OCR-тест на этих 3 файлах, не трогая v33 и не меняя веса.**

---

### 👤 **User** — 2026-08-15 13:04:29

давай сделаем прогон **14/262 (5.34%)** — margin < 0.010. 

1.  Только **7/262 (2.67%)** — margin < 0.005. в этих случаях отдавая предпочтение best. результаты посмотрим и сдаем папку с расстортированными фото для визульного контроля

---

### 🤖 **Assistant** — 2026-08-15 13:04:31

Да. Это хороший следующий эксперимент. **Основной v33 не меняем** — делаем отдельный тестовый прогон.

Логика будет такая:

### Режим теста

Для всех 262 фото:

**1. Margin ≥ 0.010**

Оставляем обычный `A_CURRENT`:

```text
FINAL winner
```

**2. Margin < 0.010 и ≥ 0.005**

Оставляем обычный winner:

```text
FINAL winner
```

То есть проверяем именно 14 пограничных случаев, но не вмешиваемся в 7 самых спорных.

**3. Margin < 0.005**

В этих **7 случаях** включаем `BEST`:

```text
if BEST(second) > BEST(first):
    winner = second
else:
    winner = first
```

То есть `BEST` имеет право изменить результат **только для 7 наиболее пограничных фотографий**.

---

### Но важная деталь

В твоём списке 7 случаев `< 0.005` есть:

```text
14      87 -> 84   BEST +0.057
10      87 -> 84   BEST +0.054
17      84 -> 87   BEST -0.059
9       84 -> 87   BEST -0.058
8       87 -> 84   BEST +0.068
11      84 -> 87   BEST -0.061
63      86 -> 89   BEST +0.012
```

То есть `BEST` реально изменит **только 3 из 7**:

```text
87 → 84   (8)
87 → 84   (10)
87 → 84   (14)
```

Остальные четыре останутся без изменения.

---

## После этого

Сортируем **все 262 фотографии** по итоговому результату:

```text
output/...
├── 78_v33/
├── 79_v33/
├── 80_v33/
...
├── 95_v33/
```

Но я предлагаю сделать это **в отдельную папку**, чтобы вообще не затронуть предыдущий результат.

Например:

```text
output/visual_test_margin005/
```

И обязательно сохранить рядом CSV:

```text
image
old_winner
new_winner
margin
best_diff
changed
```

чтобы потом можно было точно увидеть, какие фотографии были перекинуты.

---

### Давай сначала найдём существующий скрипт сортировки

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SORT / RECOGNIZE SCRIPTS ==="
find . -maxdepth 3 -type f \( \
    -name "*.py" -o \
    -name "*.sh" \
\) | sort | grep -Ei 'sort|classif|recogn|test|benchmark'
```

И ещё:

```bash
echo
echo "=== OUTPUT DIRECTORIES ==="
find output -maxdepth 2 -type d | sort
```

И:

```bash
echo
echo "=== CURRENT RECOGNITION COMMANDS IN PROJECT ==="
grep -RniE 'recognize|copy|shutil.copy|shutil.copy2|mkdir|makedirs' \
    --include="*.py" \
    --include="*.sh" \
    . 2>/dev/null | head -100
```

**Пришли вывод.** После этого я дам конкретную команду/патч именно под существующую систему, чтобы не изобретать второй механизм сортировки.

---


## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 14:39:21

Да. Сделаем отдельный анализ **без изменения распознавания**: mapping серии → правильный номер, затем TOP-1/2/3/5 и список ошибок.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/analyze_accuracy.py <<'PY'
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

BENCH = Path("data/output/benchmark_v1/benchmark.json")

# Эталонное соответствие:
# название серии -> правильный fingerprint
MAPPING = {
    "Ашхабадский": 85,
    "Вавилова52": 95,
    "Добровольского17": 82,
    "Зорге": 92,
    "КА": 81,
    "Комарова13": 78,
    "Комарова28": 80,
    "Комарова_Добровольского": 79,
    "Ленина125": 84,
    "Малиновского(": 88,
    "Малиновского_к_Доватора": 89,
    "Малиновского_к_Стачки": 90,
    "Менжинского": 86,
    "Нагибина24": 83,
    "Радиаторный": 94,
    "Рубиновый": 91,
    "Стачки_41": 93,
    "Шеболдаева8": 87,
}

with BENCH.open(encoding="utf-8") as f:
    data = json.load(f)

rows = data["results"]

def series_name(filename):
    name = Path(filename).stem

    # Сначала точные/специальные варианты
    for key in sorted(MAPPING, key=len, reverse=True):
        if name.startswith(key):
            return key

    # На случай полного пути
    return None

groups = defaultdict(list)

for r in rows:
    s = series_name(r["file"])
    if s is None:
        print("WARNING: series not found:", r["file"])
    else:
        groups[s].append(r)

print("=" * 78)
print("ACCURACY BY SERIES")
print("=" * 78)

total = 0
acc1 = acc2 = acc3 = acc5 = 0

all_errors = []

for series, real in MAPPING.items():

    rs = groups.get(series, [])

    c1 = c2 = c3 = c5 = 0

    for r in rs:
        candidates = [
            r.get("top1"),
            r.get("top2"),
            r.get("top3"),
            r.get("top4"),
            r.get("top5"),
        ]

        if candidates[0] == f"{real}_v33":
            c1 += 1

        if f"{real}_v33" in candidates[:2]:
            c2 += 1

        if f"{real}_v33" in candidates[:3]:
            c3 += 1

        if f"{real}_v33" in candidates[:5]:
            c5 += 1

        if candidates[0] != f"{real}_v33":
            all_errors.append((series, real, r))

    n = len(rs)

    total += n
    acc1 += c1
    acc2 += c2
    acc3 += c3
    acc5 += c5

    print()
    print(f"{series:<28} REAL={real:2d}  N={n:2d}")
    print(
        f"  TOP-1 {c1:2d}/{n:<2d} "
        f"{100*c1/n:6.1f}%   "
        f"TOP-2 {c2:2d}/{n:<2d} "
        f"{100*c2/n:6.1f}%   "
        f"TOP-3 {c3:2d}/{n:<2d} "
        f"{100*c3/n:6.1f}%   "
        f"TOP-5 {c5:2d}/{n:<2d} "
        f"{100*c5/n:6.1f}%"
    )

print()
print("=" * 78)
print("TOTAL ACCURACY")
print("=" * 78)

print(f"TOTAL IMAGES : {total}")
print(f"TOP-1        : {acc1}/{total} = {100*acc1/total:.2f}%")
print(f"TOP-2        : {acc2}/{total} = {100*acc2/total:.2f}%")
print(f"TOP-3        : {acc3}/{total} = {100*acc3/total:.2f}%")
print(f"TOP-5        : {acc5}/{total} = {100*acc5/total:.2f}%")

print()
print("=" * 78)
print("TOP-1 ERRORS")
print("=" * 78)

for series, real, r in all_errors:
    print()
    print(Path(r["file"]).name)
    print(f"  REAL : {real}")
    print(
        f"  TOP1 : {r['top1']} "
        f"{float(r['top1_score']):.6f}"
    )
    print(
        f"  TOP2 : {r['top2']} "
        f"{float(r['top2_score']):.6f}"
    )
    print(
        f"  TOP3 : {r['top3']} "
        f"{float(r['top3_score']):.6f}"
    )
    print(
        f"  TOP4 : {r['top4']} "
        f"{float(r['top4_score']):.6f}"
    )
    print(
        f"  TOP5 : {r['top5']} "
        f"{float(r['top5_score']):.6f}"
    )

print()
print("=" * 78)
print("ERROR PAIRS")
print("=" * 78)

pairs = Counter()

for series, real, r in all_errors:
    pairs[(real, int(r["top1"].split("_")[0]))] += 1

for (real, pred), n in pairs.most_common():
    print(f"{real:2d} -> {pred:2d} : {n}")

PY

uv run python /tmp/analyze_accuracy.py
```

### Что нам особенно важно

В конце будет блок:

```text
TOTAL ACCURACY
TOP-1
TOP-2
TOP-3
TOP-5
```

и затем:

```text
ERROR PAIRS
92 -> 91 : ...
92 -> 93 : ...
84 -> 87 : ...
89 -> 92 : ...
```

Вот этот последний блок особенно полезен. Он покажет, **какие адреса реально путаются между собой**, а не просто общий процент.

Пришли весь вывод. После него уже решим, насколько агрессивно применять V35: сейчас я бы **не менял порог 0.005**, пока не увидим реальные пары ошибок.

---

### 👤 **User** — 2026-08-15 14:39:45

REAL пока не вычисляется автоматически для переименованных тестовых файлов.
Следующим шагом построим mapping адрес -> fingerprint и получим настоящий TOP-1/2/3/5 accuracy.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/analyze_accuracy.py <<'PY'
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

BENCH = Path("data/output/benchmark_v1/benchmark.json")

# Эталонное соответствие:
# название серии -> правильный fingerprint
MAPPING = {
    "Ашхабадский": 85,
    "Вавилова52": 95,
    "Добровольского17": 82,
    "Зорге": 92,
    "КА": 81,
    "Комарова13": 78,
    "Комарова28": 80,
    "Комарова_Добровольского": 79,
    "Ленина125": 84,
    "Малиновского(": 88,
uv run python /tmp/analyze_accuracy.pyn}"):]))] += 1tal:.2f}%")
==============================================================================
ACCURACY BY SERIES
==============================================================================

Ашхабадский                  REAL=85  N=18
  TOP-1 17/18   94.4%   TOP-2 18/18  100.0%   TOP-3 18/18  100.0%   TOP-5 18/18  100.0%

Вавилова52                   REAL=95  N=16
  TOP-1 16/16  100.0%   TOP-2 16/16  100.0%   TOP-3 16/16  100.0%   TOP-5 16/16  100.0%

Добровольского17             REAL=82  N= 9
  TOP-1  9/9   100.0%   TOP-2  9/9   100.0%   TOP-3  9/9   100.0%   TOP-5  9/9   100.0%

Зорге                        REAL=92  N=17
  TOP-1 14/17   82.4%   TOP-2 17/17  100.0%   TOP-3 17/17  100.0%   TOP-5 17/17  100.0%

КА                           REAL=81  N=16
  TOP-1 16/16  100.0%   TOP-2 16/16  100.0%   TOP-3 16/16  100.0%   TOP-5 16/16  100.0%

Комарова13                   REAL=78  N=20
  TOP-1 20/20  100.0%   TOP-2 20/20  100.0%   TOP-3 20/20  100.0%   TOP-5 20/20  100.0%

Комарова28                   REAL=80  N= 8
  TOP-1  8/8   100.0%   TOP-2  8/8   100.0%   TOP-3  8/8   100.0%   TOP-5  8/8   100.0%

Комарова_Добровольского      REAL=79  N= 8
  TOP-1  8/8   100.0%   TOP-2  8/8   100.0%   TOP-3  8/8   100.0%   TOP-5  8/8   100.0%

Ленина125                    REAL=84  N=11
  TOP-1  8/11   72.7%   TOP-2 11/11  100.0%   TOP-3 11/11  100.0%   TOP-5 11/11  100.0%

Малиновского(                REAL=88  N=15
  TOP-1 15/15  100.0%   TOP-2 15/15  100.0%   TOP-3 15/15  100.0%   TOP-5 15/15  100.0%

Малиновского_к_Доватора      REAL=89  N=16
  TOP-1 15/16   93.8%   TOP-2 16/16  100.0%   TOP-3 16/16  100.0%   TOP-5 16/16  100.0%

Малиновского_к_Стачки        REAL=90  N= 5
  TOP-1  3/5    60.0%   TOP-2  5/5   100.0%   TOP-3  5/5   100.0%   TOP-5  5/5   100.0%

Менжинского                  REAL=86  N=14
  TOP-1 14/14  100.0%   TOP-2 14/14  100.0%   TOP-3 14/14  100.0%   TOP-5 14/14  100.0%

Нагибина24                   REAL=83  N=17
  TOP-1 17/17  100.0%   TOP-2 17/17  100.0%   TOP-3 17/17  100.0%   TOP-5 17/17  100.0%

Радиаторный                  REAL=94  N=25
  TOP-1 23/25   92.0%   TOP-2 23/25   92.0%   TOP-3 23/25   92.0%   TOP-5 25/25  100.0%

Рубиновый                    REAL=91  N=12
  TOP-1 12/12  100.0%   TOP-2 12/12  100.0%   TOP-3 12/12  100.0%   TOP-5 12/12  100.0%

Стачки_41                    REAL=93  N=12
  TOP-1 12/12  100.0%   TOP-2 12/12  100.0%   TOP-3 12/12  100.0%   TOP-5 12/12  100.0%

Шеболдаева8                  REAL=87  N=17
  TOP-1 17/17  100.0%   TOP-2 17/17  100.0%   TOP-3 17/17  100.0%   TOP-5 17/17  100.0%

==============================================================================
TOTAL ACCURACY
==============================================================================
TOTAL IMAGES : 256
TOP-1        : 244/256 = 95.31%
TOP-2        : 254/256 = 99.22%
TOP-3        : 254/256 = 99.22%
TOP-5        : 256/256 = 100.00%

==============================================================================
TOP-1 ERRORS
==============================================================================

Ашхабадский_08.JPG
  REAL : 85
  TOP1 : 89_v33 0.636044
  TOP2 : 85_v33 0.625444
  TOP3 : 94_v33 0.623780
  TOP4 : 91_v33 0.614940
  TOP5 : 80_v33 0.603660

Зорге_06.JPG
  REAL : 92
  TOP1 : 89_v33 0.850253
  TOP2 : 92_v33 0.834775
  TOP3 : 85_v33 0.827361
  TOP4 : 93_v33 0.812003
  TOP5 : 86_v33 0.810573

Зорге_15.JPG
  REAL : 92
  TOP1 : 89_v33 0.872659
  TOP2 : 92_v33 0.854816
  TOP3 : 86_v33 0.843098
  TOP4 : 85_v33 0.838548
  TOP5 : 94_v33 0.830380

Зорге_17.jpg
  REAL : 92
  TOP1 : 95_v33 0.869104
  TOP2 : 92_v33 0.855266
  TOP3 : 94_v33 0.854439
  TOP4 : 91_v33 0.841907
  TOP5 : 86_v33 0.838367

Ленина125_02.JPG
  REAL : 84
  TOP1 : 87_v33 0.887593
  TOP2 : 84_v33 0.881740
  TOP3 : 79_v33 0.871603
  TOP4 : 92_v33 0.863742
  TOP5 : 83_v33 0.855895

Ленина125_04.JPG
  REAL : 84
  TOP1 : 87_v33 0.895798
  TOP2 : 84_v33 0.894985
  TOP3 : 79_v33 0.881853
  TOP4 : 92_v33 0.877599
  TOP5 : 83_v33 0.867235

Ленина125_08.JPG
  REAL : 84
  TOP1 : 87_v33 0.888517
  TOP2 : 84_v33 0.887613
  TOP3 : 79_v33 0.872563
  TOP4 : 83_v33 0.860123
  TOP5 : 92_v33 0.858829

Малиновского_к_Доватора_10.JPG
  REAL : 89
  TOP1 : 94_v33 0.834451
  TOP2 : 89_v33 0.826808
  TOP3 : 86_v33 0.817796
  TOP4 : 82_v33 0.816861
  TOP5 : 81_v33 0.804640

Малиновского_к_Стачки_03.JPG
  REAL : 90
  TOP1 : 89_v33 0.833983
  TOP2 : 90_v33 0.812631
  TOP3 : 80_v33 0.776533
  TOP4 : 85_v33 0.770462
  TOP5 : 92_v33 0.768132

Малиновского_к_Стачки_05.JPG
  REAL : 90
  TOP1 : 89_v33 0.800856
  TOP2 : 90_v33 0.774688
  TOP3 : 86_v33 0.773678
  TOP4 : 92_v33 0.773302
  TOP5 : 93_v33 0.757997

Радиаторный_24.JPG
  REAL : 94
  TOP1 : 86_v33 0.800540
  TOP2 : 89_v33 0.794075
  TOP3 : 92_v33 0.780783
  TOP4 : 94_v33 0.756868
  TOP5 : 93_v33 0.756602

Радиаторный_25.JPG
  REAL : 94
  TOP1 : 89_v33 0.794089
  TOP2 : 88_v33 0.789122
  TOP3 : 86_v33 0.780216
  TOP4 : 92_v33 0.768311
  TOP5 : 94_v33 0.765951

==============================================================================
ERROR PAIRS
==============================================================================
84 -> 87 : 3
92 -> 89 : 2
90 -> 89 : 2
85 -> 89 : 1
92 -> 95 : 1
89 -> 94 : 1
94 -> 86 : 1
94 -> 89 : 1
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:39:47

Вот теперь картина очень хорошая. **Новые слепки дали отличный результат.**

### Итог v33 на 256 фотографиях

| Метрика | Результат |
|---|---:|
| **TOP-1** | **244 / 256 = 95.31%** |
| **TOP-2** | **254 / 256 = 99.22%** |
| **TOP-3** | **254 / 256 = 99.22%** |
| **TOP-5** | **256 / 256 = 100%** |

То есть **ни одной фотографии нет вне правильного TOP-5**.

И это как раз тот случай, где предложенная тобой идея с последовательностью фотографий очень хорошо подходит.

### Где реально остались ошибки

Всего **12 TOP-1 ошибок**:

- 84 → 87: **3**
- 92 → 89: **2**
- 90 → 89: **2**
- 85 → 89: **1**
- 92 → 95: **1**
- 89 → 94: **1**
- 94 → 86: **1**
- 94 → 89: **1**

Причём почти все ошибки находятся **не где-то далеко**, а правильный адрес находится сразу вторым кандидатом.

Например:

```text
Ленина125_02
87 = 0.887593
84 = 0.881740
```

Разница всего **0.005853**.

```text
Ленина125_04
87 = 0.895798
84 = 0.894985
```

Разница всего **0.000813**.

```text
Ленина125_08
87 = 0.888517
84 = 0.887613
```

Разница всего **0.000904**.

Это практически идеальный случай для соседнего контекста.

---

### И главное — Малиновского

Тут:

```text
90 → 89
90 → 89
```

Но правильный `90` каждый раз **TOP-2**.

То есть серия:

**Малиновского — Стачки**

очень похожа на:

**Малиновского — Доватора**

но TOP-2 уже содержит правильный адрес.

---

### Радиаторный

Здесь две фотографии сложнее:

```text
Радиаторный_24
86 → 89 → 92 → 94

Радиаторный_25
89 → 88 → 86 → 92 → 94
```

Но `94` всё равно находится в TOP-5.

Это как раз те случаи, где **одна отдельная фотография визуально может быть действительно неоднозначной**.

---

## Поэтому я бы сейчас НЕ трогал DINOv2

У нас уже есть очень сильная база:

**95.31% TOP-1 → 99.22% TOP-2 → 100% TOP-5.**

Теперь логично использовать информацию о серии:

```text
предыдущая фотография
        ↓
    текущая
        ↓
следующая фотография
```

Если текущая фотография имеет:

```text
TOP1 = 87
TOP2 = 84
```

а соседние фотографии уверенно определились как `84`, то мы можем сказать:

> текущая почти наверняка 84.

Именно это уже продемонстрировала V35 на старом прогоне.

---

# Следующий шаг

Я предлагаю сделать **контрольный V35 на этом новом benchmark**, не меняя саму модель.

Но есть важный момент: текущий `sort_neighbor_v35.py` читает старый:

```text
output/benchmark_components/full_analysis/margin_best.csv
```

а новый benchmark лежит здесь:

```text
data/output/benchmark_v1/benchmark.json
```

Поэтому **не надо просто запускать старый V35** — он будет работать не с этим новым прогоном.

Лучше сделать отдельный:

```text
sort_neighbor_v35_benchmark.py
```

который напрямую возьмёт:

```text
data/output/benchmark_v1/benchmark.json
```

и:

1. сохранит исходный TOP-1;
2. посмотрит ±2 фотографии;
3. будет менять только случаи с маленьким margin;
4. использует TOP-2 как альтернативу;
5. сохранит подробный `neighbor_decision.csv`;
6. разложит фотографии по папкам `78 ... 95`.

Причём я предлагаю **сначала вообще ничего не менять физически**, а получить отчёт:

```text
фото                 v33   TOP2   V35   причина
Ленина125_02         87     84    84    3 соседа за 84
Ленина125_04         87     84    84    3 соседа за 84
...
```

А потом уже посмотрим, что V35 исправила.

**Это сейчас самый правильный эксперимент:** мы уже знаем истинную точность `95.31%`, поэтому сможем объективно измерить, улучшает ли соседняя логика результат или случайно портит правильные решения.

---

### 👤 **User** — 2026-08-15 14:40:54

давай

---

### 🤖 **Assistant** — 2026-08-15 14:40:55

Да. Сделаем отдельный прогон **V35 на новом benchmark**, не затрагивая старые результаты.

Сначала создай скрипт:

```bash id="create-v35b"
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v35_benchmark.py <<'PY'
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
PY

chmod +x scripts/sort_neighbor_v35_benchmark.py

uv run python -m py_compile scripts/sort_neighbor_v35_benchmark.py

echo "STATUS=$?"
```

Если получишь:

```text
STATUS=0
```

запускай:

```bash id="run-v35b"
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/neighbor_v35_benchmark

uv run python -u scripts/sort_neighbor_v35_benchmark.py
```

### Важный момент

Здесь используется **именно новый**:

```text
data/output/benchmark_v1/benchmark.json
```

то есть те самые **256 фотографий и новые слепки**.

И результат будет здесь:

```text
output/neighbor_v35_benchmark/sorted/
```

с папками:

```text
78
79
80
...
95
```

А главное — здесь:

```text
output/neighbor_v35_benchmark/neighbor_decision.csv
```

После запуска пришли вывод начиная с:

```text
RESULT
```

особенно блок `CHANGED`. Тогда сравним:

**95.31% TOP-1 → сколько даст V35.**

---

### 👤 **User** — 2026-08-15 14:41:48

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/analyze_accuracy.py <<'PY'
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

BENCH = Path("data/output/benchmark_v1/benchmark.json")

# Эталонное соответствие:
# название серии -> правильный fingerprint
MAPPING = {
    "Ашхабадский": 85,
    "Вавилова52": 95,
    "Добровольского17": 82,
    "Зорге": 92,
    "КА": 81,
    "Комарова13": 78,
    "Комарова28": 80,
    "Комарова_Добровольского": 79,
    "Ленина125": 84,
    "Малиновского(": 88,
uv run python /tmp/analyze_accuracy.pyn}"):]))] += 1tal:.2f}%")
==============================================================================
ACCURACY BY SERIES
==============================================================================

Ашхабадский                  REAL=85  N=18
  TOP-1 17/18   94.4%   TOP-2 18/18  100.0%   TOP-3 18/18  100.0%   TOP-5 18/18  100.0%

Вавилова52                   REAL=95  N=16
  TOP-1 16/16  100.0%   TOP-2 16/16  100.0%   TOP-3 16/16  100.0%   TOP-5 16/16  100.0%

Добровольского17             REAL=82  N= 9
  TOP-1  9/9   100.0%   TOP-2  9/9   100.0%   TOP-3  9/9   100.0%   TOP-5  9/9   100.0%

Зорге                        REAL=92  N=17
  TOP-1 14/17   82.4%   TOP-2 17/17  100.0%   TOP-3 17/17  100.0%   TOP-5 17/17  100.0%

КА                           REAL=81  N=16
  TOP-1 16/16  100.0%   TOP-2 16/16  100.0%   TOP-3 16/16  100.0%   TOP-5 16/16  100.0%

Комарова13                   REAL=78  N=20
  TOP-1 20/20  100.0%   TOP-2 20/20  100.0%   TOP-3 20/20  100.0%   TOP-5 20/20  100.0%

Комарова28                   REAL=80  N= 8
  TOP-1  8/8   100.0%   TOP-2  8/8   100.0%   TOP-3  8/8   100.0%   TOP-5  8/8   100.0%

Комарова_Добровольского      REAL=79  N= 8
  TOP-1  8/8   100.0%   TOP-2  8/8   100.0%   TOP-3  8/8   100.0%   TOP-5  8/8   100.0%

Ленина125                    REAL=84  N=11
  TOP-1  8/11   72.7%   TOP-2 11/11  100.0%   TOP-3 11/11  100.0%   TOP-5 11/11  100.0%

Малиновского(                REAL=88  N=15
  TOP-1 15/15  100.0%   TOP-2 15/15  100.0%   TOP-3 15/15  100.0%   TOP-5 15/15  100.0%

Малиновского_к_Доватора      REAL=89  N=16
  TOP-1 15/16   93.8%   TOP-2 16/16  100.0%   TOP-3 16/16  100.0%   TOP-5 16/16  100.0%

Малиновского_к_Стачки        REAL=90  N= 5
  TOP-1  3/5    60.0%   TOP-2  5/5   100.0%   TOP-3  5/5   100.0%   TOP-5  5/5   100.0%

Менжинского                  REAL=86  N=14
  TOP-1 14/14  100.0%   TOP-2 14/14  100.0%   TOP-3 14/14  100.0%   TOP-5 14/14  100.0%

Нагибина24                   REAL=83  N=17
  TOP-1 17/17  100.0%   TOP-2 17/17  100.0%   TOP-3 17/17  100.0%   TOP-5 17/17  100.0%

Радиаторный                  REAL=94  N=25
  TOP-1 23/25   92.0%   TOP-2 23/25   92.0%   TOP-3 23/25   92.0%   TOP-5 25/25  100.0%

Рубиновый                    REAL=91  N=12
  TOP-1 12/12  100.0%   TOP-2 12/12  100.0%   TOP-3 12/12  100.0%   TOP-5 12/12  100.0%

Стачки_41                    REAL=93  N=12
  TOP-1 12/12  100.0%   TOP-2 12/12  100.0%   TOP-3 12/12  100.0%   TOP-5 12/12  100.0%

Шеболдаева8                  REAL=87  N=17
  TOP-1 17/17  100.0%   TOP-2 17/17  100.0%   TOP-3 17/17  100.0%   TOP-5 17/17  100.0%

==============================================================================
TOTAL ACCURACY
==============================================================================
TOTAL IMAGES : 256
TOP-1        : 244/256 = 95.31%
TOP-2        : 254/256 = 99.22%
TOP-3        : 254/256 = 99.22%
TOP-5        : 256/256 = 100.00%

==============================================================================
TOP-1 ERRORS
==============================================================================

Ашхабадский_08.JPG
  REAL : 85
  TOP1 : 89_v33 0.636044
  TOP2 : 85_v33 0.625444
  TOP3 : 94_v33 0.623780
  TOP4 : 91_v33 0.614940
  TOP5 : 80_v33 0.603660

Зорге_06.JPG
  REAL : 92
  TOP1 : 89_v33 0.850253
  TOP2 : 92_v33 0.834775
  TOP3 : 85_v33 0.827361
  TOP4 : 93_v33 0.812003
  TOP5 : 86_v33 0.810573

Зорге_15.JPG
  REAL : 92
  TOP1 : 89_v33 0.872659
  TOP2 : 92_v33 0.854816
  TOP3 : 86_v33 0.843098
  TOP4 : 85_v33 0.838548
  TOP5 : 94_v33 0.830380

Зорге_17.jpg
  REAL : 92
  TOP1 : 95_v33 0.869104
  TOP2 : 92_v33 0.855266
  TOP3 : 94_v33 0.854439
  TOP4 : 91_v33 0.841907
  TOP5 : 86_v33 0.838367

Ленина125_02.JPG
  REAL : 84
  TOP1 : 87_v33 0.887593
  TOP2 : 84_v33 0.881740
  TOP3 : 79_v33 0.871603
  TOP4 : 92_v33 0.863742
  TOP5 : 83_v33 0.855895

Ленина125_04.JPG
  REAL : 84
  TOP1 : 87_v33 0.895798
  TOP2 : 84_v33 0.894985
  TOP3 : 79_v33 0.881853
  TOP4 : 92_v33 0.877599
  TOP5 : 83_v33 0.867235

Ленина125_08.JPG
  REAL : 84
  TOP1 : 87_v33 0.888517
  TOP2 : 84_v33 0.887613
  TOP3 : 79_v33 0.872563
  TOP4 : 83_v33 0.860123
  TOP5 : 92_v33 0.858829

Малиновского_к_Доватора_10.JPG
  REAL : 89
  TOP1 : 94_v33 0.834451
  TOP2 : 89_v33 0.826808
  TOP3 : 86_v33 0.817796
  TOP4 : 82_v33 0.816861
  TOP5 : 81_v33 0.804640

Малиновского_к_Стачки_03.JPG
  REAL : 90
  TOP1 : 89_v33 0.833983
  TOP2 : 90_v33 0.812631
  TOP3 : 80_v33 0.776533
  TOP4 : 85_v33 0.770462
  TOP5 : 92_v33 0.768132

Малиновского_к_Стачки_05.JPG
  REAL : 90
  TOP1 : 89_v33 0.800856
  TOP2 : 90_v33 0.774688
  TOP3 : 86_v33 0.773678
  TOP4 : 92_v33 0.773302
  TOP5 : 93_v33 0.757997

Радиаторный_24.JPG
  REAL : 94
  TOP1 : 86_v33 0.800540
  TOP2 : 89_v33 0.794075
  TOP3 : 92_v33 0.780783
  TOP4 : 94_v33 0.756868
  TOP5 : 93_v33 0.756602

Радиаторный_25.JPG
  REAL : 94
  TOP1 : 89_v33 0.794089
  TOP2 : 88_v33 0.789122
  TOP3 : 86_v33 0.780216
  TOP4 : 92_v33 0.768311
  TOP5 : 94_v33 0.765951

==============================================================================
ERROR PAIRS
==============================================================================
84 -> 87 : 3
92 -> 89 : 2
90 -> 89 : 2
85 -> 89 : 1
92 -> 95 : 1
89 -> 94 : 1
94 -> 86 : 1
94 -> 89 : 1
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v35_benchmark.py <<'PY'
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

echo "STATUS=$?" py_compile scripts/sort_neighbor_v35_benchmark.py)
STATUS=0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/neighbor_v35_benchmark

uv run python -u scripts/sort_neighbor_v35_benchmark.py
================================================================================
NEIGHBOR CONTEXT V35 — NEW BENCHMARK
================================================================================
Input images : 256
Margin limit : 0.005
Neighbor +/- : 2

================================================================================
RESULT
================================================================================
Total images:        256
Margin < 0.005:      5
Changed by neighbors:       1

CHANGED
--------------------------------------------------------------------------------
Ленина125_11.JPG
    84 -> 87
    margin=0.002970
    reason=SECOND_SUPPORTED_BY_2+_NEIGHBORS
    second: -2:Ленина125_09.JPG; -1:Ленина125_10.JPG; +1:Малиновского(_01.JPG; +2:Малиновского(_02.JPG

DISTRIBUTION
--------------------------------------------------------------------------------
78     20
79      8
80      8
81     16
82      9
83     17
84      7
85     17
86     15
87     21
88     15
89     21
90      3
91     12
92     14
93     12
94     24
95     17
--------------------------------------------------------------------------------
TOTAL        256

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v35_benchmark/sorted
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v35_benchmark/neighbor_decision.csv

---

### 🤖 **Assistant** — 2026-08-15 14:41:48

Да. И здесь мы поймали **важную проблему именно в логике V35**, а не в DINOv2.

### Что произошло

Базовое распознавание:

- **TOP-1: 244/256 = 95.31%**
- **TOP-2: 254/256 = 99.22%**
- **TOP-5: 256/256 = 100%**

V35 с соседями изменил только **1 фотографию**:

```text
Ленина125_11.JPG
84 -> 87
```

Но это **ошибка**.

Почему? Потому что соседями для `Ленина125_11` стали:

```text
-2 Ленина125_09
-1 Ленина125_10
+1 Малиновского(_01
+2 Малиновского(_02
```

То есть скрипт использует **физический порядок файлов в общей папке `test`**, а не принадлежность к серии.

И получается:

```text
Ленина125_09
Ленина125_10
Ленина125_11
Малиновского(_01
Малиновского(_02
```

Для `Ленина125_11` два соседних изображения после него уже относятся к **другому адресу**. Поэтому V35 решил:

> второй кандидат поддержан соседями

хотя на самом деле это **ложная поддержка**.

### Значит, текущую V35 оставляем как экспериментальную, но не принимаем

Особенно показательно:

```text
Было:
84 = 8/11

После V35:
84 = 7/11
87 = 21 вместо 20
```

То есть accuracy фактически ухудшилась.

---

## Что я предлагаю сделать сейчас

Нам нужно немного изменить алгоритм V35:

**соседями считать только фотографии той же серии/адреса**, а не просто соседние файлы в каталоге.

Например:

```text
Ленина125_09
Ленина125_10
Ленина125_11
```

считаются соседями.

А:

```text
Малиновского(_01
Малиновского(_02
```

уже **не являются соседями**.

Но есть ещё более интересный момент.

У нас есть **12 ошибок TOP-1**, и большинство из них имеют правильный адрес на втором месте:

```text
84 -> 87   3 раза
92 -> 89   2 раза
90 -> 89   2 раза
85 -> 89   1
92 -> 95   1
89 -> 94   1
94 -> 86   1
94 -> 89   1
```

И практически все они имеют очень маленький margin.

Это именно тот случай, для которого мы и делали neighbor logic.

### Следующий правильный эксперимент

Я бы сейчас **не менял DINO и не трогал V33**.

Сделаем V36:

1. Берём исходный `TOP-1`.
2. Смотрим только изображения **внутри одной серии**.
3. Если `margin < 0.005` — включаем соседний контекст.
4. Соседи должны быть только из той же серии.
5. Если второй кандидат подтверждён — меняем.
6. Если нет — оставляем V33.
7. Считаем новую accuracy.
8. Отдельно покажем **все изменения V33 → V36**.

И главное — проверим именно эти проблемные серии:

- Ленина 125
- Зорге
- Малиновского → Доватора
- Малиновского → Стачки
- Ашхабадский
- Радиаторный

**Это будет уже честный тест алгоритма исправления неоднозначных кадров.**

Сейчас я бы V35 в production не ставил. Базовый **V33 пока остаётся лучшим: 95.31% TOP-1 и 100% TOP-5.**

---

### 👤 **User** — 2026-08-15 14:42:57

в реальности фотографии будут иметь наименования img_000...img_999

---

### 🤖 **Assistant** — 2026-08-15 14:42:57

Да — тогда **соседний контекст по порядку файлов вообще нельзя использовать**.

В реальном режиме будет:

```text
img_000.JPG
img_001.JPG
img_002.JPG
...
img_999.JPG
```

и соседние номера могут быть **совершенно разными адресами**. Поэтому логика V35:

```text
i-2, i-1, i+1, i+2
```

для production **невалидна**.

Но это не значит, что neighbor-идею надо выбросить. Нужно изменить источник контекста.

### Правильная архитектура

Для каждого `img_xxx`:

```text
DINOv2
   ↓
TOP кандидаты
   ↓
margin
   ↓
если уверенно → TOP-1
   ↓
если margin < 0.005
   ↓
ищем дополнительные подтверждения
```

А подтверждения берём не из соседних `img_`, а из **самого изображения / базы слепков**.

У нас уже есть очень сильная вещь — `best_image` и набор изображений внутри fingerprint.

Можно сделать:

**TOP-1 = 89**

**TOP-2 = 92**

и при маленьком margin посмотреть:

- сколько похожих эталонных изображений есть у 89;
- сколько у 92;
- насколько стабильно совпадение;
- насколько близки patch/scene embeddings;
- насколько несколько разных эталонных фотографий поддерживают кандидата.

То есть вместо:

```text
соседи фотографии
```

делаем:

```text
соседи КАНДИДАТА в fingerprint
```

Это уже соответствует реальному сценарию.

И ещё важнее: поскольку сейчас у нас **TOP-5 = 100%**, информация уже находится внутри результата распознавания. Нам осталось правильно использовать её для разрешения неоднозначных TOP-1.

Я бы следующим экспериментом сделал **V36 Candidate Context**:

```text
TOP-1
TOP-2
TOP-3
TOP-5
   ↓
margin < 0.005
   ↓
анализ поддержки кандидатов
   ↓
выбор кандидата
```

При этом **обычные уверенные кадры вообще не трогаем**.

Это намного правильнее для будущего режима `img_000...img_999`.

---

### 👤 **User** — 2026-08-15 14:44:51

в этом случае должна быть такая логика:
-есть сомнение на счет фото - смотрим на следущие два фото - если они похожи на кандидата 2 - значит это то, что надо, если второе фото не похоже, но похоже первое - значит тоже оно, если не похожи следующие, значит смотрим пердудщие две по такому же епринципу

---

### 🤖 **Assistant** — 2026-08-15 14:44:51

Да. **Вот это уже правильная логика для реального потока фотографий `img_000...img_999`.** И она отличается от нашей текущей V35 принципиально.

Здесь соседние фотографии имеют смысл не потому, что у них похожие имена, а потому что **фотограф, скорее всего, снимает один объект/адрес несколькими кадрами подряд**.

### Логика должна быть именно такой

Допустим:

```text
img_100
img_101   ← сомнительное фото
img_102
img_103
```

Распознаём `img_101`:

```text
TOP-1 = 87
TOP-2 = 84
margin = 0.002
```

Считаем `87` основным, но есть сомнение.

#### Шаг 1 — смотрим следующие два

```text
img_102 → 84
img_103 → 84
```

Получаем:

```text
2 из 2 → кандидат 2
```

→ **меняем 87 на 84.**

---

### Если только первое следующее подтверждает

```text
img_102 → 84
img_103 → 87
```

Тогда:

```text
1 → кандидат 2
1 → кандидат 1
```

И по твоему правилу:

> если второе фото не похоже, но первое похоже — значит тоже оно

→ **выбираем 84.**

То есть достаточно **хотя бы одного подтверждения из следующих двух**, при условии что второе не даёт более сильного противоречия.

---

### Если следующие два не подтвердили

Например:

```text
img_102 → 89
img_103 → 92
```

Тогда вперёд ничего не нашли.

Переходим назад:

```text
img_099 → 84
img_098 → 84
```

→ **выбираем 84.**

---

## Но есть один важный нюанс

Нельзя использовать просто `TOP-1` соседнего изображения.

Потому что сосед тоже может ошибиться.

Лучше считать:

```text
"похож на кандидата"
```

если кандидат находится у соседнего фото хотя бы в **TOP-2**, а желательно учитывать score.

Например:

```text
img_102
TOP1 = 87
TOP2 = 84
```

Это всё равно **поддержка 84**.

Таким образом:

### Для сомнительного кадра

```text
CURRENT = TOP1
CANDIDATE = TOP2
```

Проверяем:

```text
+1 → есть candidate?
+2 → есть candidate?
```

Если да → candidate.

Если нет:

```text
-1 → есть candidate?
-2 → есть candidate?
```

Если да → candidate.

---

# И ещё важнее — порядок действий

Я бы зафиксировал алгоритм V36 так:

```text
                 ┌──────────────┐
                 │  Распознали  │
                 │    img_N     │
                 └──────┬───────┘
                        ↓
                 margin >= 0.005?
                   /          \
                 ДА            НЕТ
                 ↓              ↓
              TOP-1       берём TOP-2
                 ↓              ↓
              ГОТОВО       смотрим +1
                              +2
                               ↓
                       есть TOP-2?
                       /         \
                     ДА           НЕТ
                     ↓             ↓
                 TOP-2          смотрим -1
                                  -2
                                    ↓
                              есть TOP-2?
                              /        \
                            ДА          НЕТ
                            ↓            ↓
                         TOP-2        TOP-1
```

### При этом

**Уверенные фотографии вообще не подвергаются соседней коррекции.**

Это очень важно.

Мы не хотим превратить:

```text
95.31% TOP-1
```

в систему, где соседние кадры постоянно перетаскивают правильные результаты.

---

## И я бы добавил ещё одно правило

Если:

```text
img_N → TOP1=87, TOP2=84
```

а:

```text
img_N+1 → TOP1=84
img_N+2 → TOP1=84
```

то это **очень сильное подтверждение 84**.

Но если:

```text
img_N+1 → TOP1=84
img_N+2 → TOP1=89
```

мы не должны автоматически менять.

Тут лучше использовать **силу уверенности соседей**.

---

Именно такой алгоритм хорошо соответствует будущему сценарию:

```text
img_000
img_001
img_002
...
img_999
```

где порядок съёмки сохраняется, но **имена файлов ничего не говорят об адресе**.

**Я бы сейчас переделал V35 именно в эту V36-логику и прогнал на нашем benchmark из 256 фотографий.** Тогда мы сможем точно увидеть, сколько из 12 ошибок она исправляет и сколько правильных решений случайно портит.

---

### 👤 **User** — 2026-08-15 14:46:00

давай

---

### 🤖 **Assistant** — 2026-08-15 14:46:00

Да. Делаем **V36**, но сначала без изменения V33: V36 будет только постобработкой сомнительных кадров.

Нужна одна важная деталь: в текущем benchmark фотографии уже идут в правильном порядке, поэтому можем использовать **порядок строк `benchmark.json`**, а не имена файлов.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v36.py <<'PY'
#!/usr/bin/env python3

import json
import csv
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"
SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v36"
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
PY

uv run python -m py_compile scripts/sort_neighbor_v36.py
echo "STATUS=$?"
```

Потом запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/neighbor_v36

uv run python -u scripts/sort_neighbor_v36.py
```

**Пока ничего не меняем в исходных данных.** V36 только создаст:

```text
output/neighbor_v36/sorted/
output/neighbor_v36/neighbor_decision.csv
```

После вывода пришли сюда результат. Особенно интересует блок `CHANGED`. Затем сравним V33 → V36 именно по тем **12 ошибкам**, которые уже нашли.

---

### 👤 **User** — 2026-08-15 14:46:40

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"
SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v36"
SORTED_DIR = OUTPUT_DIR / "sorted"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005

def normalize_id(x):
echo "STATUS=$?" py_compile scripts/sort_neighbor_v36.pyrs']}"========0
STATUS=0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/neighbor_v36

uv run python -u scripts/sort_neighbor_v36.py
================================================================================
NEIGHBOR CONTEXT V36
================================================================================
Input images : 256
Margin limit : 0.005
Neighbor logic : +1,+2 -> -1,-2
Neighbor match : TOP-2

================================================================================
RESULT
================================================================================
Total images:        256
Margin < 0.005:      5
Changed by neighbors:       0

DISTRIBUTION
--------------------------------------------------------------------------------
78      20
79       8
80       8
81      16
82       9
83      17
84       8
85      17
86      15
87      20
88      15
89      21
90       3
91      12
92      14
93      12
94      24
95      17
--------------------------------------------------------------------------------
TOTAL        256

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v36/sorted
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v36/neighbor_decision.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:46:41

Да, **V36 сработал именно так, как мы задумали для реальных `img_000...img_999`**:

- если `margin < 0.005` → фото считается сомнительным;
- сначала смотрим **следующие 2 фотографии**;
- если они подтверждают `TOP-2` → меняем на `TOP-2`;
- если подтверждается текущий кандидат → оставляем текущий;
- если впереди нет подтверждения → смотрим **предыдущие 2**;
- если и там нет подтверждения → оставляем исходный `TOP-1`.

Но на текущем тесте **0 изменений**, и это нормально: ни одна из 5 сомнительных фотографий не получила достаточного подтверждения по новой логике.

### Важный момент

Сейчас V36 проверял:

```text
Neighbor match : TOP-2
```

и результат:

```text
Margin < 0.005       5
Changed by neighbors 0
```

То есть **алгоритм не испортил исходные 256 результатов**:

```text
78  20
79   8
80   8
81  16
82   9
83  17
84   8
85  17
86  15
87  20
88  15
89  21
90   3
91  12
92  14
93  12
94  24
95  17
```

И это даже лучше предыдущего V35, который ошибочно изменил:

```text
Ленина125_11.JPG
84 -> 87
```

из-за того, что рядом в последовательности теста начиналась **другая серия**. Для реальных `img_000...img_999` такой проблемы действительно не будет: соседние кадры будут физически соседними фотографиями одной поездки/маршрута.

### Я бы сейчас закрепил V36 как базовую логику

И следующий тест сделать уже максимально близким к реальной работе:

```text
img_000.JPG
img_001.JPG
img_002.JPG
...
img_255.JPG
```

Причём **перемешивать фотографии не надо** — порядок кадров должен сохраниться.

Тогда мы сможем проверить главный сценарий:

> **одна фотография сомнительная → следующие 1–2 кадра подтверждают/не подтверждают кандидата → при необходимости смотрим назад.**

И отдельно я бы проверил **не только `margin < 0.005`, но и сами 5 сомнительных кадров**, потому что именно на них сейчас находится весь интерес алгоритма.

Итог текущего этапа: **V33 даёт 95.31% TOP-1, 99.22% TOP-2 и 100% TOP-5; V36 пока не ухудшил результат.**

---

### 👤 **User** — 2026-08-15 14:47:04

давай проверяем

---

### 🤖 **Assistant** — 2026-08-15 14:47:04

Да. Проверим V36 на **реальных именах `img_000...`**, но сначала сохраним текущий `test`, чтобы ничего не потерять. Затем переименуем копии, прогоним распознавание и V36, сравним распределение и решения.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== 1. BACKUP CURRENT TEST ==="

rm -rf data/input/test_img_backup
mkdir -p data/input/test_img_backup

cp -a data/input/test/. data/input/test_img_backup/

echo "BACKUP:"
find data/input/test_img_backup -maxdepth 1 -type f | wc -l

echo
echo "=== 2. RENAME TEST FILES TO img_000... ==="

rm -rf data/input/test_img
mkdir -p data/input/test_img

i=0

find data/input/test_img_backup -maxdepth 1 -type f -print0 |
sort -z |
while IFS= read -r -d '' f; do
    printf -v name "img_%03d.JPG" "$i"
    cp "$f" "data/input/test_img/$name"
    i=$((i+1))
done

echo "RENAMED:"
find data/input/test_img -maxdepth 1 -type f | wc -l

echo
echo "FIRST:"
find data/input/test_img -maxdepth 1 -type f | sort | head

echo
echo "LAST:"
find data/input/test_img -maxdepth 1 -type f | sort | tail
```

После этого проверим, что получилось ровно **256 файлов** и что номера идут последовательно.

Затем нужно будет сделать отдельный benchmark именно для `test_img`, чтобы V36 видел:

```text
img_000.JPG
img_001.JPG
img_002.JPG
...
```

а не старые названия серий. Это важно: **порядок фотографий сохранится, но информация об адресе из имени полностью исчезнет**, то есть распознавание будет работать в условиях, максимально близких к боевым.

---

### 👤 **User** — 2026-08-15 14:48:15

для img_xxx надо брать папку new

---

### 🤖 **Assistant** — 2026-08-15 14:48:16

Да, верно. **Для боевого теста `img_XXX` берём `data/input/new`, а `data/input/test` больше не трогаем.**

Причём лучше вообще не переименовывать оригиналы — сделаем отдельную копию `new` с именами `img_000.JPG ...`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SOURCE NEW ==="
find data/input/new -maxdepth 1 -type f | wc -l

echo
echo "=== CREATE IMG TEST FROM NEW ==="

rm -rf data/input/test_img
mkdir -p data/input/test_img

i=0

find data/input/new -maxdepth 1 -type f -print0 |
sort -z |
while IFS= read -r -d '' f; do
    ext="${f##*.}"
    printf -v name "img_%03d.%s" "$i" "$ext"
    cp "$f" "data/input/test_img/$name"
    i=$((i+1))
done

echo
echo "=== RESULT ==="
find data/input/test_img -maxdepth 1 -type f | wc -l

echo
echo "=== FIRST 10 ==="
find data/input/test_img -maxdepth 1 -type f | sort | head -10

echo
echo "=== LAST 10 ==="
find data/input/test_img -maxdepth 1 -type f | sort | tail -10
```

**Важно:** порядок берём из `sort` исходных имён `new`, поэтому последовательность кадров сохраняется относительно исходного набора.

После этого прогоняем **обычное V33 распознавание → V36 соседний алгоритм** и уже смотрим, как он ведёт себя на полностью обезличенных `img_XXX`.

---

### 👤 **User** — 2026-08-15 14:48:58

авай

---

### 🤖 **Assistant** — 2026-08-15 14:48:58

Давай. После создания `test_img` сначала проверим, что там действительно полный набор, затем запустим **V33 recognition** с теми же 18 fingerprint'ами.

```bash id="n3zj0e"
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== IMG TEST ==="
TOTAL=$(find data/input/test_img -maxdepth 1 -type f | wc -l)
echo "TOTAL: $TOTAL"

echo
echo "=== RUN V33 RECOGNITION ==="

rm -rf data/output/benchmark_img
mkdir -p data/output/benchmark_img

uv run scene-fingerprint recognize \
    data/input/test_img \
    --top-k 5 \
    --threshold 0.0 \
    --fingerprints $(printf "%s," {78..95} | sed 's/,$//' | sed 's/,/,/g' | sed 's/\([0-9][0-9]*\)/\1_v33/g') \
    --json \
    > data/output/benchmark_img/raw.json 2>&1

echo
echo "=== RECOGNITION STATUS ==="
echo "STATUS=$?"

echo
echo "=== RESULT COUNT ==="

uv run python - <<'PY'
import json
from pathlib import Path

p = Path("data/output/benchmark_img/raw.json")
text = p.read_text(encoding="utf-8", errors="replace")

decoder = json.JSONDecoder()
data = None

for i, ch in enumerate(text):
    if ch != "[":
        continue
    try:
        obj, _ = decoder.raw_decode(text[i:])
        if isinstance(obj, list):
            data = obj
            break
    except json.JSONDecodeError:
        pass

if data is None:
    print("JSON NOT FOUND")
    print(text[-3000:])
    raise SystemExit(1)

out = Path("data/output/benchmark_img/benchmark.json")

out.write_text(
    json.dumps(
        {
            "total": len(data),
            "results": data,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print("TOTAL:", len(data))
print("OUTPUT:", out)
PY
```

Но здесь есть **один момент**: если CLI не принимает такой способ формирования `--fingerprints`, остановимся на ошибке и поправим команду под фактический синтаксис CLI.

После успешного результата должно быть:

```text
TOTAL: 256
```

или сколько реально фотографий сейчас находится в `data/input/new`.

**Пока V36 не запускаем.** Сначала убеждаемся, что `img_XXX` полностью распознаны и `benchmark_img/benchmark.json` корректный. Потом на этот JSON запускаем V36.

---

### 👤 **User** — 2026-08-15 14:50:11

=== RUN V33 RECOGNITION ===

=== RECOGNITION STATUS ===
STATUS=0

=== RESULT COUNT ===
TOTAL: 256
OUTPUT: data/output/benchmark_img/benchmark.json

---

### 🤖 **Assistant** — 2026-08-15 14:50:12

Отлично. Теперь у нас есть **чистый боевой тест**:

- источник: `data/input/new`
- имена: `img_000...img_255`
- распознано: **256/256**
- V33: все 18 адресов
- исходные имена адресов полностью скрыты.

Теперь запускаем **V36 именно на этом результате**.

Сначала сделаем отдельную версию скрипта, которая читает `benchmark_img/benchmark.json`, чтобы случайно не использовать старый benchmark.

```bash id="v36img"
cd ~/projects/scene_fingerprint_mvp_v02

sed \
    -e 's#data/output/benchmark_v1/benchmark.json#data/output/benchmark_img/benchmark.json#' \
    -e 's#data/input/test#data/input/test_img#' \
    -e 's#output/neighbor_v36#output/neighbor_v36_img#' \
    scripts/sort_neighbor_v36.py \
    > scripts/sort_neighbor_v36_img.py

uv run python -m py_compile scripts/sort_neighbor_v36_img.py

rm -rf output/neighbor_v36_img

uv run python -u scripts/sort_neighbor_v36_img.py
```

Ожидаем увидеть:

```text
NEIGHBOR CONTEXT V36
Input images : 256
...
Changed by neighbors: ...
```

**Особенно пришли весь блок `CHANGED`**, если он появится.

Это будет уже гораздо более показательный тест: V36 будет видеть только:

```text
img_000
img_001
img_002
...
```

и не сможет использовать название адреса вообще.

---

### 👤 **User** — 2026-08-15 14:50:58

да

---

### 🤖 **Assistant** — 2026-08-15 14:50:58

Запускай именно эту команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed \
    -e 's#data/output/benchmark_v1/benchmark.json#data/output/benchmark_img/benchmark.json#' \
    -e 's#data/input/test#data/input/test_img#' \
    -e 's#output/neighbor_v36#output/neighbor_v36_img#' \
    scripts/sort_neighbor_v36.py \
    > scripts/sort_neighbor_v36_img.py

uv run python -m py_compile scripts/sort_neighbor_v36_img.py

rm -rf output/neighbor_v36_img

uv run python -u scripts/sort_neighbor_v36_img.py
```

Пришли вывод целиком, особенно:

```text
RESULT
CHANGED
DISTRIBUTION
```

После этого сравним **V33 против V36 на `img_XXX`** и решим, можно ли эту логику уже ставить в боевой сортировщик.

---

### 👤 **User** — 2026-08-15 14:51:10

================================================================================
NEIGHBOR CONTEXT V36
================================================================================
Input images : 256
Margin limit : 0.005
Neighbor logic : +1,+2 -> -1,-2
Neighbor match : TOP-2

================================================================================
RESULT
================================================================================
Total images:        256
Margin < 0.005:      5
Changed by neighbors:       0

DISTRIBUTION
--------------------------------------------------------------------------------
78      20
79       8
80       8
81      16
82       9
83      17
84       8
85      17
86      15
87      20
88      15
89      21
90       3
91      12
92      14
93      12
94      24
95      17
--------------------------------------------------------------------------------
TOTAL        256

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v36_img/sorted
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v36_img/neighbor_decision.csv

---

### 🤖 **Assistant** — 2026-08-15 14:51:11

Отлично. Это **хороший результат для V36**.

На реальном сценарии с обезличенными именами `img_XXX`:

- **256/256** фотографий распознаны.
- Только **5/256** имеют `margin < 0.005` — около **1,95%**.
- V36 **не сделал ни одного изменения**.
- То есть соседняя логика не внесла ложных коррекций.
- Распределение полностью совпало с исходным V33.

Но здесь есть важный вывод: **V36 пока не доказал свою полезность**, потому что на этих 5 сомнительных кадрах соседние фотографии не дали основания изменить решение.

### Следующий правильный тест

Нужно посмотреть эти 5 кадров и их соседей:

```bash id="q1m6pk"
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== V36 DECISIONS ==="

cat output/neighbor_v36_img/neighbor_decision.csv
```

И отдельно вывести для них:

```text
img_NNN
TOP1
TOP2
margin
+1
+2
-1
-2
```

**Именно это сейчас самое интересное.**

Потому что возможны два варианта:

1. `TOP1` действительно правильный, а V36 правильно ничего не меняет.
2. `TOP2` действительно правильный, но наша текущая логика недостаточно хорошо использует соседей.

После этого я бы сделал **V37**, где логика будет буквально такой, как ты описал:

> Сомнение → смотрим +1 и +2.  
> Если оба похожи на кандидата №2 → переключаемся.  
> Если один похож на №2, а второй на №1 → оставляем №1.  
> Если оба не подтверждают → смотрим −1 и −2.  
> Там та же логика.  
> Если подтверждения нет → оставляем TOP-1.

Причём для `img_XXX` это уже будет полностью независимая от имени файла последовательностная логика.

---

### 👤 **User** — 2026-08-15 14:51:41

echo "=== V36 DECISIONS ==="

cat output/neighbor_v36_img/neighbor_decision.csv
=== V36 DECISIONS ===
index,image,v33,second,final,margin,reason,forward_support,backward_support,forward_neighbors,backward_neighbors
0,img_000.JPG,85,93,85,0.06387112975120546,V33,0,0,,
1,img_001.JPG,85,93,85,0.0723714679479599,V33,0,0,,
2,img_002.JPG,85,94,85,0.06999923229217542,V33,0,0,,
3,img_003.JPG,85,91,85,0.06251606285572042,V33,0,0,,
4,img_004.JPG,85,91,85,0.05969446301460268,V33,0,0,,
5,img_005.JPG,85,91,85,0.0622074192762373,V33,0,0,,
6,img_006.JPG,85,93,85,0.07891240775585162,V33,0,0,,
7,img_007.JPG,89,85,89,0.010599901676177859,V33,0,0,,
8,img_008.JPG,85,94,85,0.03437144696712491,V33,0,0,,
9,img_009.JPG,85,92,85,0.08821490824222555,V33,0,0,,
10,img_010.JPG,85,91,85,0.08430003523826612,V33,0,0,,
11,img_011.JPG,85,91,85,0.08767408847808822,V33,0,0,,
12,img_012.JPG,85,93,85,0.08286674797534954,V33,0,0,,
13,img_013.JPG,85,94,85,0.09355650722980502,V33,0,0,,
14,img_014.JPG,85,94,85,0.08742140769958506,V33,0,0,,
15,img_015.JPG,85,91,85,0.08365918397903449,V33,0,0,,
16,img_016.JPG,85,91,85,0.08479376256465909,V33,0,0,,
17,img_017.JPG,85,93,85,0.06907860219478612,V33,0,0,,
18,img_018.JPG,95,78,95,0.05651606380939489,V33,0,0,,
19,img_019.JPG,95,94,95,0.0563689827919005,V33,0,0,,
20,img_020.JPG,95,94,95,0.026986816525459312,V33,0,0,,
21,img_021.JPG,95,94,95,0.05435425519943238,V33,0,0,,
22,img_022.JPG,95,78,95,0.021743475198745865,V33,0,0,,
23,img_023.JPG,95,78,95,0.04182479977607734,V33,0,0,,
24,img_024.JPG,95,94,95,0.03454017341136928,V33,0,0,,
25,img_025.JPG,95,94,95,0.01883472502231598,V33,0,0,,
26,img_026.JPG,95,94,95,0.05187192916870109,V33,0,0,,
27,img_027.JPG,95,94,95,0.05167678415775301,V33,0,0,,
28,img_028.JPG,95,94,95,0.05978727221488955,V33,0,0,,
29,img_029.JPG,95,94,95,0.01239921510219566,V33,0,0,,
30,img_030.JPG,95,94,95,0.05480723798274989,V33,0,0,,
31,img_031.JPG,95,94,95,0.032756130099296565,V33,0,0,,
32,img_032.JPG,95,94,95,0.04840520441532137,V33,0,0,,
33,img_033.JPG,95,94,95,0.06663363456726079,V33,0,0,,
34,img_034.JPG,82,86,82,0.08936476409435268,V33,0,0,,
35,img_035.JPG,82,80,82,0.12488261103630072,V33,0,0,,
36,img_036.JPG,82,86,82,0.12317003488540645,V33,0,0,,
37,img_037.JPG,82,86,82,0.12110040962696078,V33,0,0,,
38,img_038.JPG,82,86,82,0.12940170526504513,V33,0,0,,
39,img_039.JPG,82,86,82,0.12500931441783913,V33,0,0,,
40,img_040.JPG,82,86,82,0.12400702536106112,V33,0,0,,
41,img_041.JPG,82,80,82,0.13799159646034231,V33,0,0,,
42,img_042.JPG,82,86,82,0.137089718580246,V33,0,0,,
43,img_043.JPG,92,93,92,0.05051492810249347,V33,0,0,,
44,img_044.JPG,92,91,92,0.047920523285865824,V33,0,0,,
45,img_045.JPG,92,83,92,0.05877812504768376,V33,0,0,,
46,img_046.JPG,92,83,92,0.03764034926891324,V33,0,0,,
47,img_047.JPG,92,83,92,0.05397337138652791,V33,0,0,,
48,img_048.JPG,89,92,89,0.015478896498680061,V33,0,0,,
49,img_049.JPG,92,93,92,0.05804234206676484,V33,0,0,,
50,img_050.JPG,92,86,92,0.04284649729728707,V33,0,0,,
51,img_051.JPG,92,93,92,0.05486285686492931,V33,0,0,,
52,img_052.JPG,92,83,92,0.044789034724235455,V33,0,0,,
53,img_053.JPG,92,89,92,0.03018394887447362,V33,0,0,,
54,img_054.JPG,92,93,92,0.04552041172981247,V33,0,0,,
55,img_055.JPG,92,83,92,0.05383204936981201,V33,0,0,,
56,img_056.JPG,92,93,92,0.056275470852851894,V33,0,0,,
57,img_057.JPG,89,92,89,0.017843269109726112,V33,0,0,,
58,img_058.JPG,92,89,92,0.02601382851600642,V33,0,0,,
59,img_059.jpg,95,92,95,0.013838143944740255,V33,0,0,,
60,img_060.JPG,81,84,81,0.051434107422828834,V33,0,0,,
61,img_061.JPG,81,84,81,0.06633833229541763,V33,0,0,,
62,img_062.JPG,81,84,81,0.06660057008266462,V33,0,0,,
63,img_063.JPG,81,84,81,0.06172420978546134,V33,0,0,,
64,img_064.JPG,81,84,81,0.06294889509677892,V33,0,0,,
65,img_065.JPG,81,84,81,0.07533575773239143,V33,0,0,,
66,img_066.JPG,81,92,81,0.06899348437786124,V33,0,0,,
67,img_067.JPG,81,84,81,0.06563730657100675,V33,0,0,,
68,img_068.JPG,81,84,81,0.06519737899303435,V33,0,0,,
69,img_069.JPG,81,93,81,0.0362190854549409,V33,0,0,,
70,img_070.JPG,81,93,81,0.03870394885540018,V33,0,0,,
71,img_071.JPG,81,79,81,0.02880860924720763,V33,0,0,,
72,img_072.JPG,81,84,81,0.04398217141628291,V33,0,0,,
73,img_073.JPG,81,84,81,0.06721091687679293,V33,0,0,,
74,img_074.JPG,81,84,81,0.05667975723743435,V33,0,0,,
75,img_075.JPG,81,84,81,0.06430975556373597,V33,0,0,,
76,img_076.JPG,78,91,78,0.05727940678596488,V33,0,0,,
77,img_077.JPG,78,91,78,0.04950042128562937,V33,0,0,,
78,img_078.JPG,78,91,78,0.0516711926460266,V33,0,0,,
79,img_079.JPG,78,91,78,0.06546163737773891,V33,0,0,,
80,img_080.JPG,78,92,78,0.05452134072780612,V33,0,0,,
81,img_081.JPG,78,91,78,0.05292696595191959,V33,0,0,,
82,img_082.JPG,78,93,78,0.054639073610305844,V33,0,0,,
83,img_083.JPG,78,83,78,0.06760719180107133,V33,0,0,,
84,img_084.JPG,78,93,78,0.03889418363571173,V33,0,0,,
85,img_085.JPG,78,92,78,0.05619723021984102,V33,0,0,,
86,img_086.JPG,78,93,78,0.03258739650249487,V33,0,0,,
87,img_087.JPG,78,95,78,0.045886412858963,V33,0,0,,
88,img_088.JPG,78,91,78,0.05815510869026186,V33,0,0,,
89,img_089.JPG,78,95,78,0.04221824765205395,V33,0,0,,
90,img_090.JPG,78,83,78,0.03997324883937847,V33,0,0,,
91,img_091.JPG,78,91,78,0.058405218720436136,V33,0,0,,
92,img_092.JPG,78,92,78,0.057637195587158296,V33,0,0,,
93,img_093.JPG,78,83,78,0.05560545921325688,V33,0,0,,
94,img_094.JPG,78,95,78,0.04211333334445955,V33,0,0,,
95,img_095.JPG,78,92,78,0.0684369641542435,V33,0,0,,
96,img_096.jpg,80,82,80,0.13334024548530576,V33,0,0,,
97,img_097.JPG,80,82,80,0.14454219341278074,V33,0,0,,
98,img_098.JPG,80,79,80,0.0893909376859664,V33,0,0,,
99,img_099.JPG,80,79,80,0.06886896252632135,V33,0,0,,
100,img_100.JPG,80,82,80,0.0926139247417449,V33,0,0,,
101,img_101.JPG,80,82,80,0.0905121576786041,V33,0,0,,
102,img_102.JPG,80,91,80,0.10233256220817577,V33,0,0,,
103,img_103.JPG,80,79,80,0.06032289743423469,V33,0,0,,
104,img_104.JPG,79,92,79,0.05515181899070731,V33,0,0,,
105,img_105.JPG,79,92,79,0.028497468233108503,V33,0,0,,
106,img_106.JPG,79,87,79,0.07593260467052454,V33,0,0,,
107,img_107.JPG,79,87,79,0.07942694067955014,V33,0,0,,
108,img_108.JPG,79,87,79,0.08836044847965252,V33,0,0,,
109,img_109.JPG,79,92,79,0.07588721573352797,V33,0,0,,
110,img_110.JPG,79,87,79,0.09986575007438658,V33,0,0,,
111,img_111.JPG,79,87,79,0.07772250592708596,V33,0,0,,
112,img_112.JPG,84,87,84,0.023269945979118356,V33,0,0,,
113,img_113.JPG,87,84,87,0.0058522683382034035,V33,0,0,,
114,img_114.JPG,84,87,84,0.004841757416725212,FORWARD_CONFLICT_KEEP_V33,2,0,+1:img_115.JPG; +2:img_116.JPG,
115,img_115.JPG,87,84,87,0.0008131492137909424,FORWARD_CONFLICT_KEEP_V33,2,0,+1:img_116.JPG; +2:img_117.JPG,
116,img_116.JPG,84,87,84,0.0068208140134811135,V33,0,0,,
117,img_117.JPG,84,87,84,0.012004514336586114,V33,0,0,,
118,img_118.JPG,84,87,84,0.013807998299598556,V33,0,0,,
119,img_119.JPG,87,84,87,0.0009040278196335017,FORWARD_CONFLICT_KEEP_V33,2,0,+1:img_120.JPG; +2:img_121.JPG,
120,img_120.JPG,84,87,84,0.022543935775756863,V33,0,0,,
121,img_121.JPG,84,87,84,0.00894595265388487,V33,0,0,,
122,img_122.JPG,84,87,84,0.0029696345329284224,BACKWARD_CONFLICT_KEEP_V33,0,2,,-1:img_121.JPG; -2:img_120.JPG
123,img_123.JPG,88,92,88,0.15771589815616605,V33,0,0,,
124,img_124.JPG,88,92,88,0.11875754177570341,V33,0,0,,
125,img_125.JPG,88,87,88,0.10299944221973423,V33,0,0,,
126,img_126.JPG,88,92,88,0.16749849677085882,V33,0,0,,
127,img_127.JPG,88,92,88,0.12392415761947628,V33,0,0,,
128,img_128.JPG,88,86,88,0.07903994262218472,V33,0,0,,
129,img_129.JPG,88,92,88,0.11855103671550749,V33,0,0,,
130,img_130.JPG,88,87,88,0.1514065104722977,V33,0,0,,
131,img_131.JPG,88,80,88,0.13089976727962482,V33,0,0,,
132,img_132.JPG,88,92,88,0.1319566941261291,V33,0,0,,
133,img_133.JPG,88,82,88,0.1757854861021041,V33,0,0,,
134,img_134.JPG,88,89,88,0.058473131656646804,V33,0,0,,
135,img_135.JPG,88,92,88,0.1856327080726624,V33,0,0,,
136,img_136.JPG,88,89,88,0.06663685321807855,V33,0,0,,
137,img_137.JPG,88,92,88,0.11020316839218125,V33,0,0,,
138,img_138.JPG,89,92,89,0.07664183437824257,V33,0,0,,
139,img_139.JPG,89,80,89,0.12548595309257515,V33,0,0,,
140,img_140.JPG,89,80,89,0.10058635115623482,V33,0,0,,
141,img_141.JPG,89,94,89,0.024926116466522208,V33,0,0,,
142,img_142.JPG,89,92,89,0.06944957911968241,V33,0,0,,
143,img_143.JPG,89,85,89,0.07863187849521647,V33,0,0,,
144,img_144.JPG,89,93,89,0.11055969297885893,V33,0,0,,
145,img_145.JPG,89,93,89,0.10395597219467156,V33,0,0,,
146,img_146.JPG,89,92,89,0.04270372986793525,V33,0,0,,
147,img_147.JPG,94,89,94,0.007642631530761723,V33,0,0,,
148,img_148.JPG,89,92,89,0.06713824212551112,V33,0,0,,
149,img_149.JPG,89,92,89,0.06638831436634074,V33,0,0,,
150,img_150.JPG,89,86,89,0.08185622751712796,V33,0,0,,
151,img_151.JPG,89,94,89,0.08381820499897019,V33,0,0,,
152,img_152.JPG,89,93,89,0.10201574206352237,V33,0,0,,
153,img_153.JPG,89,92,89,0.05582035481929781,V33,0,0,,
154,img_154.JPG,90,89,90,0.10348871469497667,V33,0,0,,
155,img_155.JPG,90,89,90,0.026188015937805176,V33,0,0,,
156,img_156.JPG,89,90,89,0.021351562142372105,V33,0,0,,
157,img_157.JPG,90,89,90,0.022768219709396464,V33,0,0,,
158,img_158.JPG,89,90,89,0.026167194843292108,V33,0,0,,
159,img_159.JPG,86,82,86,0.09409466087818152,V33,0,0,,
160,img_160.JPG,86,92,86,0.08607355475425726,V33,0,0,,
161,img_161.JPG,86,94,86,0.07561085283756264,V33,0,0,,
162,img_162.JPG,86,95,86,0.07965811550617219,V33,0,0,,
163,img_163.JPG,86,95,86,0.08443728029727937,V33,0,0,,
164,img_164.JPG,86,82,86,0.07576295793056487,V33,0,0,,
165,img_165.JPG,86,89,86,0.00784715890884391,V33,0,0,,
166,img_166.JPG,86,82,86,0.03236340343952171,V33,0,0,,
167,img_167.JPG,86,78,86,0.08295942485332486,V33,0,0,,
168,img_168.JPG,86,82,86,0.06031382322311407,V33,0,0,,
169,img_169.JPG,86,94,86,0.11059969842433914,V33,0,0,,
170,img_170.JPG,86,78,86,0.0950364929437637,V33,0,0,,
171,img_171.JPG,86,92,86,0.09761417686939244,V33,0,0,,
172,img_172.JPG,86,92,86,0.07916835606098171,V33,0,0,,
173,img_173.JPG,83,91,83,0.04098260998725889,V33,0,0,,
174,img_174.JPG,83,91,83,0.03177075564861298,V33,0,0,,
175,img_175.JPG,83,91,83,0.03302323579788213,V33,0,0,,
176,img_176.JPG,83,91,83,0.03070852756500253,V33,0,0,,
177,img_177.JPG,83,93,83,0.03731345653533913,V33,0,0,,
178,img_178.JPG,83,92,83,0.051471405029296924,V33,0,0,,
179,img_179.JPG,83,91,83,0.03719182848930358,V33,0,0,,
180,img_180.JPG,83,91,83,0.04889068126678464,V33,0,0,,
181,img_181.JPG,83,92,83,0.03786159574985504,V33,0,0,,
182,img_182.JPG,83,91,83,0.011073499321937685,V33,0,0,,
183,img_183.JPG,83,81,83,0.018237356543541083,V33,0,0,,
184,img_184.JPG,83,93,83,0.04133761286735549,V33,0,0,,
185,img_185.JPG,83,93,83,0.03854508161544801,V33,0,0,,
186,img_186.JPG,83,93,83,0.032589153647422875,V33,0,0,,
187,img_187.JPG,83,93,83,0.03530693769454951,V33,0,0,,
188,img_188.JPG,83,93,83,0.038666583895683226,V33,0,0,,
189,img_189.JPG,83,91,83,0.049504097104072664,V33,0,0,,
190,img_190.JPG,94,93,94,0.01110450446605682,V33,0,0,,
191,img_191.JPG,94,95,94,0.061823999881744474,V33,0,0,,
192,img_192.JPG,94,91,94,0.08410342037677776,V33,0,0,,
193,img_193.JPG,94,85,94,0.06515230119228377,V33,0,0,,
194,img_194.JPG,94,91,94,0.03219431698322295,V33,0,0,,
195,img_195.JPG,94,85,94,0.06900491237640383,V33,0,0,,
196,img_196.JPG,94,91,94,0.060913925766944876,V33,0,0,,
197,img_197.JPG,94,91,94,0.05434495627880109,V33,0,0,,
198,img_198.JPG,94,91,94,0.047714905738830526,V33,0,0,,
199,img_199.JPG,94,95,94,0.05786375105381014,V33,0,0,,
200,img_200.JPG,94,95,94,0.07682474613189705,V33,0,0,,
201,img_201.JPG,94,91,94,0.06559846580028528,V33,0,0,,
202,img_202.JPG,94,91,94,0.044453635811805836,V33,0,0,,
203,img_203.JPG,94,95,94,0.019112910032272334,V33,0,0,,
204,img_204.JPG,94,95,94,0.06389893352985399,V33,0,0,,
205,img_205.JPG,94,91,94,0.040927788615226834,V33,0,0,,
206,img_206.JPG,94,91,94,0.0644290739297867,V33,0,0,,
207,img_207.JPG,94,91,94,0.0437808883190155,V33,0,0,,
208,img_208.JPG,94,95,94,0.062451746463775715,V33,0,0,,
209,img_209.JPG,94,91,94,0.04417139291763306,V33,0,0,,
210,img_210.JPG,94,91,94,0.04562346279621121,V33,0,0,,
211,img_211.JPG,94,92,94,0.015099996924400338,V33,0,0,,
212,img_212.JPG,94,92,94,0.020841539502143958,V33,0,0,,
213,img_213.JPG,86,89,86,0.006465049386024546,V33,0,0,,
214,img_214.JPG,89,88,89,0.004967231154441976,NO_NEIGHBOR_SUPPORT,0,0,,
215,img_215.JPG,91,92,91,0.04634948372840875,V33,0,0,,
216,img_216.JPG,91,92,91,0.05191995620727541,V33,0,0,,
217,img_217.JPG,91,94,91,0.04767797887325287,V33,0,0,,
218,img_218.JPG,91,93,91,0.009691809415817265,V33,0,0,,
219,img_219.JPG,91,83,91,0.050237198472023015,V33,0,0,,
220,img_220.JPG,91,93,91,0.061998027563095026,V33,0,0,,
221,img_221.JPG,91,93,91,0.029240424036979795,V33,0,0,,
222,img_222.JPG,91,93,91,0.022421183586120663,V33,0,0,,
223,img_223.JPG,91,92,91,0.04685847997665393,V33,0,0,,
224,img_224.JPG,91,85,91,0.035988532900810166,V33,0,0,,
225,img_225.JPG,91,93,91,0.040446101427078385,V33,0,0,,
226,img_226.JPG,91,93,91,0.017469892501831064,V33,0,0,,
227,img_227.JPG,93,91,93,0.051984501481056156,V33,0,0,,
228,img_228.JPG,93,91,93,0.04630861341953285,V33,0,0,,
229,img_229.JPG,93,92,93,0.03605422556400306,V33,0,0,,
230,img_230.JPG,93,91,93,0.049084411263465855,V33,0,0,,
231,img_231.JPG,93,92,93,0.03476601064205176,V33,0,0,,
232,img_232.JPG,93,92,93,0.04255214631557469,V33,0,0,,
233,img_233.JPG,93,92,93,0.044356696009635876,V33,0,0,,
234,img_234.JPG,93,83,93,0.04053391456604005,V33,0,0,,
235,img_235.JPG,93,92,93,0.03955932259559636,V33,0,0,,
236,img_236.JPG,93,95,93,0.019225502014160067,V33,0,0,,
237,img_237.JPG,93,92,93,0.036748434305190925,V33,0,0,,
238,img_238.JPG,93,92,93,0.030524402856826782,V33,0,0,,
239,img_239.JPG,87,85,87,0.0779498380422593,V33,0,0,,
240,img_240.JPG,87,85,87,0.06671746671199785,V33,0,0,,
241,img_241.JPG,87,85,87,0.06860884964466096,V33,0,0,,
242,img_242.JPG,87,79,87,0.07289833903312692,V33,0,0,,
243,img_243.JPG,87,79,87,0.04775323271751408,V33,0,0,,
244,img_244.JPG,87,92,87,0.014841661453246946,V33,0,0,,
245,img_245.JPG,87,92,87,0.06764192402362834,V33,0,0,,
246,img_246.JPG,87,85,87,0.07605030775070187,V33,0,0,,
247,img_247.JPG,87,92,87,0.06937198996543892,V33,0,0,,
248,img_248.JPG,87,79,87,0.03742801606655122,V33,0,0,,
249,img_249.JPG,87,79,87,0.05374292254447932,V33,0,0,,
250,img_250.JPG,87,79,87,0.034658710360527034,V33,0,0,,
251,img_251.JPG,87,79,87,0.04090701878070835,V33,0,0,,
252,img_252.JPG,87,79,87,0.0352832597494126,V33,0,0,,
253,img_253.JPG,87,81,87,0.04006370365619649,V33,0,0,,
254,img_254.JPG,87,92,87,0.08622642457485208,V33,0,0,,
255,img_255.JPG,87,83,87,0.08341791510581975,V33,0,0,,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---


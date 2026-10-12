## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 13:33:03

Вот это уже **очень полезный результат визуальной проверки**. Теперь можно оценивать не только margin, но и реальные ошибки.

### Что получилось по 89

В папке `89` нашли **3 фактические ошибки**:

| Файл | Было | Правильно |
|---|---:|---:|
| Стачки Зорге А (25).JPG | 89 | **92** |
| Малиновского 25 к Стачки А | 89 | **90** |
| Стачки пр-кт – Зорге… (10).JPG | 89 | **92** |

А среди `89_margin005`:

| Файл | Было | Правильно |
|---|---:|---:|
| Ленина Ашхабадский А (7) | 89 | **85** |
| Малиновского 25 к Стачки А (3) | 89 | **90** |
| Стачки Зорге А (25) | 89 | **92** |

То есть **2 из 3 ошибок 89 попали в margin < 0.005**.

Но есть ещё одна важная ошибка:

> `Ленина Ашхабадский А (7)` → 89, правильно 85

Она тоже попала в margin<0.005, причём это уже совершенно другой адрес.

---

### Что получилось по 92

В `92` обнаружились:

| Файл | Было | Правильно |
|---|---:|---:|
| `009.JPG` | 92 | **79** |
| `Комарова Добровольского А (1).JPG` | 92 | **79** |

То есть **2 ошибки внутри 18 фотографий**.

А в `92_margin005`:

- `008.JPG` → **79**
- `009.JPG` → **79**
- `Комарова Добровольского А (1).JPG` → **79**

Получается очень интересная вещь:

### Margin < 0.005 действительно хорошо ловит проблемные фотографии

По уже проверенному материалу:

- **89:** 3 ошибки, из них **2 пойманы margin <0.005**
- **92:** 2 ошибки, и они **попали в margin <0.005**
- плюс `008` тоже попал в margin<0.005 и оказался спорным `83 → 92`, но визуально правильным оказался **79**, то есть здесь вообще цепочка кандидатов требует отдельного разбора.

И это уже похоже не на случайность.

---

## Но я вижу ещё более важную закономерность

Ошибки очень часто возникают между **конкретными соседними адресами/похожими сценами**:

```text
89 ↔ 90 ↔ 92
92 ↔ 79
89 ↔ 85
```

То есть проблема не выглядит как:

> «DINO вообще не понимает фотографию».

Скорее:

> **система хорошо определяет визуальный кластер, но иногда путает соседние/похожие адреса внутри кластера.**

Именно поэтому идея с OCR, которую мы обсуждали раньше, здесь становится особенно сильной: **не надо гонять OCR по всем 262 фотографиям постоянно**. Его можно включать только как второй уровень для низкого margin.

### Я бы теперь зафиксировал такую архитектуру

```text
DINOv2 / v33
       ↓
TOP-1 + TOP-2
       ↓
margin
       │
       ├── margin >= 0.005
       │       ↓
       │    TOP-1
       │
       └── margin < 0.005
               ↓
          BEST / дополнительные признаки
               ↓
          если всё ещё спорно
               ↓
              OCR
               ↓
        номер адресной таблички
               ↓
        проверка по базе адресов
```

И главное — **OCR не должен заменять DINO**. Он должен быть именно механизмом разрешения конфликтов.

---

### Следующий шаг я бы сделал очень конкретным

Нам надо получить **все реальные ошибки среди 262**, а не только те, которые мы случайно нашли в 89 и 92.

Для этого можно сделать контрольный CSV:

```text
filename
predicted
visual_correct
margin
best_prediction
second_prediction
```

и вручную отметить правильный адрес для всех подозрительных групп.

Но перед этим я бы проверил **всю папку 90**, потому что там всего 3 фотографии. Если все три действительно `90`, это даст нам ещё один чистый контрольный кластер.

И отдельно я бы разобрал **79 ↔ 92** — сейчас это выглядит наиболее интересным конфликтом: `008`, `009` и `Комарова Добровольского (1)` система отправляет в 92, а визуально это 79.

---

### 👤 **User** — 2026-08-15 13:35:00

можно поступить немного проще: все фотографии , которые нужно распознавать идут обычно серией, т.е. при распознавании если есть сомнение - можно посмотреть на фото следущее или предыдущее и если оно похоже на второго кандидата - склоняться в его пользу

---

### 🤖 **Assistant** — 2026-08-15 13:35:01

Да. Это **намного проще и, главное, логичнее для нашего типа данных**.

У нас фотографии идут сериями одного рекламного места, поэтому соседние кадры дают дополнительный контекст. Я бы не стал усложнять сам DINOv2/слепки. Добавим **второй уровень принятия решения после обычного распознавания**.

### Как это будет работать

Сначала всё остается как сейчас:

**DINOv2 → кандидаты → best/first candidate**

А затем только для сомнительных случаев:

```text
margin < 0.005
        ↓
смотрим предыдущий и следующий кадр
        ↓
если соседний кадр уверенно относится ко 2-му кандидату
        ↓
переключаем текущий кадр на 2-го кандидата
```

Например:

```text
кадр 100 → 89 (0.801) / 92 (0.798)  ← сомнение
кадр 101 → 92 (0.91)  ← сосед
кадр 102 → 92 (0.90)  ← сосед

100 → 92
```

Но если:

```text
кадр 100 → 89 / 92
кадр 101 → 89
кадр 102 → 89

100 → 89
```

### Причём я бы сделал ещё лучше

Не просто смотреть на **один** соседний кадр, а на небольшое окно:

```text
предыдущий 2
предыдущий 1
ТЕКУЩИЙ
следующий 1
следующий 2
```

И учитывать только **уверенные** соседние распознавания.

Например:

```text
IMG 152   89   margin .083
IMG 153   89   margin .071
IMG 154   92   margin .002  ← сомнительный
IMG 155   89   margin .064
IMG 156   89   margin .091
```

Тогда `154` практически наверняка должен быть **89**, несмотря на минимальную разницу собственного score.

---

### Важный момент

Я бы **не применял это ко всем 262 фотографиям**.

Только:

```text
margin < 0.005
```

То есть сначала оставляем наши **7 сомнительных случаев**.

Получаем:

1. обычное распознавание → 255 кадров;
2. 7 кадров → соседний контекст;
3. из этих 7 принимаем решение;
4. остальные вообще не трогаем.

Это очень безопасный вариант.

---

### И ещё одно преимущество

Это может решить именно те случаи, которые мы сейчас вручную нашли:

- `008.JPG` — 83 ↔ 92
- Вавилова (63) — 86 ↔ 89
- Вавилова (70) — 88 ↔ 89
- Ленина — 84 ↔ 87
- Шеболдаева — 91 и т.д.
- Стачки/Зорге — 92/95

Причём **не нужно OCR, не нужно менять fingerprints и не нужно переобучать модель**.

Фактически мы используем информацию, которая уже есть в самой последовательности фотографирования.

### Я бы зафиксировал алгоритм v34 примерно так

```text
1. DINOv2 распознаёт все фотографии.
2. Для каждой сохраняем top-5.
3. Если margin >= 0.005:
       оставить best.
4. Если margin < 0.005:
       взять ±2 соседних кадра.
5. Посмотреть их top-1.
6. Если 2-й кандидат текущего кадра
   является уверенным кандидатом у соседей:
       отдать предпочтение 2-му.
7. Иначе:
       оставить best.
```

И обязательно сделать отчёт:

```text
image
original_best
candidate_2
original_margin
prev_1
prev_2
next_1
next_2
neighbor_vote
final_decision
reason
```

Тогда мы сможем **одним CSV увидеть, почему алгоритм перевёл конкретную фотографию**.

И я бы сейчас **не трогал текущий v33 вообще**. Сделаем отдельный `v34` поверх существующего результата, чтобы можно было напрямую сравнить:

**v33 → margin005 → margin005 + соседний контекст**

Это как раз тот случай, когда можно существенно улучшить сортировку, **не ломая уже хорошо работающую основную модель**.

---

### 👤 **User** — 2026-08-15 13:35:48

давай

---

### 🤖 **Assistant** — 2026-08-15 13:35:48

Да. Сделаем **отдельный эксперимент**, v33 не трогаем.

Сначала нам нужен точный порядок фотографий. Судя по именам, он может быть не всегда числовым, поэтому лучше использовать **порядок файлов в `data/input/test`**, а не пытаться сортировать по имени.

Создадим скрипт, который:

- берет существующий `margin_best.csv`;
- работает только с `margin < 0.005`;
- смотрит `±2` соседних файла;
- если второй кандидат текущего фото уверенно встречается у соседей — склоняется к нему;
- **не меняет решение**, если соседний контекст неубедителен;
- создает отдельную папку;
- сохраняет подробный `neighbor_decision.csv`.

Сначала выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v34.py <<'PY'
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
PY

chmod +x scripts/sort_neighbor_v34.py

echo
echo "=== RUN V34 ==="

uv run python scripts/sort_neighbor_v34.py
```

**Пока ничего из `output/78...95` не удаляем.**

После выполнения пришли сюда весь блок начиная с:

```text
RESULT
================================================================================
```

Особенно нужны строки:

```text
Margin < 0.005
Changed by neighbors
CHANGED
DISTRIBUTION
```

Тогда сравним **три решения**: исходный v33 → BEST → соседний контекст.

---

### 👤 **User** — 2026-08-15 13:36:30

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/visual_control_groups
mkdir -p output/visual_control_groups

for N in 89 90 92; do
    mkdir -p "output/visual_control_groups/$N"

    if [ -d "output/$N" ]; then
        cp -a "output/$N/." "output/visual_control_groups/$N/"
    fi

    if [ -d "output/visual_check_margin005/$N" ]; then
        mkdir -p "output/visual_control_groups/${N}_margin005"
        cp -a "output/visual_check_margin005/$N/." \
              "output/visual_control_groups/${N}_margin005/"
    fi
done

echo
echo "=== GROUPS ==="
find output/visual_control_groups -maxdepth 2 -type f | sort | sed -n '1,100p'

donefind "output/visual_control_groups/$N" -type f | wc -l

=== GROUPS ===
output/visual_control_groups/89_margin005/Ленина Ашхабадский А (7).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (17).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (1).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (26).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (6).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (7).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (11).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (25).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (28).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (2).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (32).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (47).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (4).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (5).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (6).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (8).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Стачки А (3).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Стачки А (5).JPG
output/visual_control_groups/89_margin005/Стачки Зорге А (25).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (17).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (1).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (26).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (6).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (7).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (11).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (25).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (28).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (2).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (32).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (47).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (4).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (5).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (6).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (8).JPG
output/visual_control_groups/89/Малиновского 25 к Стачки А (3).JPG
output/visual_control_groups/89/Малиновского 25 к Стачки А (5).JPG
output/visual_control_groups/89/Стачки Зорге А (25).JPG
output/visual_control_groups/89/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (10).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (1).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (2).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (4).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (1).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (2).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (4).JPG
output/visual_control_groups/92/009.JPG
output/visual_control_groups/92_margin005/008.JPG
output/visual_control_groups/92_margin005/009.JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (1).JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (42).JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (8).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (13).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (16).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (21).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (2).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (34).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (37).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (40).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (43).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (48).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (49).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (59).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (6).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (84).JPG
output/visual_control_groups/92/Комарова Добровольского А (1).JPG
output/visual_control_groups/92/Комарова Добровольского А (42).JPG
output/visual_control_groups/92/Комарова Добровольского А (8).JPG
output/visual_control_groups/92/Стачки Зорге А (13).JPG
output/visual_control_groups/92/Стачки Зорге А (16).JPG
output/visual_control_groups/92/Стачки Зорге А (21).JPG
output/visual_control_groups/92/Стачки Зорге А (2).JPG
output/visual_control_groups/92/Стачки Зорге А (34).JPG
output/visual_control_groups/92/Стачки Зорге А (37).JPG
output/visual_control_groups/92/Стачки Зорге А (40).JPG
output/visual_control_groups/92/Стачки Зорге А (43).JPG
output/visual_control_groups/92/Стачки Зорге А (48).JPG
output/visual_control_groups/92/Стачки Зорге А (49).JPG
output/visual_control_groups/92/Стачки Зорге А (59).JPG
output/visual_control_groups/92/Стачки Зорге А (6).JPG
output/visual_control_groups/92/Стачки Зорге А (84).JPG
output/visual_control_groups/92/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (18).JPG

=== COUNTS ===
----- 89 -----
19
----- 90 -----
3
----- 92 -----
18
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v34.py <<'PY'
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
uv run python scripts/sort_neighbor_v34.py)):4d}"-----------rt"-

=== RUN V34 ===
================================================================================
NEIGHBOR CONTEXT V34
================================================================================
Input images : 262
Recognition  : 262
Margin limit : 0.005
Neighbor ±   : 2

================================================================================
RESULT
================================================================================
Total images:        243
Margin < 0.005:      6
Changed by neighbors: 5

CHANGED
--------------------------------------------------------------------------------
008.JPG
    83_v33 -> 92_v33
    margin=0.001418
    second_supported_by_neighbors:+1:009.JPG
009.JPG
    92_v33 -> 83_v33
    margin=0.004476
    second_supported_by_neighbors:-1:008.JPG
Ленина 125-127 А (9).JPG
    84_v33 -> 87_v33
    margin=0.004802
    second_supported_by_neighbors:-1:Ленина 125-127 А (8).JPG, +1:Ленина 125-127 А (10).JPG
Ленина 125-127 А (10).JPG
    87_v33 -> 84_v33
    margin=0.001876
    second_supported_by_neighbors:-1:Ленина 125-127 А (9).JPG, +1:Ленина 125-127 А (11).JPG, +2:Ленина 125-127 А (12).JPG
Ленина 125-127 А (14).JPG
    87_v33 -> 84_v33
    margin=0.001037
    second_supported_by_neighbors:-2:Ленина 125-127 А (12).JPG, -1:Ленина 125-127 А (13).JPG, +1:Ленина 125-127 А (15).JPG, +2:Ленина 125-127 А (16).JPG

DISTRIBUTION
--------------------------------------------------------------------------------
78_v33       20
79_v33        8
80_v33        8
81_v33       16
82_v33        9
83_v33       18
84_v33        9
85_v33       17
86_v33       14
87_v33       13
88_v33       14
89_v33       19
90_v33        3
91_v33       10
92_v33       17
93_v33       11
94_v33       21
95_v33       16
--------------------------------------------------------------------------------
TOTAL       243

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v34
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v34/neighbor_decision.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:36:31

Да. Результат **v34 выглядит логично**, и главное — он подтверждает нашу гипотезу: последовательность фотографий действительно дает дополнительный сигнал.

Что произошло:

- Было **243** распознанных изображения.
- Сомнительных по `margin < 0.005` — **6**.
- Соседний контекст изменил **5** решений.
- Причём изменения не случайные: соседи образуют последовательные серии и поддерживают один и тот же адрес.

Особенно показательная серия:

**Ленина 125–127**
- `(9)` → `87`, потому что `(8)` и `(10)` поддерживают `87`
- `(10)` → `84`, поддержка с `(9)/(11)/(12)` фактически показывает, что здесь есть конфликт внутри самой серии
- `(14)` → `84`, и здесь уже очень сильная поддержка: `(12)`, `(13)`, `(15)`, `(16)` → `84`

То есть соседний алгоритм уже начинает работать как **контекстная коррекция**, а не просто как механическое изменение первого кандидата.

Но есть важный момент:

### `008` ↔ `009`

Получилось:

```text
008: 83 -> 92
009: 92 -> 83
```

Это означает, что алгоритм обнаружил **двунаправленную неоднозначность**. Он фактически поменял местами два изображения.

Это как раз тот случай, где нельзя просто сказать:

> «если сосед за второй кандидат — меняем».

Нужно учитывать **серийную устойчивость**. Если два соседних кадра взаимно поддерживают друг друга, это ещё не говорит, какой адрес правильный.

И вот здесь нам пригодится то, что ты предложил ранее: **смотреть не только на ±1, но на всю локальную серию**.

---

### Я бы сейчас сделал v35

Не усложняя систему DINO и не меняя сам алгоритм распознавания.

Логика:

1. Основной результат — `TOP-1`.
2. Смотрим только сомнительные кадры, например `margin < 0.005`.
3. Для каждого такого кадра смотрим **±3 фотографии** в исходной последовательности.
4. Считаем поддержку кандидатов.
5. Если:
   - второй кандидат поддерживается несколькими соседями → повышаем его;
   - первый кандидат также устойчиво поддерживается соседями → оставляем первый;
   - кандидаты образуют взаимную пару типа `83 ↔ 92` → **не меняем автоматически**, помечаем как `AMBIGUOUS_NEIGHBOR`.
6. Если соседний кандидат встречается уже **2–3 раза подряд**, это сильный сигнал.

То есть получится примерно:

```text
DINO TOP-1
    ↓
margin < 0.005 ?
    ↓ yes
смотрим ±3 соседей
    ↓
локальная серия
    ↓
 ┌───────────────┐
 │ явная победа  │ → изменить
 ├───────────────┤
 │ первый устойч │ → оставить
 ├───────────────┤
 │ 83 ↔ 92       │ → AMBIGUOUS
 └───────────────┘
```

**И самое важное:** я бы пока **не применял v34 как финальный сортировщик**. Сначала надо посмотреть эти 6 случаев визуально и сравнить их с реальными адресами. Особенно `008/009`.

Если визуальная проверка подтвердит, что соседний принцип правильно разрешает хотя бы 4–5 из этих случаев, тогда это уже очень хороший кандидат на **v35 как рабочую постобработку поверх v33**, без изменения самого DINO/fingerprint.

И ещё: я бы не трогал сейчас `89/90/92` вручную в основном алгоритме. Те ошибки, которые ты уже нашёл там, как раз являются хорошим материалом для проверки того, сможет ли **серийный контекст ±3** автоматически вытянуть их из неправильных групп.

---

### 👤 **User** — 2026-08-15 13:37:14

008: 83 -> 92
009: 92 -> 83 может быть так и нужно - какие им присовены номера?

---

### 🤖 **Assistant** — 2026-08-15 13:37:15

Да, вполне может быть. По текущему выводу мы видим только внутренние ID `83_v33` и `92_v33`, а **реальные номера/адреса, которые им соответствуют, нужно посмотреть в базе слепков**.

Для `008.JPG` и `009.JPG` предлагаю прямо сейчас вывести:

- какой адрес соответствует `83_v33`;
- какой адрес соответствует `92_v33`;
- какие исходные фотографии лежат в этих слепках;
- и, желательно, сравнить серию `008/009` с эталонными фотографиями 83 и 92.

Дай команду, которая выведет метаданные:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== 83_v33 ==="
cat data/fingerprints/83_v33/metadata.json

echo
echo "=== 92_v33 ==="
cat data/fingerprints/92_v33/metadata.json
```

Если `metadata.json` большой, лучше так:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
import json
from pathlib import Path

for n in [83, 92]:
    p = Path(f"data/fingerprints/{n}_v33/metadata.json")
    print("\n" + "="*80)
    print(n, p)
    print("="*80)

    data = json.loads(p.read_text(encoding="utf-8"))

    print(json.dumps(data, ensure_ascii=False, indent=2)[:8000])
PY
```

**Пришли вывод.** Тогда сразу скажу, что такое `83` и `92` по реальным адресам и имеет ли смысл перестановка `008 ↔ 009`.

---

### 👤 **User** — 2026-08-15 13:37:49

},
  "image_names": [
    "83_001.JPG",
    "83_002.JPG",
    "83_003.JPG",
    "83_004.JPG",
    "83_005.JPG",
    "83_006.JPG",
    "83_007.JPG",
    "83_008.JPG",
    "83_009.JPG",
    "83_010.JPG",
    "83_011.JPG",
    "83_012.JPG",
    "83_013.JPG",
    "83_014.JPG",
    "83_015.JPG",
    "83_016.JPG",
    "83_017.JPG",
    "83_018.JPG",
    "83_019.JPG",
    "83_020.JPG",
    "83_021.JPG",
    "83_022.JPG",
    "83_023.JPG",
    "83_024.JPG",
    "83_025.JPG",
    "83_026.JPG",
    "83_027.JPG",
    "83_028.JPG",
    "83_029.JPG",
    "83_030.JPG",
    "83_031.JPG",
    "83_032.JPG",
    "83_033.JPG",
    "83_034.JPG",
    "83_035.JPG",
    "83_036.JPG",
    "83_037.JPG",
    "83_038.JPG",
    "83_039.JPG",
    "83_040.JPG",
    "83_041.JPG",
    "83_042.JPG",
    "83_043.JPG",
    "83_044.JPG",
    "83_045.JPG",
    "83_046.JPG",
    "83_047.JPG",
    "83_048.JPG",
    "83_049.JPG",
    "83_050.JPG",
    "83_051.JPG",
    "83_052.JPG",
    "83_053.JPG",
    "83_054.JPG",
    "83_055.JPG",
    "83_056.JPG",
    "83_057.JPG",
    "83_058.JPG",
    "83_059.JPG",
    "83_060.JPG",
    "83_061.JPG",
    "83_062.JPG",
    "83_063.JPG",
    "83_064.JPG",
    "83_065.JPG",
    "83_066.JPG",
    "83_067.JPG",
    "83_068.JPG"
  ]
}

================================================================================
92 data/fingerprints/92_v33/metadata.json
================================================================================
{
  "id": "92_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 57,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "92_001.JPG",
    "92_002.JPG",
    "92_003.JPG",
    "92_004.JPG",
    "92_005.JPG",
    "92_006.JPG",
    "92_007.JPG",
    "92_008.JPG",
    "92_009.JPG",
    "92_010.JPG",
    "92_011.JPG",
    "92_012.JPG",
    "92_013.JPG",
    "92_014.JPG",
    "92_015.JPG",
    "92_016.JPG",
    "92_017.JPG",
    "92_018.JPG",
    "92_019.JPG",
    "92_020.JPG",
    "92_021.JPG",
    "92_022.JPG",
    "92_023.JPG",
    "92_024.JPG",
    "92_025.JPG",
    "92_026.JPG",
    "92_027.JPG",
    "92_028.JPG",
    "92_029.JPG",
    "92_030.JPG",
    "92_031.JPG",
    "92_032.JPG",
    "92_033.JPG",
    "92_034.JPG",
    "92_035.JPG",
    "92_036.JPG",
    "92_037.JPG",
    "92_038.JPG",
    "92_039.JPG",
    "92_040.JPG",
    "92_041.JPG",
    "92_042.JPG",
    "92_043.JPG",
    "92_044.JPG",
    "92_045.JPG",
    "92_046.JPG",
    "92_047.JPG",
    "92_048.JPG",
    "92_049.JPG",
    "92_050.JPG",
    "92_051.JPG",
    "92_052.JPG",
    "92_053.JPG",
    "92_054.JPG",
    "92_055.JPG",
    "92_056.JPG",
    "92_057.JPG"
  ]
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:37:50

Да, теперь видно только количество эталонных фотографий: **83 = 68 фото**, **92 = 57 фото**. Но в `metadata.json` адреса не записаны — ID `83` и `92` сами по себе адреса не раскрывают.

Зато у нас уже есть важная информация: в тестовой выборке `008` и `009` — соседние кадры, и алгоритм v34 получил:

- `008`: **83 → 92**
- `009`: **92 → 83**

Это очень похоже на ситуацию, когда два соседних кадра действительно относятся к **одному месту**, но DINO колеблется между двумя похожими слепками.

### Давай установим реальные адреса 83 и 92

Скорее всего, они есть в исходных каталогах `data/input/83` и `data/input/92`, либо в названии задания/папки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== 83 ==="
find data/input/83 -maxdepth 1 -type f | head -5

echo
echo "=== 92 ==="
find data/input/92 -maxdepth 1 -type f | head -5

echo
echo "=== SEARCH 83 / 92 IN PROJECT ==="
grep -RIl \
  --exclude-dir=.venv \
  --exclude='*.npy' \
  --exclude='*.index' \
  -E '83_v33|92_v33' . | head -50
```

Но ещё лучше — **посмотреть непосредственно фотографии 83 и 92**, особенно если это две близкие точки.

Можно сразу собрать по 8 представителей из каждого слепка:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json
import shutil

OUT = Path("output/compare_83_92")
shutil.rmtree(OUT, ignore_errors=True)

for n in [83, 92]:
    meta = Path(f"data/fingerprints/{n}_v33/metadata.json")
    data = json.loads(meta.read_text(encoding="utf-8"))

    names = data["image_names"]

    src_dir = Path(f"data/input/{n}")
    dst_dir = OUT / str(n)
    dst_dir.mkdir(parents=True)

    # первые 8 + середина + последние
    indices = list(range(min(5, len(names))))
    mid = len(names) // 2
    indices += [mid]
    indices += list(range(max(0, len(names)-3), len(names)))

    seen = set()

    for i in indices:
        name = names[i]

        if name in seen:
            continue
        seen.add(name)

        src = src_dir / name

        if src.exists():
            shutil.copy2(src, dst_dir / name)

print("Created:", OUT)
PY

find output/compare_83_92 -type f | sort
```

После этого можно будет визуально сравнить:

```text
output/compare_83_92/83/
output/compare_83_92/92/
```

**Но я бы сначала получил реальные названия 83 и 92.** Потому что если, например, окажется, что `83` — один адрес, а `92` — другой, который физически находится рядом, тогда `008/009` — очень хороший тест для нашей идеи последовательного распознавания.

---

### 👤 **User** — 2026-08-15 13:39:13

до Margins 005.  фото 008 лпределялось правильно

---

### 🤖 **Assistant** — 2026-08-15 13:39:13

Да — это **очень важный факт**.

Если **до введения `margin < 0.005` + соседней коррекции**:

```text
008.JPG → 83
009.JPG → 92
```

и визуально/по исходному тесту это было правильно, то **v34 здесь ошибочно переиграл правильный результат**:

```text
008: 83 → 92   ❌
009: 92 → 83   ❌
```

То есть проблема не в DINO v33, а именно в нашей новой логике соседей.

### Что это нам показывает

Нельзя делать правило:

> «если сосед поддерживает второй кандидат — меняем».

Потому что в серии могут быть **два разных адреса подряд**.

Именно `008/009` это прекрасно демонстрируют:

```text
... предыдущие кадры → 83
008 → 83
009 → 92
следующие кадры → вероятно 92
```

А наш алгоритм увидел только локальную взаимную поддержку:

```text
008 ↔ 009
83  ↔ 92
```

и ошибочно решил, что надо поменять оба.

### Поэтому я предлагаю изменить принцип

**v33 остаётся главным решением.**

Соседний контекст имеет право **только подтвердить или очень осторожно исправить** результат.

Причём исправление разрешаем только если:

1. `margin < 0.005`;
2. второй кандидат поддерживается соседями;
3. **нет признака перехода между двумя сериями**;
4. соседние фотографии по обе стороны не подтверждают разные адреса.

Для `008/009` получится:

```text
008
v33 → 83
сосед 009 → 92
       ↓
конфликт
       ↓
НЕ МЕНЯЕМ
       ↓
008 = 83

009
v33 → 92
сосед 008 → 83
       ↓
конфликт
       ↓
НЕ МЕНЯЕМ
       ↓
009 = 92
```

То есть **v33 сохраняет исходное правильное решение**.

---

И ещё более важный вывод: **margin 0.005 слишком агрессивно использовать как самостоятельный критерий для пересортировки**.

Он отлично подходит для определения:

> «это сомнительный кадр, его стоит проверить».

Но не обязательно:

> «его надо автоматически переопределить».

Я бы сейчас сделал **v35 = v33 + соседний контекст только как подтверждающий сигнал**, без автоматического переворота при простом совпадении с одним соседом.

И тогда уже отдельно посмотрим на те случаи, которые ты нашёл:

- Вавилова 63 → 86/89
- Вавилова 70 → 88/89
- Ленина 125–127 → 84/87
- Шеболдаева 95 → 91
- Стачки–Зорге 20 → 95
- 008/009 → 83/92

Это будет гораздо надёжнее.

---

### 👤 **User** — 2026-08-15 13:40:02

да

---

### 🤖 **Assistant** — 2026-08-15 13:40:03

Да. Тогда **v35 строим поверх v33**, а соседей используем только как дополнительный сигнал, **не как безусловную замену первого кандидата**.

Главное правило:

> **Если v33 уверенно выбрал первый кандидат — не трогаем. Если margin < 0.005 — смотрим на соседей. Но если соседние кадры сами расходятся, оставляем исходный v33.**

Для `008/009` это сохранит правильную пару **83 / 92**.

Следующим шагом я бы сделал v35 и прогнал те же 262 фотографии, чтобы получить список **только тех случаев, где новая логика реально предлагает изменить v33**.

---

### 👤 **User** — 2026-08-15 13:40:42

да. можнол 35 вресию прогнать на всем, чтобы обнаружить возможные новые ошибки

---

### 🤖 **Assistant** — 2026-08-15 13:40:42

Да. Это как раз правильный следующий тест: **v35 прогоняем на всех 262**, но ничего не перезаписываем в основной `output`. Получим отдельную папку и полный отчёт: что v35 оставил как v33, что изменил и почему.

Сделаем v35 с безопасным правилом:

- базовое решение = `v33`;
- `margin >= 0.005` → **не меняем**;
- `margin < 0.005` → смотрим соседей ±2;
- если соседний контекст однозначно поддерживает второго кандидата → можно изменить;
- если соседние кадры конфликтуют между собой → **оставляем v33**;
- `008/009` должны остаться **83 / 92**;
- основной `output/` не трогаем.

Сначала создай скрипт:

**document: **

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v35.py <<'PY'
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
            rows.append(row)

    return rows

def get_id(row, field):
    value = row.get(field)
    if value:
        return value.replace("_v33", "")
    return None

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_rows()

    # --------------------------------------------------
    # Только реальные исходные фотографии
    # --------------------------------------------------

    rows = [
        r for r in rows
        if (INPUT_DIR / r["image"]).exists()
    ]

    # --------------------------------------------------
    # Порядок фотографий
    # --------------------------------------------------

    index_by_name = {
        r["image"]: i
        for i, r in enumerate(rows)
    }

    decisions = []
    changed = []
    counters = Counter()

    for i, row in enumerate(rows):

        image = row["image"]

        current = get_id(row, "current_first")
        second = get_id(row, "current_second")

        margin = float(row["final_margin"])

        final_id = current
        reason = "V33"

        neighbor_support = Counter()
        neighbor_names = []

        # --------------------------------------------------
        # Уверенный v33 результат
        # --------------------------------------------------

        if margin >= MARGIN_LIMIT:
            reason = "V33_MARGIN_OK"

        else:

            # --------------------------------------------------
            # Смотрим соседей
            # --------------------------------------------------

            start = max(0, i - NEIGHBOR_RADIUS)
            end = min(len(rows), i + NEIGHBOR_RADIUS + 1)

            for j in range(start, end):

                if j == i:
                    continue

                neighbor = rows[j]

                n_current = get_id(
                    neighbor,
                    "current_first"
                )

                if not n_current:
                    continue

                distance = j - i

                # Нас интересует только поддержка
                # второго кандидата.
                if n_current == second:
                    neighbor_support[second] += 1

                    sign = "+" if distance > 0 else "-"
                    neighbor_names.append(
                        f"{sign}{abs(distance)}:{neighbor['image']}"
                    )

            # --------------------------------------------------
            # Безопасная смена
            #
            # Меняем только если второй кандидат
            # получает поддержку минимум от 2 соседей.
            #
            # Если есть хотя бы один сосед,
            # подтверждающий текущий кандидат,
            # считаем ситуацию конфликтной.
            # --------------------------------------------------

            current_support = 0

            for j in range(start, end):

                if j == i:
                    continue

                neighbor = rows[j]

                n_current = get_id(
                    neighbor,
                    "current_first"
                )

                if n_current == current:
                    current_support += 1

            second_support = neighbor_support[second]

            if (
                second
                and second_support >= 2
                and current_support == 0
            ):
                final_id = second
                reason = (
                    "NEIGHBOR_SECOND_STRONG"
                )

            elif (
                second
                and second_support >= 1
                and current_support > 0
            ):
                reason = (
                    "CONFLICT_KEEP_V33"
                )

            elif second:
                reason = (
                    "WEAK_NEIGHBOR_KEEP_V33"
                )

            else:
                reason = "NO_SECOND"

        # --------------------------------------------------
        # Counters
        # --------------------------------------------------

        counters[final_id] += 1

        # --------------------------------------------------
        # Change record
        # --------------------------------------------------

        if final_id != current:

            changed.append({
                "image": image,
                "from": current,
                "to": final_id,
                "margin": margin,
                "second_support": neighbor_support[second],
                "neighbors": "; ".join(neighbor_names),
                "reason": reason,
            })

        decisions.append({
            "image": image,
            "v33": current,
            "second": second,
            "final": final_id,
            "margin": margin,
            "neighbor_second_support":
                neighbor_support[second]
                if second else 0,
            "neighbor_current_support":
                current_support
                if margin < MARGIN_LIMIT
                else 0,
            "reason": reason,
            "neighbors": "; ".join(neighbor_names),
        })

    # --------------------------------------------------
    # Sort images
    # --------------------------------------------------

    for row in decisions:

        image = row["image"]
        folder = row["final"]

        if not folder:
            folder = "NO_CANDIDATE"

        dst_dir = OUTPUT_DIR / folder
        dst_dir.mkdir(parents=True, exist_ok=True)

        src = INPUT_DIR / image
        dst = dst_dir / src.name

        if dst.exists():

            stem = dst.stem
            suffix = dst.suffix
            n = 2

            while True:

                candidate = (
                    dst_dir
                    / f"{stem}__{n}{suffix}"
                )

                if not candidate.exists():
                    dst = candidate
                    break

                n += 1

        shutil.copy2(src, dst)

    # --------------------------------------------------
    # Report
    # --------------------------------------------------

    fields = [
        "image",
        "v33",
        "second",
        "final",
        "margin",
        "neighbor_second_support",
        "neighbor_current_support",
        "reason",
        "neighbors",
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
    # Console report
    # --------------------------------------------------

    print("=" * 80)
    print("NEIGHBOR CONTEXT V35")
    print("=" * 80)

    print(f"Input images : {len(rows)}")
    print(f"Margin limit : {MARGIN_LIMIT}")
    print(f"Neighbor ±   : {NEIGHBOR_RADIUS}")

    print()
    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(f"Total images:        {len(rows)}")

    low_margin = sum(
        1
        for r in decisions
        if r["margin"] < MARGIN_LIMIT
    )

    print(f"Margin < 0.005:      {low_margin}")
    print(f"Changed by neighbors:{len(changed):8d}")

    if changed:

        print()
        print("CHANGED")
        print("-" * 80)

        for c in changed:

            print(c["image"])
            print(
                f"    {c['from']} -> {c['to']}"
            )
            print(
                f"    margin={c['margin']:.6f}"
            )
            print(
                f"    second_support="
                f"{c['second_support']}"
            )
            print(
                f"    reason={c['reason']}"
            )

            if c["neighbors"]:
                print(
                    f"    neighbors="
                    f"{c['neighbors']}"
                )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for n in range(78, 96):

        key = str(n)

        print(
            f"{key:10s} {counters[key]:4d}"
        )

    print("-" * 80)
    print(
        f"TOTAL       "
        f"{sum(counters.values()):4d}"
    )

    print()
    print("OUTPUT:")
    print("  sorted :", OUTPUT_DIR)
    print("  report :", REPORT_CSV)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/sort_neighbor_v35.py

echo
echo "=== RUN V35 ==="

uv run python scripts/sort_neighbor_v35.py
```

**Важный момент:** я специально поставил для автоматического изменения порог **минимум 2 соседних кадра**, и при конфликте с текущим кандидатом v33 оставляем v33.

После запуска пришли сюда **весь блок `RESULT` + `CHANGED` + `DISTRIBUTION`**. По нему уже сравним v33 → v34 → v35 и поймём, действительно ли соседний контекст улучшает распознавание.

---

### 👤 **User** — 2026-08-15 13:41:21

давай в нормально й разметке

---

### 🤖 **Assistant** — 2026-08-15 13:41:22

Да. Сделаем без writing-блока — обычным текстом, чтобы команду можно было сразу копировать в терминал.

И я бы **чуть изменил логику v35**: не будем требовать двух соседей безоговорочно. Для серий фотографий важнее определить, **к какому кандидату относится сама последовательность**. При этом `008 → 92, 009 → 83` не надо автоматически менять, потому что v33 уже дал им разные адреса и это может быть реальной границей/переходом.

Сейчас лучше сначала сделать безопасный v35, который **ничего не меняет в основном output** и только показывает предложения.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v35.py <<'PY'
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
PY

chmod +x scripts/sort_neighbor_v35.py

rm -rf output/visual_check_neighbor_v35

uv run python scripts/sort_neighbor_v35.py
```

### Что сейчас проверяем

У нас есть **262 фотографии**, из них реально распознаваемых по CSV было 243.

v33 дал:

- 7 случаев с `margin < 0.005`;
- 3 изменения через BEST;
- затем v34 с соседями дал 5 изменений, но среди них появились подозрительные:

```text
008: 83 -> 92
009: 92 -> 83
```

что выглядит как **обмен двух соседних кадров**, а не исправление.

Поэтому v35 должен быть осторожнее.

Особенно нас интересуют:

```text
008
009

Ленина 125-127 А (9)
Ленина 125-127 А (10)
Ленина 125-127 А (14)

Вавилова ... (63)
Вавилова ... (70)

Шеболдаева 95 А (8)

Стачки ... (20)

и вся группа 89 / 90 / 92
```

После запуска пришли **только вывод начиная с `RESULT` и до `OUTPUT`**. Тогда посмотрим, какие новые ошибки v35 обнаружил на всём массиве и стоит ли вообще применять соседний контекст автоматически.

---

### 👤 **User** — 2026-08-15 13:42:17

uv run python scripts/sort_neighbor_v35.pybors']}"--------------
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/sort_neighbor_v35.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:42:19

Да, это моя ошибка в предыдущей команде: похоже, при копировании heredoc в терминал часть скрипта исказилась, поэтому `uv run` фактически ничего не вывел.

Не будем сейчас переделывать всю логику. Сначала проверим, что реально записалось в файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== FILE ==="
wc -l scripts/sort_neighbor_v35.py
echo

echo "=== FIRST 40 ==="
sed -n '1,40p' scripts/sort_neighbor_v35.py
echo

echo "=== LAST 40 ==="
tail -40 scripts/sort_neighbor_v35.py
echo

echo "=== SYNTAX ==="
uv run python -m py_compile scripts/sort_neighbor_v35.py
echo "EXIT=$?"
```

Если синтаксис нормальный, сразу проверим, почему `main()` не запускается:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python -u scripts/sort_neighbor_v35.py
echo "EXIT=$?"
```

**Пришли весь вывод этих двух команд.** После этого я дам короткую исправленную v35, без повторного огромного блока.

---

### 👤 **User** — 2026-08-15 13:42:31

eighbor_v35.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== FILE ==="
wc -l scripts/sort_neighbor_v35.py
echo

echo "=== FIRST 40 ==="
sed -n '1,40p' scripts/sort_neighbor_v35.py
echo

echo "=== LAST 40 ==="
tail -40 scripts/sort_neighbor_v35.py
echo

echo "=== SYNTAX ==="
uv run python -m py_compile scripts/sort_neighbor_v35.py
echo "EXIT=$?"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:42:32

Понял. Здесь вообще **нет вывода даже от `echo`**, значит команда, скорее всего, не была выполнена целиком — терминал получил обрезанный/повреждённый ввод. Не будем мучить heredoc.

Сделаем проще: сначала одной короткой командой проверим файл.

Скопируй **только это**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && ls -lh scripts/sort_neighbor_v35.py && wc -l scripts/sort_neighbor_v35.py
```

Потом:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && uv run python -u scripts/sort_neighbor_v35.py; echo EXIT=$?
```

Пришли результат второй команды.

Если снова будет абсолютно пусто — тогда уже понятно, что проблема не в v35, а в том, как терминал принимает вставленный многострочный текст, и я дам вариант создания скрипта через `cat` в максимально безопасном виде.

---

### 👤 **User** — 2026-08-15 13:42:54

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && ls -lh scripts/sort_neighbor_v35.py && wc -l scripts/sort_neighbor_v35.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && uv run python -u scripts/sort_neighbor_v35.py; echo EXIT=$?
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:42:55

Да, теперь причина очевидна: **команды вообще не исполняются**. Даже `cd ... && ls ...` не даёт ни `ls`, ни `wc`, ни `EXIT`. Это не проблема Python/v35.

Похоже, терминал сейчас находится в состоянии, где введённые команды не передаются shell нормально. Давай сначала проверим самым примитивным способом.

Выполни **одну строку**, без копирования большого блока:

```bash
echo TEST
```

Если увидишь:

```text
TEST
```

следом выполни:

```bash
pwd
```

и затем:

```bash
ls
```

Если `echo TEST` тоже ничего не выдаст, **не запускай пока никакие скрипты** — будем восстанавливать состояние терминала.

---

### 👤 **User** — 2026-08-15 13:43:13

пусто

---

### 🤖 **Assistant** — 2026-08-15 13:43:13

Да — тогда проблема **точно не в `v35` и не в Python**. Shell сейчас не выполняет ввод. При этом приглашение `alexice@NEURO:...$` появляется, поэтому сначала восстановим терминал.

### 1. Нажми `Ctrl+C`

После этого **вручную набери** (не вставляй):

```bash
echo TEST
```

Если снова пусто — попробуй:

```bash
reset
```

После `reset` экран может очиститься — это нормально.

### 2. Затем снова вручную:

```bash
echo TEST
```

Должно появиться:

```text
TEST
```

### 3. Если всё ещё пусто

Нажми:

**Ctrl+D**

Это закроет текущую shell-сессию. Если ты работаешь в обычном терминале Ubuntu, появится новый prompt или терминал завершит shell.

Если закрылся — открой новый терминал и выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
echo TEST
```

---

**Пока ничего не создаём и v35 не запускаем.** Сначала добьёмся, чтобы `echo TEST` реально вывел `TEST`. После этого продолжим с v35.

---

### 👤 **User** — 2026-08-15 13:43:28

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo TEST
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo TEST
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:43:28

Да, теперь картина ясная. **Команда выполняется, но stdout не отображается.** Поэтому это уже не проблема `v35`.

При этом shell возвращает prompt, то есть команды проходят.

Проверим, куда вообще делся вывод. Выполни:

```bash
echo TEST > /tmp/test_echo.txt
cat /tmp/test_echo.txt
```

Если `cat` тоже ничего не покажет, проверим stderr:

```bash
echo ERROR >&2
```

И самое важное — статус команды:

```bash
echo TEST
echo "STATUS=$?"
```

Если увидим только:

```text
STATUS=0
```

значит stdout терминала каким-то образом подавляется.

### Быстрый способ проверить

Выполни:

```bash
printf '\033[0mHELLO\n'
```

Если **HELLO тоже не видно**, попробуй:

```bash
stty sane
```

и затем:

```bash
echo TEST
```

Если и после этого пусто, **не надо пока трогать проект**. Мы восстановим нормальный вывод терминала, после чего сразу проверим `sort_neighbor_v35.py`.

И да: сам факт, что prompt возвращается после каждой команды, говорит о том, что `echo`, скорее всего, действительно запускается — просто его вывод сейчас не виден.

---

### 👤 **User** — 2026-08-15 13:43:43

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo TEST > /tmp/test_echo.txt
cat /tmp/test_echo.txt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:43:44

Да, теперь видно важную вещь: **проблема уже не в `sort_neighbor_v35.py`**.

Если даже

```bash
echo TEST
```

ничего не выводит, а приглашение shell появляется снова, значит терминал сейчас **не отображает stdout вообще** или команда фактически не выполняется так, как ожидается.

Давай сначала восстановим нормальный вывод терминала. Выполни **одной командой**:

```bash
printf '\033c'; stty sane; echo "=== TERMINAL TEST ==="; printf 'HELLO\n'; pwd; printf 'DONE\n'
```

Если снова будет пусто — попробуй:

```bash
reset
```

и затем:

```bash
echo HELLO
```

### Если `echo HELLO` всё ещё пустой

Проверим, не перенаправлен ли stdout:

```bash
echo HELLO >&2
```

Если **это покажет `HELLO`**, значит stdout терминала сломан/перенаправлен.

Тогда:

```bash
exec 1>/dev/tty
exec 2>/dev/tty
echo "STDOUT RESTORED"
```

И снова:

```bash
echo TEST
```

### После восстановления

Пока **не запускаем v35**. Сначала проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
echo "PROJECT OK"
ls -lh scripts/sort_neighbor_v35.py
wc -l scripts/sort_neighbor_v35.py
```

Должно появиться примерно:

```text
PROJECT OK
-rw-r--r-- ... scripts/sort_neighbor_v35.py
XXX scripts/sort_neighbor_v35.py
```

После этого уже нормально проверим сам файл и **запустим v35 на всех 243 распознанных фотографиях**, причем я бы сделал результат именно в нормальной разметке:

- `78`
- `79`
- ...
- `95`

а не `78_v33`, `79_v33` и т.д.;
- отдельно `CHANGED`;
- отдельно CSV с исходным кандидатом, новым решением, margin и соседями;
- отдельно список **всех случаев, где соседний контекст изменил решение**.

И главное: с учётом нашего вывода по `008/009` я бы **не разрешал v35 автоматически менять уверенные решения**. Соседний контекст должен работать только как корректор **сомнительных кадров**, а не как самостоятельный классификатор.

---

### 👤 **User** — 2026-08-15 13:44:23

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo HELLO
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo HELLO >&2
HELLO
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:44:24

Отлично, теперь причина установлена: **stdout перенаправлен/потерян, а stderr работает**. Поэтому все наши `echo`, `ls`, Python `print()` и обычный вывод скриптов были невидимы.

Восстановим stdout:

```bash
exec 1>/dev/tty
```

Потом сразу:

```bash
echo HELLO
```

Должно появиться:

```text
HELLO
```

После этого проверим:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
echo "=== CHECK ==="
ls -lh scripts/sort_neighbor_v35.py
wc -l scripts/sort_neighbor_v35.py
```

**Не запускай пока v35.** Пришли этот вывод. Затем продолжим с нормальной v35-разметкой на всех 243 фотографиях.

---

### 👤 **User** — 2026-08-15 13:44:51

HELLO
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02
echo "=== CHECK ==="
ls -lh scripts/sort_neighbor_v35.py
wc -l scripts/sort_neighbor_v35.py
=== CHECK ===
-rwxrwxr-x 1 alexice alexice 9.1K Aug 15 13:41 scripts/sort_neighbor_v35.py
437 scripts/sort_neighbor_v35.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:44:52

Отлично. Теперь терминал исправлен, и файл `v35` существует — **437 строк**, то есть проблема была только в пропавшем stdout.

Но прежде чем запускать его, я бы сделал ещё одну проверку: поскольку файл получился довольно большой, убедимся, что в нём действительно есть `main()` и запуск.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== MAIN ==="
grep -n "def main\|if __name__" scripts/sort_neighbor_v35.py

echo
echo "=== SYNTAX ==="
uv run python -m py_compile scripts/sort_neighbor_v35.py
echo "STATUS=$?"
```

Если получим `STATUS=0`, сразу запускаем:

```bash
uv run python -u scripts/sort_neighbor_v35.py
```

Теперь вывод уже должен быть виден.

**И важный момент:** если v35 снова покажет `008: 83 → 92` и `009: 92 → 83`, это не будем автоматически считать исправлением. У нас уже есть важный факт: **до neighbor-логики `008` правильно определялся как 83**. Поэтому эти два кадра нужно рассматривать как отдельную последовательность и проверить, действительно ли соседний контекст помогает, а не просто перекидывает метки между двумя кадрами.

---

### 👤 **User** — 2026-08-15 13:45:10

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== MAIN ==="
grep -n "def main\|if __name__" scripts/sort_neighbor_v35.py

echo
echo "=== SYNTAX ==="
uv run python -m py_compile scripts/sort_neighbor_v35.py
echo "STATUS=$?"
=== MAIN ===
46:def main():
436:if __name__ == "__main__":

=== SYNTAX ===
STATUS=0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== MAIN ==="
grep -n "def main\|if __name__" scripts/sort_neighbor_v35.py

echo
echo "=== SYNTAX ==="
uv run python -m py_compile scripts/sort_neighbor_v35.py
echo "STATUS=$?"
=== MAIN ===
46:def main():
436:if __name__ == "__main__":

=== SYNTAX ===
STATUS=0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:45:11

Отлично. `v35` синтаксически исправен, `main()` есть. Теперь запускаем его на всём наборе.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/visual_check_neighbor_v35

uv run python -u scripts/sort_neighbor_v35.py
```

Должен появиться отчёт примерно такого вида:

```text
================================================================================
NEIGHBOR CONTEXT V35
================================================================================
Input images : 243
Margin limit : 0.005
Neighbor +/- : 2

================================================================================
RESULT
================================================================================
...
```

### Что особенно хочу увидеть

Пришли весь вывод начиная с:

```text
RESULT
```

и до:

```text
OUTPUT:
```

Особенно интересуют строки `CHANGED`.

После этого сравним **v33 → v34 → v35** и решим, какую именно соседнюю логику оставить для рабочего распознавания. Главное — не будем автоматически портить уже правильные результаты ради нескольких сомнительных кадров.

---

### 👤 **User** — 2026-08-15 13:45:30

DISTRIBUTION
--------------------------------------------------------------------------------
78           20
79            8
80            8
81           16
82            9
83           18
84           10
85           17
86           14
87           12
88           14
89           19
90            3
91           10
92           17
93           11
94           21
95           16
--------------------------------------------------------------------------------
TOTAL        243

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v35
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v35/neighbor_decision.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:45:31

Да. По распределению уже видно важное: **v35 не развалил общую картину** — все 243 изображения распределены по 78–95, без пропавших кадров.

Но нам сейчас нужно понять **что именно v35 изменил**, потому что распределение само по себе этого не показывает.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== V35 CHANGES ==="
grep -A8 -B2 "CHANGED" \
  output/visual_check_neighbor_v35/neighbor_decision.csv \
  | head -100
```

Но лучше сразу получить нормальную сводку из CSV:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv
from pathlib import Path

p = Path("output/visual_check_neighbor_v35/neighbor_decision.csv")

with p.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print("TOTAL ROWS:", len(rows))
print()

changed = []
for r in rows:
    old = r.get("original_id") or r.get("current_id") or r.get("assigned_id")
    new = r.get("final_id") or r.get("neighbor_id") or r.get("assigned_id")

    if old != new:
        changed.append(r)

print("CHANGED:", len(changed))
print("=" * 100)

for r in changed:
    print(r)
PY
```

Если названия колонок в нашем v35 другие, команда просто покажет их не так, как нужно. Тогда выполним:

```bash
head -2 output/visual_check_neighbor_v35/neighbor_decision.csv
```

и я сразу дам правильную команду.

### Что я уже вижу

Распределение v35:

| Адрес | v35 |
|---:|---:|
| 78 | 20 |
| 79 | 8 |
| 80 | 8 |
| 81 | 16 |
| 82 | 9 |
| 83 | 18 |
| 84 | 10 |
| 85 | 17 |
| 86 | 14 |
| 87 | 12 |
| 88 | 14 |
| 89 | 19 |
| 90 | 3 |
| 91 | 10 |
| 92 | 17 |
| 93 | 11 |
| 94 | 21 |
| 95 | 16 |
| **Всего** | **243** |

Самое интересное — **83 стало 18, 84 стало 10, 87 стало 12, 92 стало 17**. Это как раз те группы, где у нас были спорные кадры.

Следующий шаг — посмотреть список `CHANGED`. **Пока v35 в рабочую логику не внедряем.** Сначала сравним каждое изменение с исходным v33 и с тем, что мы уже вручную установили для спорных серий.

---


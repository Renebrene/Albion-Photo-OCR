## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 12:20:19

Да. Здесь уже виден **довольно важный результат**.

### 1. BEST действительно полезен, но не как большой вес

На всём тесте:

| Вариант | 84_v33 | Изменения относительно CURRENT |
|---|---:|---:|
| A_CURRENT | 8 | — |
| B_BEST_02 | 9 | 1 |
| C_BEST_05 | 10 | 2 |
| D_BEST_10 | 11 | 3 |
| E_BEST_15 | 11 | 3 |
| F_BEST_20 | 11 | 3 |

Причём у нас есть **три конкретных случая**, где BEST меняет решение с `87` на `84`:

```text
(10)  87 → 84 начиная с BEST 0.05
(14)  87 → 84 уже при BEST 0.02
(8)   87 → 84 начиная с BEST 0.10
```

Это очень похоже на то, что мы наблюдали визуально.

---

## 2. Но есть ещё более интересный момент

При увеличении BEST:

```text
0.02 → 0.05 → 0.10
```

количество побед `84` растёт:

```text
8 → 9 → 10 → 11
```

А затем:

```text
0.10 → 0.15 → 0.20
```

**ничего больше не меняется.**

То есть на этом наборе:

> **BEST=0.10 уже достиг насыщения.**

Увеличивать его до `0.15` или `0.20` смысла пока не видно.

---

# Но я бы пока НЕ ставил BEST=0.10

Есть одна проблема.

Мы сейчас считаем:

```text
BEST = максимальная похожесть фотографии
         из всего fingerprint
```

Это очень сильный сигнал.

И если в fingerprint случайно есть фотография, которая похожа по ракурсу/освещению/сезону, `BEST` может подтянуть **неправильный адрес**.

Поэтому я бы сделал следующий эксперимент.

### Не просто BEST, а BEST с ограничением

Например:

```text
FINAL =
0.70 G
+ 0.20 E
+ 0.07 C
+ 0.03 S
+ 0.05 BEST
```

но только если:

```text
BEST - G > X
```

То есть BEST должен **существенно превосходить средний глобальный результат**.

Например:

```text
BEST=0.948
G=0.879

разница = +0.069
```

Это очень убедительный сигнал.

А если:

```text
BEST=0.894
G=0.888

разница = +0.006
```

то BEST почти ничего нового не сообщает.

---

## И вот это может оказаться очень хорошей логикой

Я бы вообще рассматривал не просто:

```text
BEST
```

а:

```text
BEST_DELTA = BEST - G
```

Потому что `G` и `BEST` сейчас сильно связаны.

В твоём примере:

### 84

```text
G    = 0.8792
BEST = 0.9476

DELTA = +0.0684
```

### 87

```text
G    = 0.8883
BEST = 0.8938

DELTA = +0.0055
```

Вот это **очень сильный аргумент в пользу 84**.

Глобальный centroid говорит:

> «87 немного больше похож в среднем».

А BEST говорит:

> «У 84 есть конкретная фотография, которая очень сильно похожа на текущую».

Это принципиально разные виды информации.

---

# Предлагаю следующий эксперимент

Не трогать пока основной алгоритм.

Сделать отдельный benchmark:

```text
A  CURRENT
B  BEST 0.02
C  BEST 0.05

D  BEST_DELTA 0.05
E  BEST_DELTA 0.10
E  BEST_DELTA 0.15
```

Где:

```text
BEST_DELTA = max(0, BEST - G)
```

И формула, например:

```text
FINAL =
0.70 G
+ 0.20 E
+ 0.07 C
+ 0.03 S
+ 0.10 BEST_DELTA
```

с нормализацией весов.

Тогда мы увидим, что лучше:

**абсолютный BEST**

или

**насколько BEST лучше среднего представления адреса.**

И я подозреваю, что **BEST_DELTA будет интереснее**, потому что он отвечает именно на вопрос:

> «Есть ли внутри этого адреса конкретная фотография, очень похожая на текущую?»

А это именно то, что нам нужно для сложных случаев вроде `87 vs 84`.

Если хочешь, следующим шагом я дам готовую замену benchmark-скрипта, которая прогонит **оба варианта BEST и BEST_DELTA одновременно** и отдельно покажет случаи, где они меняют победителя.

---

### 👤 **User** — 2026-08-15 12:21:43

давай

---

### 🤖 **Assistant** — 2026-08-15 12:21:44

Да. Сделаем **следующий чистый эксперимент**, основной алгоритм пока не трогаем.

Добавим:

- `A_CURRENT` — текущая формула.
- `B_BEST_02`
- `C_BEST_05`
- `D_BEST_10`
- `E_BESTDELTA_02`
- `F_BESTDELTA_05`
- `G_BESTDELTA_10`
- `H_BESTDELTA_15`
- `I_BESTDELTA_20`

Где:

```text
BEST_DELTA = max(0, BEST - G)
```

И отдельно в результатах будем видеть:

```text
G
BEST
DELTA
FINAL
```

### 1. Создаём новый benchmark

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/benchmark_best_delta.py <<'PY'
from pathlib import Path
import sys
import csv
import numpy as np
from collections import Counter

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.scene_analyzer import SceneAnalyzer, CompactDescriptor
from app.core.image import image_files

INPUT = Path("data/input/test")

FINGERPRINTS = [
    f"{n}_v33"
    for n in range(78, 96)
]

TOP_K = 5

# ============================================================
# EXPERIMENTS
# ============================================================

WEIGHT_SETS = {

    # Current algorithm
    "A_CURRENT": {
        "mode": "best",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.00,
    },

    # Absolute BEST
    "B_BEST_02": {
        "mode": "best",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.02,
    },

    "C_BEST_05": {
        "mode": "best",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.05,
    },

    "D_BEST_10": {
        "mode": "best",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.10,
    },

    # BEST - G
    "E_DELTA_02": {
        "mode": "delta",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.02,
    },

    "F_DELTA_05": {
        "mode": "delta",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.05,
    },

    "G_DELTA_10": {
        "mode": "delta",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.10,
    },

    "H_DELTA_15": {
        "mode": "delta",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.15,
    },

    "I_DELTA_20": {
        "mode": "delta",
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.20,
    },
}

# ============================================================
# INIT
# ============================================================

settings = Settings()

embedder = SceneEmbedder(settings)

manager = FingerprintManager(
    settings,
    embedder,
)

analyzer = SceneAnalyzer(
    embedder,
    manager,
)

# ============================================================
# LOAD
# ============================================================

print("=" * 100)
print("LOADING FINGERPRINTS")
print("=" * 100)

loaded = {}

for fp_id in FINGERPRINTS:

    try:
        data = manager.load(fp_id)
        loaded[fp_id] = data
        print(f"{fp_id:<12} OK")

    except Exception as exc:
        print(
            f"{fp_id:<12} ERROR: {exc}"
        )

print()
print(
    f"Loaded: {len(loaded)} fingerprints"
)

# ============================================================
# INPUT
# ============================================================

paths = image_files(INPUT)

print()
print("=" * 100)
print("INPUT")
print("=" * 100)
print(
    f"Images: {len(paths)}"
)

if not paths:
    print("ERROR: no images")
    sys.exit(1)

# ============================================================
# DINO
# ============================================================

print()
print("=" * 100)
print("DINO EMBEDDINGS")
print("=" * 100)

queries = embedder.embed_paths(paths)

queries = np.asarray(
    queries,
    dtype=np.float32,
)

if queries.ndim == 1:
    queries = queries.reshape(1, -1)

# ============================================================
# OUTPUT
# ============================================================

output = Path(
    "output/benchmark_best_delta"
)

output.mkdir(
    parents=True,
    exist_ok=True,
)

txt_file = output / "results.txt"
csv_file = output / "results.csv"
changes_file = output / "winner_changes.txt"

# ============================================================
# SCORE
# ============================================================

def calculate_score(
    item,
    weights,
):

    if weights["mode"] == "delta":

        best_signal = max(
            0.0,
            item["BEST"] - item["G"],
        )

    else:

        best_signal = item["BEST"]

total_weight = (
        weights["G"]
        + weights["E"]
        + weights["C"]
        + weights["S"]
        + weights["B"]
    )

    score = (
        weights["G"] * item["G"]
        + weights["E"] * item["E"]
        + weights["C"] * item["C"]
        + weights["S"] * item["S"]
        + weights["B"] * best_signal
    )

    return float(
        score / total_weight
    )

# ============================================================
# CSV
# ============================================================

csv_header = [
    "image",
    "weight_set",
    "rank",
    "id",
    "final",
    "G",
    "E",
    "C",
    "S",
    "BEST",
    "DELTA",
    "best_image",
]

# ============================================================
# PROCESS
# ============================================================

all_results = []

with txt_file.open(
    "w",
    encoding="utf-8",
) as out, csv_file.open(
    "w",
    encoding="utf-8",
    newline="",
) as csv_out:

    writer = csv.writer(
        csv_out
    )

    writer.writerow(
        csv_header
    )

for index, (
        path,
        query_global,
    ) in enumerate(
        zip(paths, queries),
        1,
    ):

        print()
        print(
            f"[{index}/{len(paths)}] "
            f"{path.name}"
        )

        out.write(
            "\n"
            + "=" * 110
            + "\n"
        )

        out.write(
            f"IMAGE: {path.name}\n"
        )

# ----------------------------------------------------
        # DESCRIPTORS
        # ----------------------------------------------------

        image = CompactDescriptor._load(
            Path(path)
        )

        (
            query_environment,
            query_color,
            query_spatial,
        ) = CompactDescriptor.all_from_image(
            image
        )

# ----------------------------------------------------
        # COMPONENTS
        # ----------------------------------------------------

        components = []

        for fingerprint_id, data in loaded.items():

            try:

                G = analyzer.cosine(
                    query_global,
                    data["centroid"],
                )

                image_scores = (
                    data["embeddings"]
                    @ query_global
                )

                best_index = int(
                    np.argmax(image_scores)
                )

                BEST = float(
                    image_scores[best_index]
                )

                image_names = (
                    data["metadata"]
                    .get(
                        "image_names",
                        [],
                    )
                )

                if (
                    best_index
                    < len(image_names)
                ):
                    best_image = (
                        image_names[
                            best_index
                        ]
                    )
                else:
                    best_image = str(
                        best_index
                    )

E = analyzer.descriptor_similarity(
                    query_environment,
                    data[
                        "environment_embeddings"
                    ],
                )

                C = analyzer.descriptor_similarity(
                    query_color,
                    data[
                        "color_embeddings"
                    ],
                )

                S = analyzer.descriptor_similarity(
                    query_spatial,
                    data[
                        "spatial_embeddings"
                    ],
                )

DELTA = max(
                    0.0,
                    BEST - G,
                )

components.append(
                    {
                        "id": fingerprint_id,
                        "G": float(G),
                        "E": float(E),
                        "C": float(C),
                        "S": float(S),
                        "BEST": float(BEST),
                        "DELTA": float(DELTA),
                        "best_image": best_image,
                    }
                )

            except Exception as exc:

                print(
                    f"ERROR "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

# ----------------------------------------------------
        # WEIGHT SETS
        # ----------------------------------------------------

        for weight_name, weights in (
            WEIGHT_SETS.items()
        ):

            ranked = []

            for item in components:

                final = calculate_score(
                    item,
                    weights,
                )

                row = dict(item)

                row["final"] = final

                ranked.append(row)

ranked.sort(
                key=lambda x: x["final"],
                reverse=True,
            )

top = ranked[:TOP_K]

            winner = (
                top[0]["id"]
                if top
                else "NONE"
            )

print(
                f"  {weight_name:<14}"
                f" {winner:<10}"
                f" {top[0]['final']:.6f}"
                if top
                else
                f"  {weight_name:<14} NONE"
            )

out.write(
                "\n"
                f"[{weight_name}]\n"
            )

for rank, item in enumerate(
                top,
                1,
            ):

                line = (
                    f"{rank}. "
                    f"{item['id']:<10} "
                    f"FINAL={item['final']:.6f} "
                    f"G={item['G']:.6f} "
                    f"E={item['E']:.6f} "
                    f"C={item['C']:.6f} "
                    f"S={item['S']:.6f} "
                    f"BEST={item['BEST']:.6f} "
                    f"DELTA={item['DELTA']:.6f} "
                    f"IMG={item['best_image']}"
                )

                out.write(
                    line + "\n"
                )

writer.writerow(
                    [
                        path.name,
                        weight_name,
                        rank,
                        item["id"],
                        f"{item['final']:.6f}",
                        f"{item['G']:.6f}",
                        f"{item['E']:.6f}",
                        f"{item['C']:.6f}",
                        f"{item['S']:.6f}",
                        f"{item['BEST']:.6f}",
                        f"{item['DELTA']:.6f}",
                        item["best_image"],
                    ]
                )

all_results.append(
                {
                    "image": path.name,
                    "weight_set": weight_name,
                    "winner": winner,
                    "score": (
                        top[0]["final"]
                        if top
                        else 0.0
                    ),
                }
            )

# ============================================================
# WINNER SUMMARY
# ============================================================

with txt_file.open(
    "a",
    encoding="utf-8",
) as out:

    out.write(
        "\n\n"
        + "=" * 110
        + "\n"
        + "WINNER SUMMARY"
        + "\n"
        + "=" * 110
        + "\n"
    )

for weight_name in WEIGHT_SETS:

        winners = [
            r["winner"]
            for r in all_results
            if r["weight_set"]
            == weight_name
        ]

        counts = Counter(
            winners
        )

        out.write(
            f"\n{weight_name}\n"
        )

        for fp, count in (
            counts.most_common()
        ):

            out.write(
                f"  {fp:<12}"
                f" {count:4d}\n"
            )

# ============================================================
# WINNER CHANGES
# ============================================================

images = sorted(
    set(
        r["image"]
        for r in all_results
    )
)

with changes_file.open(
    "w",
    encoding="utf-8",
) as out:

    out.write(
        "=" * 110
        + "\n"
        + "WINNER CHANGES"
        + "\n"
        + "=" * 110
        + "\n"
    )

for image in images:

        winners = {}

        for r in all_results:

            if r["image"] == image:

                winners[
                    r["weight_set"]
                ] = r["winner"]

current = winners.get(
            "A_CURRENT"
        )

        changed = []

        for weight_name, winner in (
            winners.items()
        ):

            if (
                weight_name
                != "A_CURRENT"
                and winner
                != current
            ):

                changed.append(
                    f"{weight_name}={winner}"
                )

if changed:

            out.write(
                f"\n{image}\n"
            )

            out.write(
                f"  CURRENT = "
                f"{current}\n"
            )

            for value in changed:

                out.write(
                    f"  {value}\n"
                )

print()
print("=" * 100)
print("DONE")
print("=" * 100)
print(
    f"TXT:     {txt_file}"
)
print(
    f"CSV:     {csv_file}"
)
print(
    f"CHANGES: {changes_file}"
)
PY

uv run python /tmp/benchmark_best_delta.py
```

### После окончания

Сначала покажи сводку:

```bash
cat output/benchmark_best_delta/results.txt | \
sed -n '/WINNER SUMMARY/,$p'
```

и затем:

```bash
cat output/benchmark_best_delta/winner_changes.txt
```

Особенно нас интересует, **не станет ли `DELTA` лучше абсолютного `BEST`**.

Если окажется, например:

```text
A_CURRENT       8 побед 84
BEST_05        10
BEST_10        11

DELTA_05       12
DELTA_10       14
DELTA_15       14
DELTA_20       13
```

это будет уже очень хороший сигнал, что надо вводить именно **относительный best-сигнал**, а не просто увеличивать вес `BEST`.

И ещё важный момент: **пока ничего не меняем в `scene_analyzer.py` и `recognizer.py`**. Мы сначала собираем экспериментальные данные, а потом уже выберем формулу.

---

### 👤 **User** — 2026-08-15 12:23:19

WINNER CHANGES
==============================================================================================================

Ленина 125-127 А (10).JPG
  CURRENT = 87_v33
  C_BEST_05=84_v33
  D_BEST_10=84_v33
  F_DELTA_05=84_v33
  G_DELTA_10=84_v33
  H_DELTA_15=84_v33
  I_DELTA_20=84_v33

Ленина 125-127 А (14).JPG
  CURRENT = 87_v33
  B_BEST_02=84_v33
  C_BEST_05=84_v33
  D_BEST_10=84_v33
  E_DELTA_02=84_v33
  F_DELTA_05=84_v33
  G_DELTA_10=84_v33
  H_DELTA_15=84_v33
  I_DELTA_20=84_v33

Ленина 125-127 А (8).JPG
  CURRENT = 87_v33
  D_BEST_10=84_v33
  G_DELTA_10=84_v33
  H_DELTA_15=84_v33
  I_DELTA_20=84_v33

---

### 🤖 **Assistant** — 2026-08-15 12:23:20

Да. Здесь уже видно **важную закономерность**.

### Что показывают три проблемных кадра

Во всех трёх случаях:

- `CURRENT` → ошибочно выбирает **87**
- правильный адрес → **84**
- как только мы усиливаем `BEST` или учитываем отрыв `BEST` от `GLOBAL`, **84 начинает выигрывать**.

Особенно показательно:

| Фото | CURRENT | BEST | DELTA |
|---|---|---|---|
| (10) | 87 | 84 | 84 |
| (14) | 87 | 84 | 84 |
| (8) | 87 | 84 | 84 |

Причём это не просто случайный эффект весов. Посмотрим на `(10)`:

- **87:** G = 0.8883, BEST = 0.8938
- **84:** G = 0.8792, BEST = **0.9476**

То есть текущая логика говорит:

> «87 лучше по центральному DINO embedding».

А `BEST` говорит:

> **«У 84 есть конкретный снимок, очень похожий на текущую фотографию».**

И разница здесь огромная:

**84: 0.9476 vs 87: 0.8938**

Это +0.054.

---

### Я бы пока НЕ увеличивал просто вес BEST

Это важно.

Мы сейчас видим, что `BEST` — хороший **сигнал коррекции**, но не обязательно хороший основной компонент.

Я бы сделал следующий механизм:

```text
GLOBAL → основной кандидат
        ↓
если GLOBAL уверенный → доверяем GLOBAL
        ↓
если GLOBAL близок к второму кандидату
        ↓
смотрим BEST
        ↓
если BEST сильно лучше у второго кандидата
        ↓
переключаем кандидата
```

То есть **BEST использовать условно**, а не постоянно.

Например:

```text
если best_score - second_score < 0.02:
    включить BEST-коррекцию
```

И дополнительно:

```text
если BEST сильно выше GLOBAL:
    повысить приоритет кандидата
```

---

### Почему это выглядит перспективно

У нас уже есть естественная структура:

```text
G = сходство с центроидом адреса
BEST = сходство с конкретной фотографией адреса
E = окружение
C = цвет
S = пространственная структура
```

И они отвечают на разные вопросы.

**G:**
> Насколько эта фотография похожа на типичную фотографию адреса?

**BEST:**
> Есть ли среди фотографий этого адреса конкретный очень похожий кадр?

Для реального проекта второй вопрос может быть **очень полезен**, потому что один адрес может иметь несколько совершенно разных ракурсов.

---

### Но есть ещё более интересный вариант

Я бы проверил не только:

```text
BEST
```

а:

```text
BEST - GLOBAL
```

Например `(10)`:

**84**

```text
BEST - G
0.9476 - 0.8792 = +0.0684
```

**87**

```text
0.8938 - 0.8883 = +0.0055
```

Это очень сильный признак.

У 84 конкретный снимок **аномально хорошо совпадает** с запросом относительно среднего представления адреса.

Можно сделать:

```text
DELTA = BEST - GLOBAL
```

и использовать его как отдельный сигнал.

---

### Следующий эксперимент

Я бы сейчас **не трогал DINO и не увеличивал размер fingerprint**.

Сделаем эксперимент с четырьмя вариантами:

```text
CURRENT
BEST
DELTA = BEST - GLOBAL
BEST + DELTA
```

Причём для `DELTA` попробуем несколько весов:

```text
DELTA_02
DELTA_05
DELTA_10
DELTA_15
DELTA_20
```

И сохраним для каждого кадра:

```text
image
candidate
G
BEST
DELTA
E
C
S
CURRENT_FINAL
NEW_FINAL
rank
winner
```

А в конце автоматически построим:

```text
WINNER SUMMARY

CURRENT
BEST
DELTA_02
DELTA_05
...
```

и самое главное:

```text
WINNER CHANGES
```

Чтобы сразу увидеть, **сколько реальных ошибок исправляется и сколько правильных результатов портится**.

И я бы отдельно вывел:

```text
FIXED
```

где новый алгоритм исправил CURRENT,

и

```text
BROKEN
```

где новый алгоритм испортил правильный результат.

Это даст нам уже объективное основание выбрать формулу, а не подбирать веса «на глаз».

---

### 👤 **User** — 2026-08-15 12:24:39

давай. прогоним на всех фото

---

### 🤖 **Assistant** — 2026-08-15 12:24:42

Да. **Прогоняем все 262 фотографии** из `data/input/test` и не меняем основной алгоритм.

Сделаем эксперимент именно с:

- `A_CURRENT` — текущая формула
- `B_BEST_02`
- `C_BEST_05`
- `D_BEST_10`
- `E_BEST_15`
- `F_BEST_20`
- `G_DELTA_02`
- `H_DELTA_05`
- `I_DELTA_10`
- `J_DELTA_15`
- `K_DELTA_20`

И для каждого кандидата сохраняем:

```text
G
E
C
S
BEST
DELTA = BEST - G
FINAL
rank
best_image
```

В конце будут автоматически:

```text
WINNER SUMMARY
WINNER CHANGES
FIXED
BROKEN
```

То есть мы увидим не только, **сколько раз 84 стал победителем**, но и не начал ли новый вариант ломать уже правильные распознавания.

### Запуск

Из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python /tmp/benchmark_components.py
```

Если текущий `/tmp/benchmark_components.py` ещё содержит только старые `A–F`, сначала нужно добавить туда `DELTA`-варианты. **Я бы именно так и сделал — не трогая `scene_analyzer.py` и `recognizer.py`.**

После завершения покажи мне:

```text
WINNER SUMMARY
WINNER CHANGES
FIXED
BROKEN
```

и мы уже по **262 изображениям** выберем формулу.

Особенно нас будет интересовать:

> сколько ошибок `CURRENT` исправляет `DELTA_05/10/15/20` и сколько правильных ответов при этом портит.

Это будет гораздо показательнее, чем смотреть на отдельные фотографии.

---

### 👤 **User** — 2026-08-15 12:26:32

можно посчитать winner changes по всем фото?

---

### 🤖 **Assistant** — 2026-08-15 12:26:33

Да, и **это как раз нужно посчитать**. Более того, я бы вывел не только `WINNER CHANGES`, а полную статистику по всем 262 фото.

Если результаты уже сохранены в читаемом файле, можно быстро посчитать. Дай мне вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -n "WINNER CHANGES" output/benchmark_components/*.txt
```

Но лучше сделать отдельный скрипт, который автоматически выдаст:

```text
TOTAL IMAGES: 262

CURRENT winner:
84_v33  ...
87_v33  ...

CHANGES FROM CURRENT
B_BEST_02
  changed: XX
  unchanged: XXX

C_BEST_05
  changed: XX
  unchanged: XXX

...

FIXED
  CURRENT wrong → new correct: XX

BROKEN
  CURRENT correct → new wrong: XX

UNCHANGED CORRECT: XX
UNCHANGED WRONG: XX
```

И отдельно очень важную таблицу:

```text
CURRENT → NEW

87_v33 → 84_v33    XX
84_v33 → 87_v33    XX
79_v33 → 84_v33    XX
...
```

Так мы увидим **направление изменений**, а не просто количество.

Если у нас есть правильные адреса в именах фотографий (`Ленина 125-127 А ...`), можно ещё автоматически посчитать **реальную accuracy** каждого варианта. Это будет вообще лучший критерий выбора веса.

---

### 👤 **User** — 2026-08-15 12:26:51

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -n "WINNER CHANGES" output/benchmark_components/*.txt
11918:WINNER CHANGES

---

### 🤖 **Assistant** — 2026-08-15 12:26:52

Да. Значит файл уже содержит весь блок результатов. Давай **не будем ничего пересчитывать заново** — посчитаем статистику прямо из него.

Сначала покажи конец файла:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '11918,$p' output/benchmark_components/*.txt
```

Но если там большой список, лучше сразу сделать автоматический подсчёт. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
from collections import Counter

files = list(Path("output/benchmark_components").glob("*.txt"))

if not files:
    print("Нет txt-файлов")
    raise SystemExit

path = max(files, key=lambda p: p.stat().st_mtime)

print("FILE:", path)

text = path.read_text(encoding="utf-8")
lines = text.splitlines()

start = None
for i, line in enumerate(lines):
    if line.strip() == "WINNER CHANGES":
        start = i + 1
        break

if start is None:
    print("WINNER CHANGES не найден")
    raise SystemExit

changes = []
current = None

for line in lines[start:]:
    line = line.strip()

    if not line:
        continue

    if line.startswith("="):
        continue

    if " = " in line and not line.startswith(("B_", "C_", "D_", "E_", "F_", "G_", "H_", "I_", "J_", "K_")):
        current = line.split(" = ", 1)[1].strip()
        continue

    if "=" in line:
        variant, winner = line.split("=", 1)
        variant = variant.strip()
        winner = winner.strip()

        if current:
            changes.append((current, variant, winner))

print()
print("=" * 100)
print("WINNER CHANGES STATISTICS")
print("=" * 100)

variants = sorted(set(v for _, v, _ in changes))

for variant in variants:
    rows = [
        (image, winner)
        for image, v, winner in changes
        if v == variant
    ]

    changed = sum(1 for image, winner in rows if winner)
    print(f"{variant:<15} changes: {changed}")

print()
print("=" * 100)
print("CHANGE MATRIX")
print("=" * 100)

for variant in variants:
    counter = Counter()

    for image, v, winner in changes:
        if v == variant:
            # CURRENT winner берём из строк выше
            pass

# Просто статистика победителей каждого варианта
for variant in variants:
    counter = Counter(
        winner
        for image, v, winner in changes
        if v == variant
    )

    print()
    print(variant)
    for winner, count in counter.most_common():
        print(f"  {winner:<12} {count:4}")

PY
```

Однако здесь есть один нюанс: **твой текущий блок `WINNER CHANGES` показывает только фотографии, где победитель изменился**, поэтому из него нельзя узнать количество `UNCHANGED`.

Для полноценной статистики нужно использовать весь benchmark-файл, где есть строки:

```text
image | weight_set | rank | id | final | G | E | C | S | BEST
```

и уже из них построить таблицу:

```text
262 фото
    ↓
CURRENT winner
    ↓
B/C/D/... winner
    ↓
сравнение
```

**Я предлагаю именно второй вариант.** Он даст нам настоящую статистику:

- сколько изменилось;
- сколько не изменилось;
- куда изменилось;
- какой вариант чаще выбирает 84 вместо 87;
- какие варианты дают одинаковый результат;
- и, главное, **какой вариант реально лучше CURRENT на всём наборе**.

Если хочешь, следующим сообщением дам готовый `analyze_benchmark.py`, который это всё посчитает одной командой.

---

### 👤 **User** — 2026-08-15 12:27:02

давай скрипт

---

### 🤖 **Assistant** — 2026-08-15 12:27:03

Да. Сделаем отдельный скрипт, который **ничего не меняет в распознавании**, а анализирует уже полученный benchmark-файл.

Он посчитает:

- все изображения;
- победителя `CURRENT`;
- победителя каждого варианта;
- `UNCHANGED`;
- `CHANGED`;
- переходы типа `87 → 84`;
- сколько раз каждый вариант исправил изменение относительно CURRENT;
- насколько часто вариант портит результат;
- сводку по каждому адресу.

Создай файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano /tmp/analyze_benchmark.py
```

Вставь:

```python
from pathlib import Path
from collections import Counter, defaultdict
import re

# ============================================================
# CONFIG
# ============================================================

ROOT = Path("output/benchmark_components")

# Если файлов несколько — берём самый свежий
files = list(ROOT.glob("*.txt"))

if not files:
    raise SystemExit(
        f"Нет benchmark txt в {ROOT}"
    )

SOURCE = max(
    files,
    key=lambda p: p.stat().st_mtime,
)

OUTPUT = ROOT / "benchmark_statistics.txt"

# ============================================================
# PARSE
# ============================================================

text = SOURCE.read_text(
    encoding="utf-8"
)

lines = text.splitlines()

# Формат строки:
#
# image | weight_set | rank | id | final | G | E | C | S | BEST | best_image

records = []

for line in lines:

    line = line.strip()

    if not line:
        continue

    if not line.startswith("|"):
        continue

    parts = [
        x.strip()
        for x in line.strip("|").split("|")
    ]

    if len(parts) < 11:
        continue

    # Пропускаем header
    if parts[0].lower() == "image":
        continue

    try:
        image = parts[0]
        weight_set = parts[1]
        rank = int(parts[2])
        fp_id = parts[3]

        final = float(parts[4])
        g = float(parts[5])
        e = float(parts[6])
        c = float(parts[7])
        s = float(parts[8])
        best = float(parts[9])

        best_image = parts[10]

    except Exception:
        continue

    records.append(
        {
            "image": image,
            "weight": weight_set,
            "rank": rank,
            "id": fp_id,
            "final": final,
            "G": g,
            "E": e,
            "C": c,
            "S": s,
            "BEST": best,
            "best_image": best_image,
        }
    )

# ============================================================
# GROUP
# ============================================================

by_image = defaultdict(
    lambda: defaultdict(list)
)

for r in records:
    by_image[
        r["image"]
    ][
        r["weight"]
    ].append(r)

def winner(rows):
    if not rows:
        return None

    rows = sorted(
        rows,
        key=lambda x: x["rank"],
    )

    return rows[0]["id"]

weights = sorted(
    {
        r["weight"]
        for r in records
    }
)

images = sorted(
    by_image.keys()
)

# ============================================================
# CURRENT
# ============================================================

current_weight = "A_CURRENT"

current_winners = {}

for image in images:

    current_winners[image] = winner(
        by_image[image].get(
            current_weight,
            [],
        )
    )

# ============================================================
# REPORT
# ============================================================

out = []

def p(text=""):
    print(text)
    out.append(text)

p("=" * 110)
p("BENCHMARK STATISTICS")
p("=" * 110)

p(f"Source: {SOURCE}")
p(f"Images: {len(images)}")
p(f"Records: {len(records)}")
p(f"Weight sets: {len(weights)}")

p()
p("WEIGHT SETS")
for w in weights:
    p(f"  {w}")

# ============================================================
# WINNER SUMMARY
# ============================================================

p()
p("=" * 110)
p("WINNER SUMMARY")
p("=" * 110)

for w in weights:

    counter = Counter()

    for image in images:

        rows = by_image[
            image
        ].get(
            w,
            [],
        )

        win = winner(rows)

        if win:
            counter[win] += 1

    p()
    p(w)

    for fp_id, count in counter.most_common():
        p(
            f"  {fp_id:<15} {count:4}"
        )

# ============================================================
# CHANGES
# ============================================================

p()
p("=" * 110)
p("CHANGES RELATIVE TO A_CURRENT")
p("=" * 110)

for w in weights:

    if w == current_weight:
        continue

    changed = []
    unchanged = []

    for image in images:

        current = current_winners.get(
            image
        )

        new = winner(
            by_image[
                image
            ].get(
                w,
                [],
            )
        )

        if not new:
            continue

        if new == current:
            unchanged.append(image)
        else:
            changed.append(
                (
                    image,
                    current,
                    new,
                )
            )

    p()
    p(w)

    p(
        f"  CHANGED   : {len(changed)}"
    )

    p(
        f"  UNCHANGED : {len(unchanged)}"
    )

    p(
        f"  TOTAL     : "
        f"{len(changed) + len(unchanged)}"
    )

# ============================================================
# CHANGE MATRIX
# ============================================================

p()
p("=" * 110)
p("CHANGE MATRIX")
p("=" * 110)

for w in weights:

    if w == current_weight:
        continue

    matrix = Counter()

    for image in images:

        current = current_winners.get(
            image
        )

        new = winner(
            by_image[
                image
            ].get(
                w,
                [],
            )
        )

        if (
            current
            and new
            and current != new
        ):
            matrix[
                (
                    current,
                    new,
                )
            ] += 1

    p()
    p(w)

    if not matrix:
        p("  no changes")
        continue

    for (
        (old, new),
        count,
    ) in matrix.most_common():

        p(
            f"  {old:<12} -> "
            f"{new:<12} "
            f"{count:4}"
        )

# ============================================================
# ALL CHANGED IMAGES
# ============================================================

p()
p("=" * 110)
p("ALL WINNER CHANGES")
p("=" * 110)

for image in images:

    current = current_winners.get(
        image
    )

    changes = []

    for w in weights:

        if w == current_weight:
            continue

        new = winner(
            by_image[
                image
            ].get(
                w,
                [],
            )
        )

        if (
            new
            and current
            and new != current
        ):
            changes.append(
                f"{w}={new}"
            )

    if changes:

        p()
        p(image)
        p(
            f"  CURRENT = {current}"
        )

        for change in changes:
            p(
                f"  {change}"
            )

# ============================================================
# WINNER DISTRIBUTION
# ============================================================

p()
p("=" * 110)
p("WINNER DISTRIBUTION COMPARISON")
p("=" * 110)

all_ids = sorted(
    {
        r["id"]
        for r in records
    }
)

header = (
    f"{'ID':<12}"
    + "".join(
        f"{w:>14}"
        for w in weights
    )
)

p(header)
p("-" * len(header))

for fp_id in all_ids:

    row = f"{fp_id:<12}"

    for w in weights:

        count = sum(
            1
            for image in images
            if winner(
                by_image[
                    image
                ].get(
                    w,
                    [],
                )
            ) == fp_id
        )

        row += f"{count:>14}"

    p(row)

# ============================================================
# DELTA ANALYSIS
# ============================================================

p()
p("=" * 110)
p("BEST - GLOBAL DELTA")
p("=" * 110)

# Считаем средний delta для каждого адреса
# по CURRENT winner и по всех кандидатам.

delta_stats = defaultdict(list)

for r in records:

    delta = (
        r["BEST"]
        - r["G"]
    )

    delta_stats[
        r["id"]
    ].append(
        delta
    )

for fp_id in sorted(
    delta_stats
):

    values = np = delta_stats[
        fp_id
    ]

    if not values:
        continue

    avg = sum(values) / len(values)
    mx = max(values)
    mn = min(values)

    p(
        f"{fp_id:<12} "
        f"AVG={avg:+.5f} "
        f"MIN={mn:+.5f} "
        f"MAX={mx:+.5f}"
    )

# ============================================================
# SAVE
# ============================================================

OUTPUT.write_text(
    "\n".join(out),
    encoding="utf-8",
)

print()
print("=" * 110)
print(f"SAVED: {OUTPUT}")
print("=" * 110)
```

Потом запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python /tmp/analyze_benchmark.py
```

Результат будет здесь:

```text
output/benchmark_components/benchmark_statistics.txt
```

### Особенно интересуют эти три блока

После запуска пришли мне:

```bash
grep -A40 "CHANGES RELATIVE" \
output/benchmark_components/benchmark_statistics.txt
```

и:

```bash
grep -A80 "CHANGE MATRIX" \
output/benchmark_components/benchmark_statistics.txt
```

И ещё:

```bash
grep -A30 "WINNER DISTRIBUTION" \
output/benchmark_components/benchmark_statistics.txt
```

По ним уже можно будет понять, **какой вариант `BEST/DELTA` действительно улучшает 262 фотографии, а какой просто перетаскивает победителя с одного адреса на другой**.

---

### 👤 **User** — 2026-08-15 12:27:24

====================

Ленина 125-127 А (10).JPG
  CURRENT = 87_v33
  C_BEST_05=84_v33
  D_BEST_10=84_v33
  E_BEST_15=84_v33
  F_BEST_20=84_v33

Ленина 125-127 А (14).JPG
  CURRENT = 87_v33
  B_BEST_02=84_v33
  C_BEST_05=84_v33
  D_BEST_10=84_v33
  E_BEST_15=84_v33
  F_BEST_20=84_v33

Ленина 125-127 А (8).JPG
  CURRENT = 87_v33
  D_BEST_10=84_v33
  E_BEST_15=84_v33
  F_BEST_20=84_v33

---

### 🤖 **Assistant** — 2026-08-15 12:27:25

Да, это подтверждает нашу гипотезу: **BEST действительно вытаскивает 84 в тех случаях, где GLOBAL ошибается**, и чем сильнее его вес, тем стабильнее исправление.

Но пока это только 3 известных случая. Нам нужна статистика по всем 262.

Сейчас у тебя показан блок `ALL WINNER CHANGES`, а нам нужны именно **итоги**. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -A80 "CHANGES RELATIVE TO A_CURRENT" \
output/benchmark_components/benchmark_statistics.txt
```

И отдельно:

```bash
grep -A100 "CHANGE MATRIX" \
output/benchmark_components/benchmark_statistics.txt
```

### Что я ожидаю увидеть

Если, например, получится:

```text
B_BEST_02
  CHANGED   : 1
  UNCHANGED : 261

C_BEST_05
  CHANGED   : 2
  UNCHANGED : 260

D_BEST_10
  CHANGED   : 3
  UNCHANGED : 259
```

и матрица:

```text
D_BEST_10

  87_v33 -> 84_v33    2
  79_v33 -> 84_v33    1
```

это очень хороший знак.

Но если будет, например:

```text
D_BEST_10

  87_v33 -> 84_v33    3
  84_v33 -> 87_v33    5
  83_v33 -> 79_v33    4
```

то простое увеличение `BEST` нам не подходит.

---

### И ещё важный момент

Из названия файлов:

```text
Ленина 125-127 А (8).JPG
Ленина 125-127 А (10).JPG
Ленина 125-127 А (14).JPG
```

мы **уже знаем правильный адрес = 84**, если именно эти фотографии относятся к 84.

Поэтому следующий шаг можно сделать гораздо интереснее: автоматически определить **GROUND TRUTH из имени файла** и посчитать:

```text
CURRENT accuracy
BEST_02 accuracy
BEST_05 accuracy
BEST_10 accuracy
BEST_15 accuracy
BEST_20 accuracy
DELTA_02 accuracy
...
```

Тогда мы получим не субъективное:

> «кажется, BEST лучше»

а конкретное:

> **CURRENT — 94.3%  
> BEST_10 — 96.6%  
> DELTA_10 — 97.0%**

И уже на основании этого выберем формулу.

Если имена всех 262 фотографий действительно содержат правильный номер адреса, **я бы сейчас именно это и сделал**.

---

### 👤 **User** — 2026-08-15 12:27:44

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -A80 "CHANGES RELATIVE TO A_CURRENT" \
output/benchmark_components/benchmark_statistics.txt
grep: output/benchmark_components/benchmark_statistics.txt: No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 12:27:46

Да, значит предыдущий скрипт **не был запущен** или файл лежит под другим именем. Не будем гадать.

Сначала найдём фактический benchmark:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find output/benchmark_components -maxdepth 1 -type f -printf '%f\n' | sort
```

Потом покажи:

```bash
ls -lah output/benchmark_components/
```

Если там есть исходный `.txt`, мы сразу запустим анализ **из него**, без повторного прогона 262 фотографий.

Если хочешь сразу найти файл, содержащий `WINNER CHANGES`:

```bash
grep -l "WINNER CHANGES" output/benchmark_components/*.txt
```

**Пришли вывод последней команды.** Тогда дам точную команду для подсчёта `CHANGED / UNCHANGED / CHANGE MATRIX` по всем 262 фото.

---

### 👤 **User** — 2026-08-15 12:28:10

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

find output/benchmark_components -maxdepth 1 -type f -printf '%f\n' | sort
components.csv
components.txt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ls -lah output/benchmark_components/
total 1.8M
drwxrwxr-x  2 alexice alexice 4.0K Aug 15 12:19 .
drwxrwxr-x 23 alexice alexice 4.0K Aug 15 12:22 ..
-rw-rw-r--  1 alexice alexice 968K Aug 15 12:25 components.csv
-rw-rw-r--  1 alexice alexice 845K Aug 15 12:25 components.txt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 12:28:10

Да. Файла `benchmark_statistics.txt` у нас действительно нет — сейчас есть только `components.csv` и `components.txt`.

Давай **не перезапускать распознавание**, а посчитаем статистику прямо из уже готового `components.csv`.

Сделаем отдельный скрипт, который покажет:

- сколько всего фотографий;
- победителя `A_CURRENT`;
- сколько раз каждый вариант `BEST_02/05/10/15/20` изменил победителя относительно `CURRENT`;
- **какие именно фото изменились**;
- для каждого изменения: `CURRENT → новый winner`;
- отдельно посчитает случаи, когда `84_v33` вытесняет `87_v33`, `92_v33` и т.д.;
- сохранит всё в `output/benchmark_components/benchmark_statistics.txt`.

Создай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/analyze_benchmark.py <<'PY'
from pathlib import Path
import csv
from collections import defaultdict, Counter

CSV_FILE = Path("output/benchmark_components/components.csv")
OUT_FILE = Path("output/benchmark_components/benchmark_statistics.txt")

rows = []

with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        rows.append(row)

print(f"Loaded rows: {len(rows)}")

# ------------------------------------------------------------
# GROUP BY IMAGE + WEIGHT SET
# ------------------------------------------------------------

data = defaultdict(list)

for row in rows:
    image = row["image"]
    weight_set = row["weight_set"]

    data[(image, weight_set)].append(row)

# winner = rank 1
winners = {}

for key, group in data.items():
    group = sorted(
        group,
        key=lambda x: int(x["rank"])
    )

    winners[key] = group[0]["id"]

images = sorted(
    {row["image"] for row in rows}
)

weight_sets = sorted(
    {row["weight_set"] for row in rows}
)

# Put CURRENT first
weight_sets = (
    ["A_CURRENT"]
    + [x for x in weight_sets if x != "A_CURRENT"]
)

# ------------------------------------------------------------
# STATISTICS
# ------------------------------------------------------------

current_winners = {
    image: winners[(image, "A_CURRENT")]
    for image in images
    if (image, "A_CURRENT") in winners
}

changes = defaultdict(list)

for image in images:

    current = current_winners.get(image)

    if current is None:
        continue

    for ws in weight_sets:

        if ws == "A_CURRENT":
            continue

        winner = winners.get((image, ws))

        if winner is None:
            continue

        if winner != current:
            changes[ws].append(
                (image, current, winner)
            )

# ------------------------------------------------------------
# WRITE REPORT
# ------------------------------------------------------------

with OUT_FILE.open("w", encoding="utf-8") as out:

    def p(text=""):
        print(text)
        out.write(text + "\n")

    p("=" * 100)
    p("BENCHMARK STATISTICS")
    p("=" * 100)

    p(f"Images: {len(images)}")
    p(f"Weight sets: {len(weight_sets)}")
    p(f"Rows: {len(rows)}")
    p()

    # --------------------------------------------------------
    # CURRENT WINNERS
    # --------------------------------------------------------

    p("=" * 100)
    p("CURRENT WINNERS")
    p("=" * 100)

    counter = Counter(current_winners.values())

    for winner, count in counter.most_common():
        p(f"{winner:<15} {count:>5}")

    p()

    # --------------------------------------------------------
    # CHANGES SUMMARY
    # --------------------------------------------------------

    p("=" * 100)
    p("WINNER CHANGES RELATIVE TO A_CURRENT")
    p("=" * 100)

    for ws in weight_sets:

        if ws == "A_CURRENT":
            continue

        changed = changes[ws]

        p()
        p(f"{ws}")
        p(f"  changed: {len(changed)} / {len(images)}")
        p(f"  percent: {100.0 * len(changed) / len(images):.2f}%")

        transitions = Counter(
            (current, winner)
            for _, current, winner in changed
        )

        if transitions:
            p("  transitions:")

            for (current, winner), count in transitions.most_common():
                p(
                    f"    {current} -> {winner}: "
                    f"{count}"
                )

    p()

    # --------------------------------------------------------
    # ALL CHANGED IMAGES
    # --------------------------------------------------------

    p("=" * 100)
    p("ALL CHANGED IMAGES")
    p("=" * 100)

    for ws in weight_sets:

        if ws == "A_CURRENT":
            continue

        changed = changes[ws]

        if not changed:
            continue

        p()
        p("-" * 100)
        p(f"{ws}  ({len(changed)} changes)")
        p("-" * 100)

        for image, current, winner in changed:
            p(
                f"{image}\n"
                f"  {current} -> {winner}"
            )

    # --------------------------------------------------------
    # 84 VS 87
    # --------------------------------------------------------

    p()
    p("=" * 100)
    p("SPECIAL: 84_v33 VS 87_v33")
    p("=" * 100)

    for ws in weight_sets:

        if ws == "A_CURRENT":
            continue

        count_84_from_87 = sum(
            1
            for image, current, winner in changes[ws]
            if current == "87_v33"
            and winner == "84_v33"
        )

        if count_84_from_87:
            p(
                f"{ws:<15} "
                f"87_v33 -> 84_v33 : "
                f"{count_84_from_87}"
            )

    # --------------------------------------------------------
    # CHANGE MATRIX
    # --------------------------------------------------------

    p()
    p("=" * 100)
    p("CHANGE MATRIX")
    p("=" * 100)

    p(
        f"{'CURRENT':<15}"
        f"{'NEW WINNER':<15}"
        + "".join(
            f"{ws:<15}"
            for ws in weight_sets
            if ws != "A_CURRENT"
        )
    )

    all_transitions = set()

    for ws in weight_sets:
        if ws == "A_CURRENT":
            continue

        for _, current, winner in changes[ws]:
            all_transitions.add(
                (current, winner)
            )

    for current, winner in sorted(all_transitions):

        line = (
            f"{current:<15}"
            f"{winner:<15}"
        )

        for ws in weight_sets:

            if ws == "A_CURRENT":
                continue

            count = sum(
                1
                for _, c, w in changes[ws]
                if c == current and w == winner
            )

            line += f"{count:<15}"

        p(line)

    p()
    p("=" * 100)
    p(f"REPORT SAVED TO: {OUT_FILE}")
    p("=" * 100)

print()
print(f"REPORT: {OUT_FILE}")
PY

uv run python /tmp/analyze_benchmark.py
```

После этого покажи вывод:

```bash
cat output/benchmark_components/benchmark_statistics.txt
```

### Что особенно важно

Мы сейчас получим не просто количество изменений, а, например:

```text
B_BEST_02
  changed: 1 / 262
  percent: 0.38%
  transitions:
    87_v33 -> 84_v33: 1

C_BEST_05
  changed: 2 / 262
  percent: 0.76%
  transitions:
    87_v33 -> 84_v33: 2
```

И отдельно:

```text
SPECIAL: 84_v33 VS 87_v33

B_BEST_02     87_v33 -> 84_v33 : 1
C_BEST_05     87_v33 -> 84_v33 : 2
...
```

Это уже позволит **не на глаз**, а по всем 262 фотографиям определить, действительно ли добавление `BEST` улучшает систему или просто случайно исправляет несколько пограничных случаев.

И я бы пока **не менял веса в основном `recognizer.py`**. Сначала посмотрим эту статистику. Если окажется, что `BEST_05` или `BEST_10` стабильно исправляет ошибки, следующим шагом сделаем уже нормальный тест **Top-1 / Top-2 / Top-3 accuracy и margin между первым и вторым кандидатом**.

---

### 👤 **User** — 2026-08-15 12:29:14

====================
REPORT SAVED TO: output/benchmark_components/benchmark_statistics.txt
====================================================================================================

REPORT: output/benchmark_components/benchmark_statistics.txt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cat output/benchmark_components/benchmark_statistics.txt
====================================================================================================
BENCHMARK STATISTICS
====================================================================================================
Images: 262
Weight sets: 6
Rows: 7860

====================================================================================================
CURRENT WINNERS
====================================================================================================
94_v33             24
78_v33             20
87_v33             20
89_v33             20
83_v33             18
92_v33             18
95_v33             17
85_v33             17
81_v33             16
88_v33             16
86_v33             15
91_v33             13
93_v33             12
82_v33              9
79_v33              8
80_v33              8
84_v33              8
90_v33              3

====================================================================================================
WINNER CHANGES RELATIVE TO A_CURRENT
====================================================================================================

B_BEST_02
  changed: 1 / 262
  percent: 0.38%
  transitions:
    87_v33 -> 84_v33: 1

C_BEST_05
  changed: 2 / 262
  percent: 0.76%
  transitions:
    87_v33 -> 84_v33: 2

D_BEST_10
  changed: 3 / 262
  percent: 1.15%
  transitions:
    87_v33 -> 84_v33: 3

E_BEST_15
  changed: 3 / 262
  percent: 1.15%
  transitions:
    87_v33 -> 84_v33: 3

F_BEST_20
  changed: 3 / 262
  percent: 1.15%
  transitions:
    87_v33 -> 84_v33: 3

====================================================================================================
ALL CHANGED IMAGES
====================================================================================================

----------------------------------------------------------------------------------------------------
B_BEST_02  (1 changes)
----------------------------------------------------------------------------------------------------
Ленина 125-127 А (14).JPG
  87_v33 -> 84_v33

----------------------------------------------------------------------------------------------------
C_BEST_05  (2 changes)
----------------------------------------------------------------------------------------------------
Ленина 125-127 А (10).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (14).JPG
  87_v33 -> 84_v33

----------------------------------------------------------------------------------------------------
D_BEST_10  (3 changes)
----------------------------------------------------------------------------------------------------
Ленина 125-127 А (10).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (14).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (8).JPG
  87_v33 -> 84_v33

----------------------------------------------------------------------------------------------------
E_BEST_15  (3 changes)
----------------------------------------------------------------------------------------------------
Ленина 125-127 А (10).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (14).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (8).JPG
  87_v33 -> 84_v33

----------------------------------------------------------------------------------------------------
F_BEST_20  (3 changes)
----------------------------------------------------------------------------------------------------
Ленина 125-127 А (10).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (14).JPG
  87_v33 -> 84_v33
Ленина 125-127 А (8).JPG
  87_v33 -> 84_v33

====================================================================================================
SPECIAL: 84_v33 VS 87_v33
====================================================================================================
B_BEST_02       87_v33 -> 84_v33 : 1
C_BEST_05       87_v33 -> 84_v33 : 2
D_BEST_10       87_v33 -> 84_v33 : 3
E_BEST_15       87_v33 -> 84_v33 : 3
F_BEST_20       87_v33 -> 84_v33 : 3

====================================================================================================
CHANGE MATRIX
====================================================================================================
CURRENT        NEW WINNER     B_BEST_02      C_BEST_05      D_BEST_10      E_BEST_15      F_BEST_20      
87_v33         84_v33         1              2              3              3              3              

====================================================================================================
REPORT SAVED TO: output/benchmark_components/benchmark_statistics.txt
====================================================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
  тут только 84 - а спорных случаев большще

---

### 🤖 **Assistant** — 2026-08-15 12:29:14

Да. И это **очень важное наблюдение**.

Сейчас статистика считает только **фактическую смену победителя**. Поэтому она показывает лишь 3 случая `87 → 84`. Но у нас есть гораздо больше **спорных случаев**, где:

- `CURRENT` победил с небольшим отрывом;
- второй кандидат очень близко;
- `BEST` у второго кандидата существенно выше;
- при этом итоговый `FINAL` всё ещё оставляет его вторым.

Например, как у нас было:

```text
87_v33  FINAL=0.8969  G=0.8883 ... BEST=0.8938
84_v33  FINAL=0.8950  G=0.8792 ... BEST=0.9476
```

То есть `87` победил всего на:

```text
0.0019
```

а `BEST` у `84`:

```text
0.9476
```

против:

```text
0.8938
```

Разница огромная:

```text
+0.0538
```

**Именно такие случаи сейчас теряются в нашей статистике.**

### Предлагаю следующий анализ

Не менять пока алгоритм. Сделаем отдельный анализатор `components.csv`, который для каждой фотографии посчитает:

1. `CURRENT winner`
2. `SECOND candidate`
3. **margin**:
   ```text
   FINAL1 - FINAL2
   ```
4. `BEST1`
5. `BEST2`
6. **BEST advantage второго кандидата**
7. случаи, где второй кандидат имеет:
   - `BEST > BEST winner`
   - `BEST` существенно выше
   - `FINAL margin < 0.01`
   - `< 0.02`
   - `< 0.03`
   - `< 0.05`
8. отдельно посмотрим:
   ```text
   CURRENT winner
   BEST winner
   ```
   даже если `BEST` сам по себе ещё не меняет итоговый рейтинг.

То есть получим примерно такую таблицу:

```text
IMAGE                         CURRENT   2ND      MARGIN   BEST1    BEST2    BEST_DIFF
Ленина ... (10).JPG           87        84       0.0019   0.8938   0.9476   +0.0538
Ленина ... (11).JPG           84        87       0.0061   0.9487   0.8877   -0.0610
...
```

И ещё гораздо более полезную классификацию:

```text
========================================================
SUSPICIOUS CASES
========================================================

margin < 0.01       XX
margin < 0.02       XX
margin < 0.03       XX
margin < 0.05       XX

2nd BEST > winner BEST       XX
2nd BEST > winner BEST + .02 XX
2nd BEST > winner BEST + .05 XX
```

### Главное

У нас уже есть **7860 строк**, то есть данных достаточно. Ничего заново считать через DINO не нужно.

И я бы сделал ещё один показатель:

**BEST-adjusted ranking**

Не обязательно сразу использовать его в боевом алгоритме. Просто виртуально посмотрим, что произойдёт при:

```text
FINAL + 0.02 * BEST
FINAL + 0.05 * BEST
FINAL + 0.10 * BEST
FINAL + 0.15 * BEST
FINAL + 0.20 * BEST
```

Но самое важное - **смотреть не только на смену winner, а на Top-2 спорные случаи**.

Потому что сейчас мы видим только верхушку айсберга: `3` исправленных случая. А вполне может оказаться, что имеется, например, **30-50 случаев, где система почти ошиблась**, и `BEST` очень хорошо показывает правильный адрес.

Если хочешь, следующим шагом я дам скрипт именно для такого **полного анализа 262 фотографий**, без повторного распознавания.

---

### 👤 **User** — 2026-08-15 12:29:48

Дай мне скрипт для полного анализа 262 фотографий

---

### 🤖 **Assistant** — 2026-08-15 12:29:49

Да. Сейчас лучше сделать **полный диагностический прогон по уже существующему `components.csv`**, ничего заново не распознавая.

Он даст именно то, чего нам не хватало:

- Top-1 и Top-2;
- разницу `FINAL1 - FINAL2`;
- разницу `BEST2 - BEST1`;
- случаи, когда **второй кандидат имеет значительно лучший BEST**;
- случаи с маленьким `FINAL margin`;
- виртуальный результат при добавлении `BEST` с разными коэффициентами;
- список всех подозрительных фотографий;
- статистику по всем 262 фото;
- отдельный анализ `84 vs 87`;
- CSV для дальнейшего анализа.

Запускай из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/full_analysis.py <<'PY'
from pathlib import Path
import csv
from collections import Counter, defaultdict

INPUT = Path("output/benchmark_components/components.csv")
OUT_DIR = Path("output/benchmark_components/full_analysis")

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded rows: {len(rows)}")

# ------------------------------------------------------------
# GROUP
# ------------------------------------------------------------

groups = defaultdict(list)

for r in rows:
    groups[r["image"], r["weight_set"]].append(r)

weight_sets = sorted(
    {r["weight_set"] for r in rows}
)

weight_sets = (
    ["A_CURRENT"]
    + [x for x in weight_sets if x != "A_CURRENT"]
)

images = sorted(
    {r["image"] for r in rows}
)

print(f"Images: {len(images)}")
print(f"Weight sets: {weight_sets}")

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def ranked(image, weight_set):
    result = groups.get((image, weight_set), [])

    return sorted(
        result,
        key=lambda x: float(x["final"]),
        reverse=True,
    )

def f(row, key):
    return float(row[key])

# ------------------------------------------------------------
# MAIN DIAGNOSTIC CSV
# ------------------------------------------------------------

diagnostic_file = OUT_DIR / "diagnostic.csv"

fields = [
    "image",
    "weight_set",

    "winner",
    "second",

    "final1",
    "final2",
    "final_margin",

    "G1",
    "G2",
    "E1",
    "E2",
    "C1",
    "C2",
    "S1",
    "S2",

    "BEST1",
    "BEST2",
    "best_diff",

    "best_image1",
    "best_image2",

    "best_winner",
]

with diagnostic_file.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    for image in images:

        for ws in weight_sets:

            r = ranked(image, ws)

            if len(r) < 2:
                continue

            a = r[0]
            b = r[1]

            final1 = f(a, "final")
            final2 = f(b, "final")

            best1 = f(a, "BEST")
            best2 = f(b, "BEST")

            writer.writerow({
                "image": image,
                "weight_set": ws,

                "winner": a["id"],
                "second": b["id"],

                "final1": final1,
                "final2": final2,
                "final_margin": final1 - final2,

                "G1": f(a, "G"),
                "G2": f(b, "G"),

                "E1": f(a, "E"),
                "E2": f(b, "E"),

                "C1": f(a, "C"),
                "C2": f(b, "C"),

                "S1": f(a, "S"),
                "S2": f(b, "S"),

                "BEST1": best1,
                "BEST2": best2,
                "best_diff": best2 - best1,

                "best_image1": a["best_image"],
                "best_image2": b["best_image"],

                "best_winner": (
                    a["id"]
                    if best1 >= best2
                    else b["id"]
                ),
            })

# ------------------------------------------------------------
# CURRENT ANALYSIS
# ------------------------------------------------------------

current = {}

for image in images:

    r = ranked(image, "A_CURRENT")

    if len(r) < 2:
        continue

    current[image] = r

# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

report_file = OUT_DIR / "full_analysis.txt"

with report_file.open(
    "w",
    encoding="utf-8",
) as out:

    def p(x=""):
        print(x)
        out.write(x + "\n")

    p("=" * 120)
    p("FULL 262 IMAGE DIAGNOSTIC ANALYSIS")
    p("=" * 120)

    p(f"Images: {len(images)}")
    p(f"Rows: {len(rows)}")

    # --------------------------------------------------------
    # THRESHOLDS
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("CURRENT: FINAL MARGIN DISTRIBUTION")
    p("=" * 120)

    margins = []

    for image, r in current.items():

        margin = (
            f(r[0], "final")
            - f(r[1], "final")
        )

        margins.append(
            (margin, image, r[0]["id"], r[1]["id"])
        )

    thresholds = [
        0.001,
        0.002,
        0.005,
        0.010,
        0.020,
        0.030,
        0.050,
        0.100,
    ]

    for threshold in thresholds:

        count = sum(
            1
            for margin, *_ in margins
            if margin < threshold
        )

        p(
            f"margin < {threshold:.3f}: "
            f"{count:3d} / {len(margins)} "
            f"({100*count/len(margins):.2f}%)"
        )

    # --------------------------------------------------------
    # BEST BEATS
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("CURRENT: SECOND CANDIDATE BEST ADVANTAGE")
    p("=" * 120)

    cases = []

    for image, r in current.items():

        a = r[0]
        b = r[1]

        diff = (
            f(b, "BEST")
            - f(a, "BEST")
        )

        margin = (
            f(a, "final")
            - f(b, "final")
        )

        cases.append(
            (
                diff,
                margin,
                image,
                a,
                b,
            )
        )

    for threshold in [
        0.005,
        0.010,
        0.020,
        0.030,
        0.050,
        0.100,
    ]:

        count = sum(
            1
            for diff, *_ in cases
            if diff > threshold
        )

        p(
            f"SECOND BEST - WINNER BEST > "
            f"{threshold:.3f}: "
            f"{count:3d}"
        )

    # --------------------------------------------------------
    # STRONG SUSPICIOUS CASES
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("SUSPICIOUS CASES")
    p("=" * 120)

    suspicious = []

    for diff, margin, image, a, b in cases:

        # Strong indication that second candidate
        # may actually be correct.
        if (
            margin < 0.030
            and diff > 0.020
        ):
            suspicious.append(
                (
                    diff,
                    margin,
                    image,
                    a,
                    b,
                )
            )

    suspicious.sort(
        key=lambda x: (
            -x[0],
            x[1],
        )
    )

    p(
        f"Found: {len(suspicious)} "
        f"cases "
        f"(margin < 0.03 AND BEST advantage > 0.02)"
    )

    for (
        diff,
        margin,
        image,
        a,
        b,
    ) in suspicious:

        p()
        p(image)
        p(
            f"  CURRENT: {a['id']} "
            f"FINAL={f(a,'final'):.6f} "
            f"BEST={f(a,'BEST'):.6f}"
        )
        p(
            f"  SECOND : {b['id']} "
            f"FINAL={f(b,'final'):.6f} "
            f"BEST={f(b,'BEST'):.6f}"
        )
        p(
            f"  FINAL margin : {margin:.6f}"
        )
        p(
            f"  BEST advantage: {diff:+.6f}"
        )
        p(
            f"  BEST images: "
            f"{a['best_image']} / "
            f"{b['best_image']}"
        )

    # --------------------------------------------------------
    # 84 vs 87
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("SPECIAL ANALYSIS: 84_v33 VS 87_v33")
    p("=" * 120)

    special = []

    for image, r in current.items():

        lookup = {
            x["id"]: x
            for x in r
        }

        if (
            "84_v33" not in lookup
            or "87_v33" not in lookup
        ):
            continue

        a = lookup["84_v33"]
        b = lookup["87_v33"]

        final_delta = (
            f(a, "final")
            - f(b, "final")
        )

        best_delta = (
            f(a, "BEST")
            - f(b, "BEST")
        )

        special.append(
            (
                abs(final_delta),
                image,
                final_delta,
                best_delta,
                a,
                b,
            )
        )

    special.sort(
        key=lambda x: x[0]
    )

    p()
    p(
        f"{'IMAGE':<42}"
        f"{'FINAL 84-87':>15}"
        f"{'BEST 84-87':>15}"
    )

    for _, image, fd, bd, a, b in special:

        p(
            f"{image[:40]:<42}"
            f"{fd:>15.6f}"
            f"{bd:>15.6f}"
        )

    # --------------------------------------------------------
    # VIRTUAL BEST WEIGHTS
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("VIRTUAL FINAL = CURRENT FINAL + BEST_WEIGHT * BEST")
    p("=" * 120)

    virtual_weights = [
        0.00,
        0.02,
        0.05,
        0.10,
        0.15,
        0.20,
    ]

    for bw in virtual_weights:

        winners = Counter()

        for image in images:

            r = ranked(
                image,
                "A_CURRENT"
            )

            if not r:
                continue

            best_row = max(
                r,
                key=lambda x:
                    f(x, "final")
                    + bw * f(x, "BEST")
            )

            winners[
                best_row["id"]
            ] += 1

        p()
        p(
            f"BEST_WEIGHT = {bw:.2f}"
        )

        for winner, count in winners.most_common():
            p(
                f"  {winner:<15} "
                f"{count:>4}"
            )

    # --------------------------------------------------------
    # VIRTUAL CHANGES
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("VIRTUAL WINNER CHANGES")
    p("=" * 120)

    for bw in virtual_weights:

        changed = []

        for image in images:

            r = ranked(
                image,
                "A_CURRENT"
            )

            if not r:
                continue

            current_winner = r[0]["id"]

            virtual_winner = max(
                r,
                key=lambda x:
                    f(x, "final")
                    + bw * f(x, "BEST")
            )["id"]

            if (
                virtual_winner
                != current_winner
            ):
                changed.append(
                    (
                        image,
                        current_winner,
                        virtual_winner,
                    )
                )

        p()
        p(
            f"BEST_WEIGHT={bw:.2f} "
            f"changed={len(changed)}"
        )

        transitions = Counter(
            (a, b)
            for _, a, b in changed
        )

        for (
            (a, b),
            count,
        ) in transitions.most_common():

            p(
                f"  {a} -> {b}: "
                f"{count}"
            )

    # --------------------------------------------------------
    # LOW MARGIN TOP 30
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("TOP 30 LOWEST FINAL MARGINS")
    p("=" * 120)

    margins.sort(
        key=lambda x: x[0]
    )

    for (
        margin,
        image,
        winner,
        second,
    ) in margins[:30]:

        r = current[image]

        a = r[0]
        b = r[1]

        p(
            f"{margin:.6f} | "
            f"{winner:<10} "
            f"{second:<10} | "
            f"BEST "
            f"{f(a,'BEST'):.4f} / "
            f"{f(b,'BEST'):.4f} | "
            f"{image}"
        )

    # --------------------------------------------------------
    # TOP BEST REVERSALS
    # --------------------------------------------------------

    p()
    p("=" * 120)
    p("TOP 30 BEST ADVANTAGES OF SECOND CANDIDATE")
    p("=" * 120)

    cases.sort(
        key=lambda x: x[0],
        reverse=True
    )

    for (
        diff,
        margin,
        image,
        a,
        b,
    ) in cases[:30]:

        p(
            f"BEST_DIFF={diff:+.6f} "
            f"FINAL_MARGIN={margin:.6f} | "
            f"{a['id']} / {b['id']} | "
            f"{image}"
        )

    p()
    p("=" * 120)
    p("END")
    p("=" * 120)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print()
print("=" * 100)
print("DONE")
print("=" * 100)
print(f"Diagnostic CSV : {diagnostic_file}")
print(f"Full report    : {report_file}")
print()
PY

uv run python /tmp/full_analysis.py
```

После выполнения:

```bash
less output/benchmark_components/full_analysis/full_analysis.txt
```

И отдельно очень удобно:

```bash
column -s, -t < output/benchmark_components/full_analysis/diagnostic.csv | less -S
```

### Что нас особенно интересует

В отчёте будут три ключевых блока.

**1. `SUSPICIOUS CASES`**

Это случаи типа:

```text
CURRENT: 87_v33 FINAL=0.8969 BEST=0.8938
SECOND : 84_v33 FINAL=0.8950 BEST=0.9476

FINAL margin : 0.0019
BEST advantage: +0.0538
```

Вот **это потенциальные ошибки**, которые обычный `winner changes` вообще не показывает.

**2. `TOP 30 LOWEST FINAL MARGINS`**

Это все фотографии, где система наиболее неуверенна. Мы сможем посмотреть их визуально и понять, действительно ли второй кандидат часто правильный.

**3. `VIRTUAL FINAL`**

Мы увидим, например:

```text
BEST_WEIGHT = 0.00
...

BEST_WEIGHT = 0.05
...

BEST_WEIGHT = 0.10
...

BEST_WEIGHT = 0.15
...
```

То есть пока **не меняя код распознавания**, проверим, насколько добавление `BEST` реально меняет картину на всех 262 фотографиях.

И важный момент: я специально сделал виртуальную формулу **`FINAL + BEST_WEIGHT × BEST`**, а не просто увеличил вес BEST внутри текущей суммы. Это позволит отдельно увидеть силу `BEST`, не ломая текущую систему весов `G/E/C/S`.

---

### 👤 **User** — 2026-08-15 12:30:33

# LOAD
# ------------------------------------------------------------

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded rows: {len(rows)}")

# ------------------------------------------------------------
# GROUP
uv run python /tmp/full_analysis.pyle}")e}")------------------
Loaded rows: 7860
Images: 262
Weight sets: ['A_CURRENT', 'B_BEST_02', 'C_BEST_05', 'D_BEST_10', 'E_BEST_15', 'F_BEST_20']
Traceback (most recent call last):
  File "/tmp/full_analysis.py", line 123, in <module>
    final1 = f(a, "final")
             ^^^^^^^^^^^^^
TypeError: '_io.TextIOWrapper' object is not callable

---

### 🤖 **Assistant** — 2026-08-15 12:30:35

Да, это моя ошибка в скрипте. Я назвал функцию `f()` для чтения чисел, а затем открыл файл через `with ... as f:` — в этот момент `f` стал файловым объектом.

Ничего заново считать не надо. Исправим только скрипт.

Самый простой вариант — заменить имя функции `f()` на `num()` и все вызовы `f(` на `num(`, **кроме `as f`**. Надёжнее сделать автоматически:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -i 's/^def f(row, key):/def num(row, key):/' /tmp/full_analysis.py

sed -i \
  -E 's/\bf\(([^)]*)\)/num(\1)/g' \
  /tmp/full_analysis.py
```

Проверим, что получилось:

```bash
grep -nE 'def num|num\(|as f|f\(' /tmp/full_analysis.py | head -80
```

Должно быть примерно:

```text
41:def num(row, key):
...
123:final1 = num(a, "final")
124:final2 = num(b, "final")
...
```

А `as f` должно остаться только там, где открывается файл:

```text
with diagnostic_file.open(...) as f:
with report_file.open(...) as out:
```

После этого запускаем:

```bash
uv run python /tmp/full_analysis.py
```

Если всё нормально, получим:

```text
output/benchmark_components/full_analysis/diagnostic.csv
output/benchmark_components/full_analysis/full_analysis.txt
```

И сразу после выполнения давай посмотрим **самое интересное**, не весь огромный файл:

```bash
grep -A120 "SUSPICIOUS CASES" \
output/benchmark_components/full_analysis/full_analysis.txt
```

а затем:

```bash
grep -A80 "VIRTUAL WINNER CHANGES" \
output/benchmark_components/full_analysis/full_analysis.txt
```

Вот эти два блока сейчас для нас наиболее важны: первый покажет **реально сомнительные фотографии**, а второй — насколько `BEST` способен исправлять их при разных коэффициентах.

---

### 👤 **User** — 2026-08-15 12:31:55

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -i 's/^def f(row, key):/def num(row, key):/' /tmp/full_analysis.py

sed -i \
  -E 's/\bf$([^)]*)$/num(\1)/g' \
  /tmp/full_analysis.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -nE 'def num|num\(|as f|f\(' /tmp/full_analysis.py | head -80
14:with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
58:def num(row, key):
102:) as f:
123:            final1 = num(a, "final")
124:            final2 = num(b, "final")
126:            best1 = num(a, "BEST")
127:            best2 = num(b, "BEST")
140:                "G1": num(a, "G"),
141:                "G2": num(b, "G"),
143:                "E1": num(a, "E"),
144:                "E2": num(b, "E"),
146:                "C1": num(a, "C"),
147:                "C2": num(b, "C"),
149:                "S1": num(a, "S"),
150:                "S2": num(b, "S"),
219:            num(r[0], "final")
220:            - num(r[1], "final")
269:            num(b, "BEST")
270:            - num(a, "BEST")
274:            num(a, "final")
275:            - num(b, "final")
363:            f"FINAL={num(a,'final'):.6f} "
364:            f"BEST={num(a,'BEST'):.6f}"
368:            f"FINAL={num(b,'final'):.6f} "
369:            f"BEST={num(b,'BEST'):.6f}"
411:            num(a, "final")
412:            - num(b, "final")
416:            num(a, "BEST")
417:            - num(b, "BEST")
485:                    num(x, "final")
486:                    + bw * num(x, "BEST")
532:                    num(x, "final")
533:                    + bw * num(x, "BEST")
599:            f"{num(a,'BEST'):.4f} / "
600:            f"{num(b,'BEST'):.4f} | "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 12:31:57

Да, теперь проблема исправлена: `f` использовался одновременно как функция и как `open(...)`. После `sed` функция стала `num()`, но **строка 102 всё ещё использует `as f`** — это уже нормально, потому что `num()` больше с ним не конфликтует.

Запускай полный анализ именно через `uv`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python /tmp/full_analysis.py
```

Если отработает, сразу покажи последние ~150 строк:

```bash
tail -n 150 output/benchmark_components/full_analysis.txt
```

И отдельно самое важное — какие кандидаты меняются относительно `A_CURRENT`:

```bash
grep -nE \
"WINNER|CHANGES|CHANGED|84_v33|87_v33|LOW|AMBIG|ERROR" \
output/benchmark_components/full_analysis.txt | tail -n 200
```

### Но я бы сейчас сделал ещё лучше

У нас уже видно, что простое добавление `BEST` меняет только **3 из 262** фотографий. Это означает, что `BEST` сам по себе не решает все спорные случаи.

В полном анализе нужно посмотреть не только:

```text
FINAL
BEST
```

но и **разрыв между первым и вторым кандидатом**:

```text
winner_score - second_score
```

Например:

```text
84 = 0.892
87 = 0.891
DELTA = 0.001
```

Это реально **сомнительный случай**.

А вот:

```text
84 = 0.892
87 = 0.840
DELTA = 0.052
```

— уверенный случай.

Поэтому после запуска полного анализа нам особенно нужны четыре показателя:

1. **сколько случаев меняет BEST;**
2. **сколько случаев имеют маленький DELTA;**
3. **какие именно кандидаты конкурируют в этих случаях;**
4. **помогает ли BEST именно в случаях с маленьким DELTA.**

И тогда уже можно сделать нормальную логику:

```text
если DELTA большой
    → берем первого

если DELTA маленький
    → подключаем BEST
    → возможно E/C/S
    → принимаем решение между 1-м и 2-м кандидатом
```

**Не будем пока менять основной алгоритм.** Сначала получим статистику по всем 262 фотографиям.

---


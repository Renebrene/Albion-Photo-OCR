## СЕССИЯ: LORA

**Создано:** 2026-08-07 22:33:24
**Обновлено:** 2026-08-19 17:08:04
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c)

---

### 🤖 **Assistant** — 2026-08-13 22:04:58

Да. По этому прогону уже видно **существенный результат v33**: шесть fingerprint'ов довольно хорошо разделяют сцены, но есть важная проблема с **пограничными объектами 79/81/83/78**, особенно для `Ленина 125-127` и `Комарова Добровольского А`.

### Что видно по результатам

| Fingerprint | Основная сцена | Качество |
|---|---|---|
| **78_v33** | `00`, `Космонавтов 13`, `Ленина Ашхабадский` | очень хорошо |
| **79_v33** | `Комарова 20/Добровольского Б`, `Ленина 125-127` | хорошо, но Ленина неоднозначна |
| **80_v33** | `Комарова 28 А` | очень хорошо |
| **81_v33** | `1 Конной Армии 32 А` | очень хорошо |
| **82_v33** | `Добровольского 17 А` | отлично |
| **83_v33** | `Нагибина 24 А` | отлично |

### 1. Сильная сторона — реальные сцены распознаются очень уверенно

Например:

`Добровольского 17 А`:

- 0.9460
- 0.9467
- 0.9509
- 0.9514
- 0.9531
- 0.9569
- 0.9571

Это **прекрасный кластер**. Причём второй кандидат находится около `0.81–0.84`, то есть отрыв большой.

То же самое для `Комарова 28 А`:

`0.9054–0.9328`

и для `Нагибина 24 А`:

`0.8820–0.9479`.

То есть fingerprint действительно выучил **визуальную идентичность сцены**, а не просто случайно выбирает один класс.

---

## 2. Очень интересный результат — `00`

`00` практически стабильно определяется как `78_v33`.

Например:

```text
0.9475
0.9384
0.9336
0.9301
0.9375
0.9057
0.9513
0.9300
0.9470
0.9341
0.9364
```

Это уже не случайное совпадение.

Причём `BEST IMAGE` постоянно возвращает:

```text
photo040.JPG
photo042.JPG
photo044.JPG
photo043.JPG
photo010.JPG
photo012.JPG
```

То есть **внутри fingerprint 78 есть несколько действительно близких эталонов**, и система умеет выбирать конкретный representative.

---

# 3. Но есть главная проблема: `78/79/81/83` слишком близки

Посмотри, например:

```text
Комарова Добровольского А (42)

83 = 0.8752
79 = 0.8751
81 = 0.8747
82 = 0.8709
78 = 0.8696
```

Разница между первым и вторым:

```text
0.0001
```

Это **абсолютно неразрешённый случай**.

И правильно, что v33 говорит:

```text
CONFIDENCE AMBIGUOUS
STATUS AMBIGUOUS
```

То есть здесь алгоритм ведёт себя правильно.

---

# 4. Ещё более показательная группа — Ленина 125-127

Например:

```text
Ленина 125-127 А (17)

79 = 0.8743
83 = 0.8731
81 = 0.8539
```

margin:

```text
0.0012
```

Или:

```text
Ленина 125-127 А (16)

79 = 0.8684
83 = 0.8648
81 = 0.8475
```

margin:

```text
0.0037
```

Это означает, что **DINOv2 видит эти изображения как очень похожие сцены**.

И здесь я бы пока **не пытался искусственно повышать confidence**.

---

# 5. Самое важное наблюдение

У нас получается примерно такая структура:

```text
                 ┌── 78
                 │
                 ├── 79
        ОБЩАЯ ───┤
        СЦЕНА    ├── 81
                 │
                 └── 83

         отдельно:
         80
         82
```

То есть:

**80 и 82 очень хорошо отделяются.**

А вот:

**78 ↔ 79 ↔ 81 ↔ 83**

образуют близкую группу.

Это очень важный результат для следующего этапа разработки.

---

# 6. `Ленина Ашхабадский` — отдельная проблема

Там система в целом правильно выбирает `78`, но confidence уже значительно хуже:

```text
0.8187
0.8224
0.8484
0.8413
0.8459
0.8207
0.8171
0.8383
0.8314
0.8204
0.8715
0.8309
0.8513
```

Причём:

```text
Ленина Ашхабадский А (3)
0.7067
NO_MATCH

Ленина Ашхабадский А (4)
0.7987
NO_MATCH
```

И это **очень хороший признак**, что threshold сейчас не просто декоративный.

Система фактически говорит:

> «Я вижу сходство с 78, но недостаточно уверен, чтобы назвать это совпадением».

Это именно то поведение, которое нам нужно сохранить.

---

# 7. А вот `Комарова 20 Добровольского Б (4)` — особенно интересный случай

```text
79 = 0.6004
83 = 0.5539
82 = 0.5501
78 = 0.5376
81 = 0.5308
80 = 0.5216

NO_MATCH
```

А остальные изображения той же сцены:

```text
0.9485
0.9529
```

То есть здесь **не ошибка fingerprint'а**.

Скорее всего:

> `Комарова 20 Добровольского Б (4)` визуально настолько отличается от остальных фотографий той же сцены, что глобальный embedding уже не способен надёжно связать её с fingerprint 79.

И это как раз тот случай, ради которого нам нужны **patch tokens**.

---

# Что я бы делал дальше

Я бы **не менял сейчас threshold вслепую**.

v33 уже показывает очень полезную картину.

Следующий этап я бы сделал таким:

### Этап 1 — построить confusion matrix

Не просто:

```text
image → best fingerprint
```

а:

```text
                    78      79      80      81      82      83

78                   —      ?       ?       ?       ?       ?
79                  ...
80
81
82
83
```

И вычислить:

- средний score;
- median;
- min/max;
- standard deviation;
- `margin`;
- процент `CONFIDENT`;
- процент `PROBABLE`;
- процент `AMBIGUOUS`;
- процент `NO_MATCH`.

---

### Этап 2 — особенно изучить margin

Сейчас видно, что **score сам по себе недостаточен**.

Например:

```text
0.900 / 0.850
```

намного надёжнее, чем:

```text
0.900 / 0.899
```

Поэтому у нас фактически два независимых показателя:

```text
SCORE
MARGIN
```

И я бы в v34 сделал confidence примерно двухмерным:

```text
              HIGH SCORE
                  │
                  │       CONFIDENT
                  │
                  │
        PROBABLE  │
                  │
──────────────────┼──────────────────
                  │
                  │       AMBIGUOUS
                  │
             LOW SCORE
```

---

# И главное — я бы сейчас не трогал DINOv2

По этому выводу:

**DINOv2 + patch tokens работают.**

Проблема уже не в том, что модель «не понимает сцены».

Наоборот:

- `80` отлично отделяется;
- `82` отлично отделяется;
- `83` отлично отделяется;
- `81` отлично отделяется;
- `78` хорошо отделяется;
- `79` хорошо отделяется;
- проблема возникает именно там, где **сами фотографии визуально близки**.

Это уже следующий уровень задачи:

> **scene recognition → fine-grained scene disambiguation**

И вот здесь нам очень пригодится уже имеющийся `patch_embeddings.npy`.

### Я предлагаю следующий шаг

Не переписывать систему целиком.

**Сделать `v34` как второй этап распознавания:**

```text
                    DINO global
                         ↓
                  top-2 / top-3
                         ↓
              ┌──────────┴──────────┐
              │                     │
        большой margin        маленький margin
              │                     │
          ACCEPT               PATCH ANALYSIS
                                      ↓
                              spatial similarity
                                      ↓
                              final decision
```

То есть для нормальных случаев система остаётся такой же быстрой, а **только спорные случаи** вроде:

```text
79 = 0.8743
83 = 0.8731
```

отправляются на patch-level анализ.

Это, на мой взгляд, сейчас самый правильный следующий шаг для `scene_fingerprint_mvp_v02`.

---

### 👤 **User** — 2026-08-13 22:09:02

дело в том, что слепки с patch весят очень много. давай сделаем вот что - пусть скрипт прогонится оп папке test и пронумерует фотографии как видит - на что они больше похожи, а что не опознает - пронумерует как 00

---

### 🤖 **Assistant** — 2026-08-13 22:09:02

Да. И это, на мой взгляд, **правильнее для следующего этапа**.

Сейчас `patch_embeddings` дают большой выигрыш по точности, но для твоей задачи они действительно слишком тяжёлые. Мы можем сделать режим **классификации папки `test` только по обычным DINOv2 image embeddings**, без хранения patch-токенов.

### Что предлагаю сделать

Скрипт будет:

1. Брать все фотографии из:
   ```bash
   data/input/test/
   ```

2. Для каждой фотографии получать обычный **768-мерный DINOv2 embedding**.

3. Сравнивать её со слепками:
   ```text
   78_v33
   79_v33
   80_v33
   81_v33
   82_v33
   83_v33
   ```

4. Если уверенно похожа на один из слепков — **переименовывать/копировать** фотографию с соответствующим номером.

   Например:

   ```text
   IMG_001.jpg  → 78.jpg
   IMG_002.jpg  → 81.jpg
   IMG_003.jpg  → 00.jpg
   IMG_004.jpg  → 83.jpg
   ```

   Но я бы сделал безопаснее:

   ```text
   78_001.jpg
   78_002.jpg
   81_001.jpg
   00_001.jpg
   ```

5. Если модель не уверена — ставить:
   ```text
   00
   ```

### Причём важный момент

По твоему текущему выводу видно, что **просто `score > X` недостаточно**.

Например:

```text
Ленина 125-127 А (1)
79 = 0.8453
81 = 0.8431
margin = 0.0023
```

Очевидно, что это не уверенное распознавание, несмотря на высокий абсолютный score.

А вот:

```text
Добровольского 17 А (37)
82 = 0.9571
80 = 0.8362
margin = 0.1210
```

это уже очень хороший результат.

Поэтому для автоматической раскладки я предлагаю использовать **двойной критерий**:

```text
SCORE >= порог
        И
MARGIN >= порог
```

Например первоначально:

```text
SCORE  >= 0.82
MARGIN >= 0.035
```

а всё остальное:

```text
00
```

Но **порог я бы не зашивал окончательно**. Лучше сделать его параметрами командной строки, чтобы мы могли быстро прогнать `test` с разными значениями.

---

### Ещё лучше — не трогать исходные фотографии

Сделаем:

```text
data/input/test/
```

исходники остаются как есть.

Результат:

```text
data/output/test_classified/

├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
└── 83/
```

То есть:

```text
test/
   photo001.jpg
   photo002.jpg
   photo003.jpg
```

после обработки:

```text
test_classified/
   78/
      photo001.jpg
   81/
      photo002.jpg
   00/
      photo003.jpg
```

**Это намного удобнее, чем физически переименовывать исходники.**

И одновременно создаём CSV:

```text
filename,predicted,score,second,margin,status
photo001.jpg,78,0.9475,0.8808,0.0667,CONFIDENT
photo002.jpg,81,0.9359,0.8425,0.0933,CONFIDENT
photo003.jpg,00,0.8453,0.8431,0.0022,AMBIGUOUS
```

Так мы потом сможем анализировать ошибки.

### И главное

**Новые patch-слепки создавать вообще не будем.**

Используем существующие:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
```

и только:

```text
centroid.npy
embeddings.npy
representatives.npy
faiss.index
metadata.json
```

без:

```text
patch_embeddings.npy
patch_centroid.npy
patch_representatives.npy
```

Это как раз позволит держать базу слепков относительно компактной.

---

Я предлагаю сделать это **отдельной командой**, например:

```bash
uv run scene-fingerprint classify-test \
    --input data/input/test \
    --output data/output/test_classified \
    --score 0.82 \
    --margin 0.035
```

И получить в конце примерно:

```text
=== CLASSIFICATION SUMMARY ===

78 : 37
79 : 24
80 : 18
81 : 42
82 : 31
83 : 29
00 : 16

TOTAL: 197
```

Причём `00` будет означать именно **«не удалось достаточно уверенно определить»**, а не «похож на слепок 00».

**Да, я бы сейчас именно так и переделал проект.** Это позволит отказаться от огромных patch-слепков для рабочего классификатора, сохранив patch-анализ как отдельный исследовательский режим.

---

### 👤 **User** — 2026-08-14 23:08:30

я добавил 84 -95 в data и новые фото в test

---

### 🤖 **Assistant** — 2026-08-14 23:08:30

Отлично. Тогда сейчас у нас база уже:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
...
95_v33
```

и новые фотографии в:

```bash
data/input/test/
```

Я бы **пока не создавал patch-слепки 84–95**. Сначала проверим, насколько хорошо обычные `embeddings.npy` различают все **18 адресов (78–95)**.

Следующий шаг — сделать классификатор `test`, который автоматически обнаружит все `*_v33` в `data/fingerprints/`, прогонит весь `test` и разложит фотографии:

```text
data/output/test_classified/

├── 00/
├── 78/
├── 79/
├── 80/
...
├── 94/
└── 95/
```

При этом исходный `test` **не трогаем**.

И обязательно сохраним:

```text
classification.csv
```

с:

```text
файл
результат
score
second_score
margin
status
```

### Важный момент

Я бы сделал ещё одну вещь: **не использовать заранее заданный список 78–95**.

Скрипт сам выполнит:

```bash
find data/fingerprints -maxdepth 1 -type d -name '*_v33'
```

и увидит актуальную базу.

То есть завтра ты добавишь:

```text
96_v33
97_v33
98_v33
```

и классификатор автоматически начнёт их учитывать.

---

Но прежде чем писать новый код, лучше посмотреть **как именно сейчас устроен твой `recognizer.py` / CLI**, чтобы не сломать уже работающий `v33`.

Дай мне вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/fingerprints -maxdepth 1 -type d -name '*_v33' -printf '%f\n' | sort -V

echo "===================="

find data/input/test -maxdepth 1 -type f | wc -l

echo "===================="

sed -n '1,260p' app/core/recognizer.py

echo "===================="

sed -n '1,260p' app/cli.py
```

Если `app/cli.py` у тебя называется иначе — покажи:

```bash
find app -maxdepth 2 -type f | sort
```

**После этого я дам готовую команду/скрипт именно под твою текущую версию проекта**, без переделки уже работающего `v33`.

---

### 👤 **User** — 2026-08-14 23:10:52

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

find data/fingerprints -maxdepth 1 -type d -name '*_v33' -printf '%f\n' | sort -V

echo "===================="

find data/input/test -maxdepth 1 -type f | wc -l

echo "===================="

sed -n '1,260p' app/core/recognizer.py

echo "===================="

sed -n '1,260p' app/cli.py
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
====================
253
====================
from __future__ import annotations

from pathlib import Path

import numpy as np

from .image import image_files
from .scene_analyzer import SceneAnalyzer

class SceneRecognizer:
    """
    Scene Fingerprint v3.3 compact recognizer.

    Uses:
        global
        environment
        color
        spatial

    Does NOT use:
        DINO patch tokens

    Recognition decision uses:
        absolute score
        margin to second-best candidate
    """

    VERSION = "3.3"

    HIGH_SCORE = 0.90
    PROBABLE_SCORE = 0.80

    HIGH_MARGIN = 0.03
    PROBABLE_MARGIN = 0.015

    def __init__(
        self,
        settings,
        embedder,
        manager,
    ):
        self.settings = settings
        self.embedder = embedder
        self.manager = manager

        self.analyzer = SceneAnalyzer(
            embedder,
            manager,
        )

    @classmethod
    def _confidence(
        cls,
        score,
        margin,
    ):
        score = float(score)
        margin = float(margin)

        if (
            score >= cls.HIGH_SCORE
            and margin >= cls.HIGH_MARGIN
        ):
            return "HIGH"

        if (
            score >= cls.PROBABLE_SCORE
            and margin >= cls.PROBABLE_MARGIN
        ):
            return "PROBABLE"

        if score >= cls.PROBABLE_SCORE:
            return "AMBIGUOUS"

        return "NO_MATCH"

    @staticmethod
    def _status_from_confidence(
        confidence,
    ):
        if confidence == "HIGH":
            return "CONFIDENT"

        if confidence == "PROBABLE":
            return "PROBABLE_MATCH"

        if confidence == "AMBIGUOUS":
            return "AMBIGUOUS"

        return "NO_MATCH"

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        folder = Path(folder)

        paths = image_files(
            folder
        )

        if not paths:
            return []

        print(
            f"[Recognizer] "
            f"Query images: {len(paths)}"
        )

        fingerprints = []

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            try:
                data = self.manager.load(
                    fingerprint_id
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:

                print(
                    f"[Recognizer] SKIP old "
                    f"fingerprint "
                    f"{fingerprint_id}"
                )

                continue

            fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )

        if not fingerprints:
            raise ValueError(
                "No compatible v3.3 compact "
                "fingerprints found."
            )
  print(
            "[Recognizer] Fingerprints: "
            + ", ".join(
                fp_id
                for fp_id, _ in fingerprints
            )
        )

        # One DINO pass for all query images.
        queries = self.embedder.embed_paths(
            paths
        )

        queries = np.asarray(
            queries,
            dtype=np.float32,
        )

        if queries.ndim == 1:
            queries = queries.reshape(
                1,
                -1,
            )

        results = []

        for path, query_embedding in zip(
            paths,
            queries,
        ):
            ranked = []

            for fingerprint_id, data in fingerprints:

                # First use the analyzer.
                # This calculates the full v3.3 score.
                try:
                    score = self.analyzer.compare(
                        Path(path),
                        fingerprint_id,
                    )

                except (
                    FileNotFoundError,
                    ValueError,
                    OSError,
                ) as exc:

                    print(
                        f"[Recognizer] SKIP "
                        f"{fingerprint_id} "
                        f"for "
                        f"{Path(path).name}: "
                        f"{exc}"
                    )

                    continue

                ranked.append(
                    {
                        "id": fingerprint_id,

                        "score": float(
                            score.get(
                                "final_score",
                                0.0,
                            )
                        ),

                        "global": float(
                            score.get(
                                "global_score",
                                0.0,
                            )
                        ),

                        "environment": float(
                            score.get(
                                "environment_score",
                                0.0,
                            )
                        ),

                        "color": float(
                            score.get(
                                "color_score",
                                0.0,
                            )
                        ),
====================
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer
from app.core.scene_analyzer import SceneAnalyzer

def build_parser():
    parser = argparse.ArgumentParser(
        prog="scene-fingerprint",
        description=(
            "Scene fingerprinting and "
            "recognition v3.3 compact"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    create_parser = subparsers.add_parser(
        "create",
        help="Create v3.3 compact fingerprint",
    )

    create_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    create_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )
 # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze one fingerprint",
    )

    analyze_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    analyze_parser.add_argument(
        "--fingerprint",
        required=True,
        help="Fingerprint ID",
    )

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    recognize_parser = subparsers.add_parser(
        "recognize",
        help="Recognize images",
    )

    recognize_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    recognize_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of candidates",
    )

    recognize_parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Minimum absolute match score",
    )

    recognize_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON",
    )

    return parser

def print_analyze_result(
    path,
    result,
):
    print()
    print(
        f"## {Path(path).name}"
    )
    print()

    print(
        f"GLOBAL        "
        f"{result['global_score']:.4f}"
    )

    print(
        f"BEST IMAGE    "
        f"{result['best_image_score']:.4f}"
    )

    print(
        "PATCH         "
        "0.0000 (DISABLED)"
    )

    print(
        f"COLOR         "
        f"{result['color_score']:.4f}"
    )

    print(
        f"SPATIAL       "
        f"{result['spatial_score']:.4f}"
    )

    print(
        f"ENVIRONMENT   "
        f"{result['environment_score']:.4f}"
    )

    print(
        f"FINAL         "
        f"{result['final_score']:.4f}"
    )

    print(
        f"BEST MATCH    "
        f"{result['best_image']}"
    )

def print_recognition_result(
    result,
):
    filename = Path(
        result["file"]
    ).name

    print()
    print(
        f"## {filename}"
    )
    print()

    best_id = result.get(
        "best_id"
    )

    score = float(
        result.get(
            "score",
            0.0,
        )
    )

    second_score = float(
        result.get(
            "second_score",
            0.0,
        )
    )

    margin = float(
        result.get(
            "margin",
            0.0,
        )
    )

    confidence = result.get(
        "confidence",
        "NO_MATCH",
    )

    status = result.get(
        "status",
        "NO_MATCH",
    )

    print(
        f"MATCH        "
        f"{best_id or 'NONE'}"
    )

    print(
        f"SCORE        "
        f"{score:.4f}"
    )

    print(
        f"SECOND       "
        f"{second_score:.4f}"
    )

    print(
        f"MARGIN       "
        f"{margin:.4f}"
    )

    print(
        f"CONFIDENCE   "
        f"{confidence}"
    )

    print(
        f"STATUS       "
        f"{status}"
    )

    best_image = result.get(
        "best_image"
    )

    if best_image:
        print(
            f"BEST IMAGE   "
            f"{best_image}"
        )

    candidates = result.get(
        "candidates",
        [],
    )

    if candidates:
        print()
        print(
            "TOP CANDIDATES"
        )

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):
            print(
                f"{index}. "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:10:53

Да, теперь видно структуру. И есть важный момент: **у тебя сейчас реально найдены только `78_v33`–`85_v33`**, а `86–95` команда `find` не показывает.

То есть сначала проверь, что именно лежит в `data/fingerprints`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/fingerprints -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -30
```

И отдельно:

```bash
for n in {84..95}; do
    echo -n "$n : "
    test -d "data/fingerprints/${n}_v33" && echo "OK" || echo "MISSING"
done
```

### А вот с классификатором всё хорошо

Твой `recognizer.py` уже **v3.3 compact** и прямо говорит:

> Does NOT use DINO patch tokens

То есть **patch-файлы вообще не нужны для этого режима**.

Более того, текущий алгоритм уже делает именно то, что нам нужно:

```text
DINO global
      ↓
v3.3 analyzer
      ↓
78_v33
79_v33
...
85_v33
      ↓
score + margin
      ↓
CONFIDENT / PROBABLE / AMBIGUOUS / NO_MATCH
```

Поэтому **не надо сейчас переписывать `recognizer.py`**.

Нам нужен только небольшой новый режим `classify-test`, который возьмёт существующий результат `recognize_folder()` и физически разложит фотографии.

---

## Предлагаю сделать безопасно

Не переименовывать оригиналы.

Из:

```text
data/input/test/
```

сделать:

```text
data/output/test_classified/
```

Например:

```text
test_classified/
├── 00/
│   ├── IMG_001.JPG
│   └── IMG_037.JPG
├── 78/
│   ├── IMG_002.JPG
│   └── IMG_003.JPG
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
└── 85/
```

При этом **`00` получат все `NO_MATCH` и `AMBIGUOUS`**.

Это как раз соответствует твоей задаче:

> «на что они больше похожи, а что не опознает — пронумерует как 00».

### Но есть одна тонкость

Например:

```text
Ленина 125-127 А (1)

79 = 0.8453
81 = 0.8431
margin = 0.0023
```

Технически `79` первое, но разница всего `0.0023`.

Я бы в классификации **не отправлял такую фотографию в 79**, а отправлял в `00`.

А:

```text
82 = 0.9571
80 = 0.8362
margin = 0.1210
```

идёт в `82`.

То есть используем уже имеющуюся систему confidence.

---

### Сейчас сделай только проверку 84–95

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in {84..95}; do
    echo -n "$n : "
    if [ -d "data/fingerprints/${n}_v33" ]; then
        echo "OK"
    else
        echo "MISSING"
    fi
done
```

И пришли вывод.

**После этого дам тебе готовый `classify_test.py` + команду запуска**, причём он будет автоматически подхватывать **все существующие `*_v33`**, так что в следующий раз при добавлении `96`, `97` и т.д. код менять вообще не придётся.

---

### 👤 **User** — 2026-08-14 23:11:18

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

find data/fingerprints -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -30
78
78_patch
78_v3
78_v31
78_v32
78_v33
79
79_v31
79_v32
79_v33
80
80_v31
80_v32
80_v33
81
81_v31
81_v32
81_v33
82
82_v31
82_v32
82_v33
83_v33
84_v33
85_v33
fingerprints
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ for n in {84..95}; do
    echo -n "$n : "
    test -d "data/fingerprints/${n}_v33" && echo "OK" || echo "MISSING"
done
84 : OK
85 : OK
86 : MISSING
87 : MISSING
88 : MISSING
89 : MISSING
90 : MISSING
91 : MISSING
92 : MISSING
93 : MISSING
94 : MISSING
95 : MISSING
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:11:21

Да, теперь картина ясна.

Фактически сейчас база **8 слепков**:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
```

`86-95` пока **не созданы как `*_v33`**, поэтому текущий recognizer их не увидит.

И я бы сейчас **не трогал существующую систему v3.3**. Она уже делает нужную работу и, судя по результатам выше, достаточно хорошо различает адреса.

### Следующий шаг

Делаем отдельную команду:

```bash
uv run scene-fingerprint classify-test
```

Она будет:

- брать `data/input/test`;
- автоматически находить **все `*_v33`**;
- использовать существующий `SceneRecognizer`;
- **не использовать patch embeddings**;
- для уверенных совпадений класть фото в папку соответствующего номера;
- для `AMBIGUOUS` и `NO_MATCH` класть в `00`;
- исходные фотографии не изменять;
- создавать CSV с результатами.

Например:

```text
data/output/test_classified/
├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
└── 85/
```

И поскольку у тебя сейчас **253 фотографии**, в конце получим что-то вроде:

```text
78 : 31
79 : 27
80 : 35
81 : 42
82 : 29
83 : 38
84 : 21
85 : 18
00 : 12

TOTAL : 253
```

Причём я предлагаю **не считать `PROBABLE` автоматически правильным**. Для первого теста:

```text
CONFIDENT       → соответствующий номер
PROBABLE        → соответствующий номер
AMBIGUOUS       → 00
NO_MATCH        → 00
```

Это даст нам максимально чистую первую раскладку.

---

### Но есть ещё один важный момент

Сейчас в `recognizer.py` уже есть:

```python
threshold=0.65
```

но фактическое решение `CONFIDENT / PROBABLE / AMBIGUOUS / NO_MATCH` определяется `_confidence()`:

```python
HIGH_SCORE = 0.90
PROBABLE_SCORE = 0.80

HIGH_MARGIN = 0.03
PROBABLE_MARGIN = 0.015
```

То есть наша классификация будет опираться **именно на эти существующие правила**, а не придумывать новые.

Это особенно важно для таких случаев:

```text
79 = 0.8453
81 = 0.8431
margin = 0.0023
```

→ `00`

и:

```text
82 = 0.9571
80 = 0.8362
margin = 0.1210
```

→ `82`

---

**Я готов дать тебе сейчас готовый файл `classify_test.py` и команды для установки его в проект.** Причём сделаем его так, чтобы потом добавление `86_v33`, `87_v33` и т.д. не требовало изменения кода.

---

### 👤 **User** — 2026-08-14 23:11:56

Give me the ready file classify_test.py

---

### 🤖 **Assistant** — 2026-08-14 23:11:57

Да. Создай файл `classify_test.py` в корне проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
nano classify_test.py
```

Вставь туда:

```python
#!/usr/bin/env python3

from __future__ import annotations

import csv
import shutil
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

TEST_DIR = PROJECT_ROOT / "data" / "input" / "test"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "test_classified"

CSV_FILE = OUTPUT_DIR / "results.csv"

# ============================================================
# SETTINGS
# ============================================================

TOP_K = 5

# Existing recognizer settings.
THRESHOLD = 0.65

# Classification:
# HIGH       -> match
# PROBABLE   -> match
# AMBIGUOUS  -> 00
# NO_MATCH   -> 00

# ============================================================
# HELPERS
# ============================================================

def get_image_files(folder: Path) -> list[Path]:
    extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
    }

    return sorted(
        [
            p
            for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower() in extensions
        ],
        key=lambda p: p.name.lower(),
    )

def get_v33_fingerprints() -> list[str]:
    """
    Automatically finds all fingerprints like:

        78_v33
        79_v33
        80_v33
        ...

    No need to edit this script when new fingerprints
    are added.
    """

    fingerprint_root = (
        PROJECT_ROOT
        / "data"
        / "fingerprints"
    )

    result = []

    for path in fingerprint_root.iterdir():

        if not path.is_dir():
            continue

        name = path.name

        if not name.endswith("_v33"):
            continue

        number = name[:-4]

        if not number.isdigit():
            continue

        result.append(name)

    # Numerical sorting:
    # 78_v33, 79_v33, ..., 100_v33
    result.sort(
        key=lambda x: int(x.split("_")[0])
    )

    return result

def prepare_output():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Create 00 and all fingerprint folders.
    folders = ["00"]

    for fp in get_v33_fingerprints():

        number = fp.split("_")[0]

        if number not in folders:
            folders.append(number)

    for folder in folders:

        (
            OUTPUT_DIR / folder
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

def safe_copy(
    source: Path,
    destination_dir: Path,
):
    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        destination_dir
        / source.name
    )

    # Prevent overwriting if duplicate filenames exist.
    if destination.exists():

        stem = source.stem
        suffix = source.suffix

        counter = 1

        while True:

            destination = (
                destination_dir
                / f"{stem}_{counter}{suffix}"
            )

            if not destination.exists():
                break

            counter += 1

    shutil.copy2(
        source,
        destination,
    )

    return destination

# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SCENE FINGERPRINT — TEST CLASSIFIER")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # Check test folder
    # --------------------------------------------------------

    if not TEST_DIR.exists():

        print(
            f"[ERROR] Test folder not found:\n"
            f"{TEST_DIR}"
        )

        return 1

    images = get_image_files(
        TEST_DIR
    )

    if not images:

        print(
            f"[ERROR] No images found in:\n"
            f"{TEST_DIR}"
        )

        return 1

    print(
        f"[Input] Images: {len(images)}"
    )

    # --------------------------------------------------------
    # Find fingerprints
    # --------------------------------------------------------

    fingerprint_ids = (
        get_v33_fingerprints()
    )

    if not fingerprint_ids:

        print()
        print(
            "[ERROR] No *_v33 fingerprints found."
        )

        return 1

    print(
        f"[Database] Fingerprints: "
        f"{len(fingerprint_ids)}"
    )

    print(
        "[Database] "
        + ", ".join(
            fingerprint_ids
        )
    )

    print()

    # --------------------------------------------------------
    # Prepare output
    # --------------------------------------------------------

    prepare_output()

    print(
        f"[Output] {OUTPUT_DIR}"
    )

    print()

    # --------------------------------------------------------
    # Initialize model
    # --------------------------------------------------------

    print(
        "[Model] Loading DINO..."
    )

    embedder = SceneEmbedder(
        settings
    )

    manager = FingerprintManager(
        settings
    )

    recognizer = SceneRecognizer(
        settings,
        embedder,
        manager,
    )

    print(
        "[Model] Ready."
    )

    print()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Use the existing recognizer.
    # It uses compact v3.3 fingerprints
    # and DOES NOT use patch tokens.
    # --------------------------------------------------------

    print(
        "[Recognizer] Starting recognition..."
    )

    results = recognizer.recognize_folder(
        TEST_DIR,
        top_k=TOP_K,
        threshold=THRESHOLD,
    )

    print()

    # --------------------------------------------------------
    # Create lookup by filename
    # --------------------------------------------------------

    results_by_file = {}

    for result in results:

        file_path = Path(
            result["file"]
        )

        results_by_file[
            file_path.name
        ] = result

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    statistics = {}

    for fp in fingerprint_ids:

        number = fp.split("_")[0]

        statistics[number] = 0

    statistics["00"] = 0

    matched = 0
    no_match = 0

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    csv_rows = []

    # --------------------------------------------------------
    # Classify every image
    # --------------------------------------------------------

    for index, image in enumerate(
        images,
        start=1,
    ):

        result = results_by_file.get(
            image.name
        )

        if result is None:

            # Something went wrong or image
            # was skipped by recognizer.
            classification = "00"

            best_id = ""
            score = 0.0
            second_score = 0.0
            margin = 0.0
            confidence = "NO_MATCH"
            status = "NO_MATCH"
            best_image = ""

        else:

            best_id = result.get(
                "best_id"
            )

            score = float(
                result.get(
                    "score",
                    0.0,
                )
            )

            second_score = float(
                result.get(
                    "second_score",
                    0.0,
                )
            )

            margin = float(
                result.get(
                    "margin",
                    0.0,
                )
            )

            confidence = result.get(
                "confidence",
                "NO_MATCH",
            )

            status = result.get(
                "status",
                "NO_MATCH",
            )

            best_image = result.get(
                "best_image",
                "",
            )

            # ------------------------------------------------
            # FINAL CLASSIFICATION
            # ------------------------------------------------
            #
            # HIGH / PROBABLE:
            #     -> fingerprint number
            #
            # AMBIGUOUS / NO_MATCH:
            #     -> 00
            #
            # ------------------------------------------------

            if confidence in {
                "HIGH",
                "PROBABLE",
            } and best_id:

                classification = (
                    str(best_id)
                    .replace("_v33", "")
                )

                matched += 1

            else:

                classification = "00"

                no_match += 1

        # ----------------------------------------------------
        # Copy image
        # ----------------------------------------------------

        destination_dir = (
            OUTPUT_DIR
            / classification
        )

        destination = safe_copy(
            image,
            destination_dir,
        )

        statistics.setdefault(
            classification,
            0,
        )

        statistics[
            classification
        ] += 1

        # ----------------------------------------------------
        # CSV row
        # ----------------------------------------------------

        csv_rows.append(
            {
                "file": image.name,
                "classification": classification,
                "best_id": best_id or "",
                "score": f"{score:.6f}",
                "second_score": (
                    f"{second_score:.6f}"
                ),
                "margin": f"{margin:.6f}",
                "confidence": confidence,
                "status": status,
                "best_image": best_image or "",
                "output": str(
                    destination.relative_to(
                        OUTPUT_DIR
                    )
                ),
            }
        )

        # ----------------------------------------------------
        # Console
        # ----------------------------------------------------

        print(
            f"[{index:03d}/{len(images):03d}] "
            f"{image.name} "
            f"-> {classification:>2} "
            f"score={score:.4f} "
            f"margin={margin:.4f} "
            f"{confidence}"
        )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    with CSV_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "classification",
                "best_id",
                "score",
                "second_score",
                "margin",
                "confidence",
                "status",
                "best_image",
                "output",
            ],
        )

        writer.writeheader()

        writer.writerows(
            csv_rows
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print()

    # Numerical order
    sorted_statistics = sorted(
        statistics.items(),
        key=lambda item: (
            -1
            if item[0] == "00"
            else int(item[0])
        ),
    )

    for number, count in sorted_statistics:

        if count == 0:
            continue

        print(
            f"{number:>3} : {count}"
        )

    print()
    print(
        f"TOTAL       : {len(images)}"
    )

    print(
        f"MATCHED     : {matched}"
    )

    print(
        f"00 / UNKNOWN: {no_match}"
    )

    print()
    print(
        f"[CSV] {CSV_FILE}"
    )

    print(
        f"[OUTPUT] {OUTPUT_DIR}"
    )

    print()
    print("=" * 70)

    return 0

if __name__ == "__main__":
    raise SystemExit(
        main()
    )
```

После сохранения:

```bash
chmod +x classify_test.py
```

И запуск:

```bash
uv run python classify_test.py
```

### Что получишь

Оригиналы останутся нетронутыми:

```text
data/input/test/
```

А результат появится здесь:

```text
data/output/test_classified/
```

Например:

```text
test_classified/
├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
└── 85/
```

И дополнительно:

```text
data/output/test_classified/results.csv
```

В CSV будет для **каждой фотографии**:

```text
file
classification
best_id
score
second_score
margin
confidence
status
best_image
output
```

### Важный момент

Скрипт **автоматически обнаруживает `*_v33`**, поэтому когда ты создашь:

```text
86_v33
87_v33
...
95_v33
```

ничего в `classify_test.py` менять не понадобится.

Сейчас он увидит именно:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
```

и классифицирует твои **253 фотографии** по этим 8 категориям + `00`.

**Patch-файлы (`78_patch` и т.п.) вообще не используются.**

---

### 👤 **User** — 2026-08-14 23:12:55

Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 2016.43it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/classify_test.py", line 608, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/classify_test.py", line 282, in main
    manager = FingerprintManager(
              ^^^^^^^^^^^^^^^^^^^
TypeError: FingerprintManager.__init__() missing 1 required positional argument: 'embedder'

---

### 🤖 **Assistant** — 2026-08-14 23:12:56

Да, это моя ошибка в `classify_test.py`. В твоей версии `FingerprintManager` конструктор требует **три аргумента**, включая `embedder`.

Сейчас у нас:

```python
manager = FingerprintManager(
    settings
)
```

Нужно:

```python
manager = FingerprintManager(
    settings,
    embedder,
)
```

### Исправь

Открой файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
nano classify_test.py
```

Найди:

```python
manager = FingerprintManager(
    settings
)
```

и замени на:

```python
manager = FingerprintManager(
    settings,
    embedder,
)
```

После этого снова:

```bash
uv run python classify_test.py
```

### Почему это произошло

Твой `SceneRecognizer` уже показывает правильный вариант:

```python
self.analyzer = SceneAnalyzer(
    embedder,
    manager,
)
```

А сам `FingerprintManager` в текущей версии проекта, судя по ошибке, имеет примерно такой конструктор:

```python
FingerprintManager(settings, embedder)
```

То есть модель `embedder` должна передаваться и менеджеру.

**Ничего пересоздавать из fingerprint не надо.** `78_v33 ... 85_v33` остаются как есть, patch тоже не используется.

Если после этой правки появится следующая ошибка — **не меняй ничего наугад**, просто пришли traceback целиком. Доведём этот запуск до классификации 253 фотографий.

---

### 👤 **User** — 2026-08-14 23:28:35

давай сделаем слепки новых адресов и прогоним распознавние заново, ориентируясь на первого кандидата

---

### 🤖 **Assistant** — 2026-08-14 23:28:41

Да. Я бы сейчас сделал **чистый цикл v3.3 без patch**:

1. Создаём компактные слепки новых адресов **84–95** из соответствующих папок `data/input/84 ... 95`.
2. Старые `*_v33` не трогаем.
3. Прогоняем `data/input/test`.
4. Для каждой фотографии берём **первого кандидата** — максимальный `final_score`.
5. Если первый кандидат слишком слабый — ставим `00`.
6. Фотографии физически раскладываем по папкам:
   ```text
   data/output/test_classified/
   ├── 00/
   ├── 84/
   ├── 85/
   ├── 86/
   ...
   └── 95/
   ```
7. При этом сохраняем CSV с оценками, чтобы потом посмотреть, **насколько уверенно** модель определяла каждый адрес.

Но сначала важный момент: сейчас у тебя подтверждены только `84_v33` и `85_v33`, а **86–95 ещё отсутствуют**. Поэтому сначала их создаём.

### Шаг 1 — проверить исходные папки

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in {84..95}; do
    echo -n "$n : "
    if [ -d "data/input/$n" ]; then
        find "data/input/$n" -maxdepth 1 -type f | wc -l
    else
        echo "NO FOLDER"
    fi
done
```

Нам должно показать примерно:

```text
84 : ...
85 : ...
86 : ...
87 : ...
...
95 : ...
```

### Шаг 2 — создаём новые слепки

Если папки `84–95` действительно существуют, можно одним циклом:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in {84..95}; do
    if [ -d "data/input/$n" ]; then
        echo
        echo "========================================"
        echo "CREATING FINGERPRINT ${n}_v33"
        echo "========================================"

        uv run scene-fingerprint create \
            "${n}_v33" \
            "data/input/$n"

    else
        echo "SKIP $n — data/input/$n does not exist"
    fi
done
```

**Это именно compact v3.3**, поэтому patch embeddings не должны создаваться. У тебя уже видно:

```text
[SceneEmbedder] patch extraction=DISABLED (compact)
```

Это то, что нам сейчас нужно.

---

После создания проверим:

```bash
find data/fingerprints -maxdepth 1 -type d -name '*_v33' -printf '%f\n' | sort -V
```

Должно получиться:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
86_v33
87_v33
88_v33
89_v33
90_v33
91_v33
92_v33
93_v33
94_v33
95_v33
```

**После этого я дам тебе готовый `classify_test.py` именно под эту схему**, который будет ориентироваться на первого кандидата и раскладывать 253 фотографии по адресам, а `00` использовать для нераспознанных.

И я бы сразу сделал ещё одну полезную вещь: сохранять для каждой фотографии не только `first candidate`, но и **score + second candidate + margin**. Тогда мы сможем потом быстро подобрать порог для `00`, не прогоняя DINO заново.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)

---

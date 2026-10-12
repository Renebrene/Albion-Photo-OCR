## СЕССИЯ: LORA

**Создано:** 2026-08-07 22:33:24
**Обновлено:** 2026-08-19 17:08:04
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c)

---

### 🤖 **Assistant** — 2026-08-12 22:22:45

> **Assessing Scene Analyzer Similarity Weights**
>
> 
>
> Worked for a few seconds

Да. Я посмотрел **твой текущий `scene_analyzer.py`** и поискал предыдущие рабочие версии выше в истории.

### Вывод

Твой текущий `scene_analyzer.py` **в целом правильный для v3.3 compact**, и я бы сейчас его **не заменял**. Он соответствует той версии, на которой ты получил `78_v33 ... 82_v33` и результаты `0.94-0.97`. В истории есть практически тот же v3.3-файл с теми же дескрипторами и весами. `Pasted text.txt` `Pasted text.txt`

Но я нашёл **одну важную вещь**, которую стоит исправить.

## 1. Главная проблема - `representatives` сейчас фактически не используются

В `SceneAnalyzer.compare()`:

```python
image_scores = data["embeddings"] @ query_global
best_index = int(np.argmax(image_scores))
```

Это нормально: ищется лучший кадр среди **всех** изображений fingerprint.

Но для `environment`, `color`, `spatial` используется:

```python
data["environment_embeddings"]
data["color_embeddings"]
data["spatial_embeddings"]
```

и затем:

```python
k = max(3, int(len(scores) * 0.10))
```

То есть берётся **верхние 10% всех изображений**, а не 16 representative images.

Это не ошибка, но название `representatives` в fingerprint тогда вводит в заблуждение.

---

## 2. Более серьёзный момент - `environment` у тебя слишком похож на color + brightness

Текущий descriptor:

```text
8 × 8 × 10 = 640
```

содержит:

- HSV mean
- HSV std
- grayscale mean
- grayscale std
- edge mean
- edge std

То есть он действительно описывает **структуру сцены**, но значительная часть descriptor - цвет/яркость.

А потом ещё отдельно:

```text
color = 7%
```

Поэтому:

```text
global       70%
environment  20%
color         7%
spatial       3%
```

фактически несколько раз учитывает похожую информацию.

Это не критично, но для дальнейших экспериментов с **83, 84, 85** я бы пока это **не трогал**.

Почему?

Потому что сейчас нам нужна **контрольная стабильная v3.3**, а не очередная версия, где одновременно меняются:

- descriptor;
- weights;
- fingerprint;
- recognizer.

---

# 3. Что я предлагаю сейчас

**83, 84, 85 оставляем именно для экспериментов.**

А `78-82` используем как контрольную группу:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
```

И **не пересоздаём их**.

Для экспериментов:

```text
83_v33
84_v33
85_v33
```

Можно создавать разные варианты.

Например:

```text
83_v33_env
84_v33_env2
85_v33_test
```

или лучше, если хотим системно:

```text
83_v33_A
84_v33_B
85_v33_C
```

---

# 4. Но есть ещё одна вещь, которую я хочу исправить перед экспериментами

Твой `recognizer.py` сейчас делает:

```python
queries = self.embedder.embed_paths(paths)
```

а потом для **каждого fingerprint**:

```python
self.analyzer.compare(
    Path(path),
    fingerprint_id,
)
```

а `compare()` снова делает:

```python
self.embedder.embed_paths(
    [Path(image_path)]
)[0]
```

То есть DINO для одного query изображения вычисляется:

> **один раз заранее + ещё по одному разу на каждый fingerprint.**

При 5 fingerprints это примерно:

```text
9 query images × 6 DINO inference
```

вместо:

```text
9 query images × 1 DINO inference
```

Это **не влияет на правильность результата**, но совершенно лишнее.

И это особенно важно, когда у тебя станет:

```text
78
79
80
81
82
83
84
85
...
```

---

# 5. Поэтому я бы сейчас сделал v3.3.1, но не менял математику

То есть:

### Оставляем абсолютно неизменным:

```text
DINOv2 ViT-B/14
768
patch = OFF
global = 0.70
environment = 0.20
color = 0.07
spatial = 0.03
```

И существующий `SceneAnalyzer` оставляем как эталон. `Pasted text.txt`

### Меняем только:

**Recognizer → передаёт уже вычисленный global embedding в Analyzer.**

Тогда результат должен быть **математически тем же**, но система станет значительно быстрее.

---

## И ещё один важный момент по 83/84/85

Я бы **не включал их автоматически в основную базу теста**, если они экспериментальные.

Сейчас:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
```

- контроль.

А:

```text
83
84
85
```

- экспериментальные fingerprint'ы.

Иначе новый fingerprint может случайно начать выигрывать у старых, и мы потеряем чистоту эксперимента.

---

### Мой вердикт по твоему `scene_analyzer.py`

**Оставляем. Не переписываем.**

Он соответствует рабочей v3.3 compact и именно на нём получены твои текущие результаты. `Pasted text.txt`

Следующий шаг я бы сделал такой:

**1. Исправляем только лишние повторные DINO inference в `recognizer.py`.**  
**2. Проверяем, что результаты 001-009 абсолютно те же.**  
**3. После этого начинаем экспериментировать с 83/84/85.**

И только после этого будем решать, нужна ли **v3.4** с изменением самой модели оценки сцены.

---

### 👤 **User** — 2026-08-12 22:24:42

83/84/85 - они равноправны относительно предыдущих, это просто рекламные конструкции по другним адреса. можно их использовать вместпе со всеми, чтобы лучше находить разницу

---

### 🤖 **Assistant** — 2026-08-12 22:24:43

Да. **83, 84 и 85 не будем выделять в отдельную экспериментальную группу** — они должны участвовать в распознавании **наравне с 78–82**.

И это даже полезно: у нас теперь **8 полноценных сцен**:

`78, 79, 80, 81, 82, 83, 84, 85`

Для v3.3 я бы зафиксировал логику именно так:

- все `*_v33` участвуют одинаково;
- `78_v33 ... 85_v33` — единый набор fingerprints;
- старые `v3.2`, `v3.1` и неполные fingerprints игнорируются;
- `global` + `environment` + `color` + `spatial`;
- patch tokens **не используются**;
- `margin` считается относительно **второго лучшего из всех 8**;
- `83/84/85` должны реально влиять на ranking, а не просто отображаться;
- особенно интересны случаи, где раньше `78/79/80` были близки — новые сцены могут дать более правильное разделение.

Но есть важный момент: **не надо сейчас переписывать `scene_analyzer.py` вслепую**. Ты сказал, что у тебя он уже есть, и в предыдущих сообщениях мы делали несколько вариантов.

### Сейчас сделаем правильно

Покажи мне **текущие четыре файла**, которые реально стоят у тебя на диске:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== scene_analyzer.py ====="
sed -n '1,420p' app/core/scene_analyzer.py

echo
echo "===== recognizer.py ====="
sed -n '1,420p' app/core/recognizer.py

echo
echo "===== fingerprint.py ====="
sed -n '1,500p' app/core/fingerprint.py

echo
echo "===== config.py ====="
sed -n '1,300p' app/core/config.py
```

И отдельно:

```bash
echo "===== FINGERPRINTS ====="
find data/fingerprints -maxdepth 2 -type f | sort
```

### Почему сначала это

По твоему последнему выводу `recognizer.py` уже работает с **v3.3**, и сейчас он видит:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
```

Наша задача — получить:

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

без изменения архитектуры, которая уже дала нормальный результат.

И ещё я хочу проверить одну важную вещь: сейчас `recognizer.py` делает **один DINO pass для query**, но затем для каждого fingerprint вызывает:

```python
self.analyzer.compare(...)
```

То есть потенциально `SceneAnalyzer` может **повторно считать embedding**, что совершенно не нужно и может сильно тормозить. Если это действительно так в твоём текущем `scene_analyzer.py`, я поправлю это в v3.3 compact.

**Пока ничего не удаляй и не пересоздавай.** Сначала посмотрим эти файлы и существующие `83/84/85`. Затем я дам точечные команды для создания `83_v33`, `84_v33`, `85_v33` и контрольный `recognize`.

---

### 👤 **User** — 2026-08-12 22:26:01

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== scene_analyzer.py ====="
sed -n '1,420p' app/core/scene_analyzer.py

echo
echo "===== recognizer.py ====="
sed -n '1,420p' app/core/recognizer.py

echo
echo "===== fingerprint.py ====="
sed -n '1,500p' app/core/fingerprint.py

echo
echo "===== config.py ====="
sed -n '1,300p' app/core/config.py
===== scene_analyzer.py =====
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

class CompactDescriptor:
    """
    Scene Fingerprint v3.3 compact descriptors.

    No DINOv2 patch tokens.

    environment:
        8x8 grid x 10 values = 640 floats

    color:
        HSV histograms = 48 floats

    spatial:
        4x4 grid x 2 values = 32 floats
    """

    GRID = 8
    IMAGE_SIZE = 128

    @staticmethod
    def _load(path: Path):
        image = cv2.imread(
            str(path),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError(
                f"Cannot read image: {path}"
            )

        return cv2.resize(
            image,
            (
                CompactDescriptor.IMAGE_SIZE,
                CompactDescriptor.IMAGE_SIZE,
            ),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def _normalize(vector):
        vector = np.asarray(
            vector,
            dtype=np.float32,
        )

        norm = np.linalg.norm(vector)

        if norm > 0.0:
            vector = vector / norm

        return vector.astype(np.float32)

    @classmethod
    def environment(cls, path: Path):
        image = cls._load(path)

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        ).astype(np.float32)

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        ).astype(np.float32) / 255.0

        gx = cv2.Sobel(
            gray,
            cv2.CV_32F,
            1,
            0,
            ksize=3,
        )

        gy = cv2.Sobel(
            gray,
            cv2.CV_32F,
            0,
            1,
            ksize=3,
        )

        edge = np.clip(
            cv2.magnitude(gx, gy),
            0.0,
            1.0,
        )

        features = []
        size = cls.IMAGE_SIZE

        for gy_idx in range(cls.GRID):
            for gx_idx in range(cls.GRID):

                y1 = gy_idx * size // cls.GRID
                y2 = (gy_idx + 1) * size // cls.GRID

                x1 = gx_idx * size // cls.GRID
                x2 = (gx_idx + 1) * size // cls.GRID

                h = hsv[y1:y2, x1:x2]
                g = gray[y1:y2, x1:x2]
                e = edge[y1:y2, x1:x2]

                features.extend(
                    [
                        float(h[:, :, 0].mean()) / 179.0,
                        float(h[:, :, 1].mean()) / 255.0,
                        float(h[:, :, 2].mean()) / 255.0,

                        float(h[:, :, 0].std()) / 179.0,
                        float(h[:, :, 1].std()) / 255.0,
                        float(h[:, :, 2].std()) / 255.0,

                        float(g.mean()),
                        float(g.std()),

                        float(e.mean()),
                        float(e.std()),
                    ]
                )

        return cls._normalize(
            np.asarray(
                features,
                dtype=np.float32,
            )
        )

    @classmethod
    def color(cls, path: Path):
        image = cls._load(path)

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        hist_h = cv2.calcHist(
            [hsv],
            [0],
            None,
            [16],
            [0, 180],
        )

        hist_s = cv2.calcHist(
            [hsv],
            [1],
            None,
            [16],
            [0, 256],
        )

        hist_v = cv2.calcHist(
            [hsv],
            [2],
            None,
            [16],
            [0, 256],
        )

        descriptor = np.concatenate(
            [
                hist_h.flatten(),
                hist_s.flatten(),
                hist_v.flatten(),
            ]
        ).astype(np.float32)

        return cls._normalize(descriptor)

    @classmethod
    def spatial(cls, path: Path):
        image = cls._load(path)

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        ).astype(np.float32) / 255.0

        descriptor = []

        h, w = gray.shape

        for gy_idx in range(4):
            for gx_idx in range(4):

                y1 = gy_idx * h // 4
                y2 = (gy_idx + 1) * h // 4

                x1 = gx_idx * w // 4
                x2 = (gx_idx + 1) * w // 4

                cell = gray[y1:y2, x1:x2]

                descriptor.extend(
                    [
                        float(cell.mean()),
                        float(cell.std()),
                    ]
                )

        return cls._normalize(
            np.asarray(
                descriptor,
                dtype=np.float32,
            )
        )

class SceneAnalyzer:
    """
    v3.3 compact scene comparison.

    Weights:
        global       0.70
        environment 0.20
        color       0.07
        spatial     0.03

    Patch storage is disabled.
    """

    GLOBAL_WEIGHT = 0.70
    ENVIRONMENT_WEIGHT = 0.20
    COLOR_WEIGHT = 0.07
    SPATIAL_WEIGHT = 0.03

    def __init__(
        self,
        embedder,
        manager,
    ):
        self.embedder = embedder
        self.manager = manager

    @staticmethod
    def cosine(a, b):
        a = np.asarray(
            a,
            dtype=np.float32,
        ).reshape(-1)

        b = np.asarray(
            b,
            dtype=np.float32,
        ).reshape(-1)

        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)

        if na == 0.0 or nb == 0.0:
            return 0.0

        return float(
            np.dot(a, b)
            / (na * nb)
        )

    @staticmethod
    def descriptor_similarity(
        query,
        references,
    ):
        q = np.asarray(
            query,
            dtype=np.float32,
        ).reshape(-1)

        refs = np.asarray(
            references,
            dtype=np.float32,
        )

        if refs.ndim == 1:
            refs = refs.reshape(1, -1)

        if len(refs) == 0:
            return 0.0

        q_norm = np.linalg.norm(q)

        if q_norm == 0.0:
            return 0.0

        q = q / q_norm

        ref_norms = np.linalg.norm(
            refs,
            axis=1,
            keepdims=True,
        )

        ref_norms[
            ref_norms == 0.0
        ] = 1.0

        refs = refs / ref_norms

        scores = refs @ q

        # Strongest 10%, but at least 3 images.
        k = max(
            3,
            int(len(scores) * 0.10),
        )

        k = min(
            k,
            len(scores),
        )

        return float(
            np.mean(
                np.sort(scores)[-k:]
            )
        )

    def compare(
        self,
        image_path: Path,
        fingerprint_id: str,
    ):
        data = self.manager.load(
            fingerprint_id
        )

        query_global = (
            self.embedder.embed_paths(
                [Path(image_path)]
            )[0]
        )

        query_global = np.asarray(
            query_global,
            dtype=np.float32,
        )

        global_score = self.cosine(
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

        best_image_score = float(
            image_scores[best_index]
        )

        image_names = (
            data["metadata"]
            .get(
                "image_names",
                [],
            )
        )

        if best_index < len(image_names):
            best_image = image_names[
                best_index
            ]
        else:
            best_image = str(
                best_index
            )

        query_environment = (
            CompactDescriptor.environment(
                Path(image_path)
            )
        )

        environment_score = (
            self.descriptor_similarity(
                query_environment,
                data[
                    "environment_embeddings"
                ],
            )
        )

        query_color = (
            CompactDescriptor.color(
                Path(image_path)
            )
        )

        color_score = (
            self.descriptor_similarity(
                query_color,
                data[
                    "color_embeddings"
                ],
            )
        )

        query_spatial = (
            CompactDescriptor.spatial(
                Path(image_path)
            )
        )

===== recognizer.py =====
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

                        "spatial": float(
                            score.get(
                                "spatial_score",
                                0.0,
                            )
                        ),

                        "best_image": score.get(
                            "best_image"
                        ),

                        "best_image_score": float(
                            score.get(
                                "best_image_score",
                                0.0,
                            )
                        ),
                    }
                )

            ranked.sort(
                key=lambda item: item[
                    "score"
                ],
                reverse=True,
            )

            ranked = ranked[
                :max(
                    1,
                    int(top_k),
                )
            ]

            if not ranked:
                results.append(
                    {
                        "file": str(path),
                        "best_id": None,
                        "score": 0.0,
                        "second_score": 0.0,
                        "margin": 0.0,
                        "confidence": "NO_MATCH",
                        "status": "NO_MATCH",
                        "candidates": [],
                    }
                )

                continue

            best = ranked[0]

            best_score = float(
                best["score"]
            )

            if len(ranked) >= 2:
                second_score = float(
                    ranked[1]["score"]
                )
            else:
                second_score = 0.0

            margin = (
                best_score
                - second_score
            )

            confidence = (
                self._confidence(
                    best_score,
                    margin,
                )
            )

            status = (
                self._status_from_confidence(
                    confidence
                )
            )

            # Threshold is still an absolute safety gate.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]

            results.append(
                {
                    "file": str(path),

                    "best_id": best_id,

                    "score": best_score,

                    "second_score": (
                        second_score
                    ),

                    "margin": float(
                        margin
                    ),

                    "confidence": confidence,

                    "status": status,

                    "best_image": best.get(
                        "best_image"
                    ),

                    "best_image_score": float(
                        best.get(
                            "best_image_score",
                            0.0,
                        )
                    ),

                    "candidates": ranked,
                }
            )

        return results

    def recognize(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        return self.recognize_folder(
            folder,
            top_k=top_k,
            threshold=threshold,
        )

===== fingerprint.py =====
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from .image import image_files
from .scene_analyzer import CompactDescriptor

class FingerprintManager:
    """
    Fingerprint storage for Scene Fingerprint v3.3 compact.

    Stored:

        embeddings.npy
        centroid.npy
        representatives.npy
        representative_indices.npy

        environment_embeddings.npy
        color_embeddings.npy
        spatial_embeddings.npy

        faiss.index
        metadata.json

    Patch storage:
        DISABLED
    """

    VERSION = "3.3"

    def __init__(
        self,
        settings,
        embedder,
    ):
        self.settings = settings
        self.embedder = embedder

        self.settings.fingerprints_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(
        self,
        fingerprint_id,
    ):
        return (
            self.settings.fingerprints_dir
            / str(fingerprint_id)
        )

    def list_fingerprints(self):
        result = []

        root = (
            self.settings.fingerprints_dir
        )

        if not root.exists():
            return result

        for directory in sorted(
            root.iterdir()
        ):
            if not directory.is_dir():
                continue

            metadata_file = (
                directory
                / "metadata.json"
            )

            if not metadata_file.exists():
                continue

            try:
                metadata = json.loads(
                    metadata_file.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                ValueError,
                json.JSONDecodeError,
            ):
                continue

            result.append(
                {
                    "id": directory.name,
                    **metadata,
                }
            )

        return result

    @staticmethod
    def _normalize_rows(array):
        array = np.asarray(
            array,
            dtype=np.float32,
        )

        if array.ndim == 1:
            array = array.reshape(
                1,
                -1,
            )

        norms = np.linalg.norm(
            array,
            axis=1,
            keepdims=True,
        )

        norms[
            norms == 0.0
        ] = 1.0

        return (
            array / norms
        ).astype(np.float32)

    @staticmethod
    def _normalize_vector(vector):
        vector = np.asarray(
            vector,
            dtype=np.float32,
        ).reshape(-1)

        norm = np.linalg.norm(
            vector
        )

        if norm > 0.0:
            vector = vector / norm

        return vector.astype(
            np.float32
        )

    def create(
        self,
        fingerprint_id,
        folder,
        embedder=None,
    ):
        fingerprint_id = str(
            fingerprint_id
        )

        folder = Path(folder)

        paths = image_files(folder)

        if not paths:
            raise ValueError(
                f"No images found in {folder}"
            )

        output = self._path(
            fingerprint_id
        )

        if output.exists():
            existing = list(
                output.iterdir()
            )

            if existing:
                raise FileExistsError(
                    f"Fingerprint '{fingerprint_id}' "
                    f"already exists and is not empty: "
                    f"{output}"
                )

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        embedder = (
            embedder
            or self.embedder
        )

        print(
            f"[Fingerprint v3.3] "
            f"Creating '{fingerprint_id}' "
            f"from {len(paths)} images"
        )

        print(
            "[Fingerprint v3.3] "
            "Building compact descriptors..."
        )

        embeddings = embedder.embed_paths(
            paths
        )

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(
                1,
                -1,
            )

        if embeddings.shape[1] != 768:
            raise ValueError(
                "Invalid DINO embedding "
                f"dimension: {embeddings.shape}"
            )

        embeddings = self._normalize_rows(
            embeddings
        )

        centroid = embeddings.mean(
            axis=0
        )

        centroid = self._normalize_vector(
            centroid
        )

        similarities = (
            embeddings @ centroid
        )

        representative_count = min(
            16,
            len(paths),
        )

        representative_indices = (
            np.argsort(
                similarities
            )[
                -representative_count:
            ][::-1]
        ).astype(np.int32)

        representatives = (
            embeddings[
                representative_indices
            ]
        )

        environment_embeddings = np.stack(
            [
                CompactDescriptor.environment(
                    Path(path)
                )
                for path in paths
            ]
        ).astype(np.float32)

        color_embeddings = np.stack(
            [
                CompactDescriptor.color(
                    Path(path)
                )
                for path in paths
            ]
        ).astype(np.float32)

        spatial_embeddings = np.stack(
            [
                CompactDescriptor.spatial(
                    Path(path)
                )
                for path in paths
            ]
        ).astype(np.float32)

        # FAISS global image index.
        index = faiss.IndexFlatIP(
            embeddings.shape[1]
        )

        index.add(
            embeddings.astype(
                np.float32
            )
        )

        np.save(
            output / "embeddings.npy",
            embeddings,
        )

        np.save(
            output / "centroid.npy",
            centroid.astype(
                np.float32
            ),
        )

        np.save(
            output / "representatives.npy",
            representatives.astype(
                np.float32
            ),
        )

        np.save(
            output / "representative_indices.npy",
            representative_indices,
        )

        np.save(
            output / "environment_embeddings.npy",
            environment_embeddings,
        )

        np.save(
            output / "color_embeddings.npy",
            color_embeddings,
        )

        np.save(
            output / "spatial_embeddings.npy",
            spatial_embeddings,
        )

        faiss.write_index(
            index,
            str(
                output / "faiss.index"
            ),
        )

        metadata = {
            "id": fingerprint_id,
            "version": self.VERSION,
            "model": "dinov2_vitb14",
            "images": len(paths),
            "dimension": int(
                embeddings.shape[1]
            ),
            "representatives": int(
                representative_count
            ),
            "patch_tokens": 0,
            "patch_storage": False,
            "environment_descriptor": "compact_v1",
            "environment_dimension": 640,
            "color_descriptor": "hsv_histogram_v1",
            "color_dimension": 48,
            "spatial_descriptor": "gray_grid_v1",
            "spatial_dimension": 32,
            "weights": {
                "global": 0.70,
                "environment": 0.20,
                "color": 0.07,
                "spatial": 0.03,
            },
            "image_names": [
                Path(path).name
                for path in paths
            ],
        }

        with (
            output / "metadata.json"
        ).open(
            "w",
            encoding="utf-8",
        ) as fh:
            json.dump(
                metadata,
                fh,
                ensure_ascii=False,
                indent=2,
            )

        print(
            f"[Fingerprint v3.3] Saved: "
            f"{output}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"global={embeddings.shape}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"environment="
            f"{environment_embeddings.shape}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"color={color_embeddings.shape}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"spatial={spatial_embeddings.shape}"
        )

        print(
            "[Fingerprint v3.3] "
            "PATCH STORAGE = DISABLED"
        )

        return metadata

    def load(
        self,
        fingerprint_id,
    ):
        fingerprint_id = str(
            fingerprint_id
        )

        output = self._path(
            fingerprint_id
        )

        if not output.exists():
            raise FileNotFoundError(
                f"Fingerprint "
                f"'{fingerprint_id}' "
                f"not found"
            )

        required = [
            "embeddings.npy",
            "centroid.npy",
            "representatives.npy",
            "representative_indices.npy",
            "environment_embeddings.npy",
            "color_embeddings.npy",
            "spatial_embeddings.npy",
            "faiss.index",
            "metadata.json",
        ]

        missing = [
            name
            for name in required
            if not (
                output / name
            ).exists()
        ]

        if missing:
            raise FileNotFoundError(
                f"Fingerprint "
                f"'{fingerprint_id}' "
                f"is incomplete. "
                f"Missing: "
                f"{', '.join(missing)}"
            )

        with (
            output / "metadata.json"
        ).open(
            "r",
            encoding="utf-8",
        ) as fh:
            metadata = json.load(fh)

        version = str(
            metadata.get(
                "version",
                "",
            )
        )

        if version != self.VERSION:
            raise ValueError(
                f"Fingerprint "
                f"'{fingerprint_id}' "
                f"is version "
                f"'{version}', "
                f"expected "
                f"'{self.VERSION}'"
            )

        return {
            "id": fingerprint_id,

            "metadata": metadata,

===== config.py =====
from dataclasses import dataclass
from pathlib import Path
import os
import torch

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("SCENE_HOST", "127.0.0.1")
    port: int = int(os.getenv("SCENE_PORT", "8080"))
    data_dir: Path = Path(os.getenv("SCENE_DATA", "data"))
    model_name: str = os.getenv("SCENE_MODEL", "facebook/dinov2-base")
    device: str = os.getenv("SCENE_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    batch_size: int = int(os.getenv("SCENE_BATCH", "16"))

    @property
    def fingerprints_dir(self):
        return self.data_dir / "fingerprints"

settings = Settings()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "===== FINGERPRINTS ====="
find data/fingerprints -maxdepth 2 -type f | sort
===== FINGERPRINTS =====
data/fingerprints/78/centroid.npy
data/fingerprints/78/embeddings.npy
data/fingerprints/78/faiss.index
data/fingerprints/78/metadata.json
data/fingerprints/78_patch/centroid.npy
data/fingerprints/78_patch/embeddings.npy
data/fingerprints/78_patch/faiss.index
data/fingerprints/78_patch/metadata.json
data/fingerprints/78_patch/patch_centroid.npy
data/fingerprints/78_patch/patch_embeddings.npy
data/fingerprints/78_patch/patch_representatives.npy
data/fingerprints/78_patch/representatives.npy
data/fingerprints/78/representatives.npy
data/fingerprints/78_v31/centroid.npy
data/fingerprints/78_v31/embeddings.npy
data/fingerprints/78_v31/faiss.index
data/fingerprints/78_v31/metadata.json
data/fingerprints/78_v31/patch_centroid.npy
data/fingerprints/78_v31/patch_embeddings.npy
data/fingerprints/78_v31/patch_representatives.npy
data/fingerprints/78_v31/representatives.npy
data/fingerprints/78_v32/centroid.npy
data/fingerprints/78_v32/color_embeddings.npy
data/fingerprints/78_v32/embeddings.npy
data/fingerprints/78_v32/environment_embeddings.npy
data/fingerprints/78_v32/faiss.index
data/fingerprints/78_v32/metadata.json
data/fingerprints/78_v32/representative_indices.npy
data/fingerprints/78_v32/representatives.npy
data/fingerprints/78_v32/spatial_embeddings.npy
data/fingerprints/78_v33/centroid.npy
data/fingerprints/78_v33/color_embeddings.npy
data/fingerprints/78_v33/embeddings.npy
data/fingerprints/78_v33/environment_embeddings.npy
data/fingerprints/78_v33/faiss.index
data/fingerprints/78_v33/metadata.json
data/fingerprints/78_v33/representative_indices.npy
data/fingerprints/78_v33/representatives.npy
data/fingerprints/78_v33/spatial_embeddings.npy
data/fingerprints/78_v3/centroid.npy
data/fingerprints/78_v3/embeddings.npy
data/fingerprints/78_v3/environment_centroid.npy
data/fingerprints/78_v3/environment_embeddings.npy
data/fingerprints/78_v3/environment_representatives.npy
data/fingerprints/78_v3/faiss.index
data/fingerprints/78_v3/metadata.json
data/fingerprints/78_v3/patch_centroid.npy
data/fingerprints/78_v3/patch_embeddings.npy
data/fingerprints/78_v3/patch_representatives.npy
data/fingerprints/78_v3/representative_indices.npy
data/fingerprints/78_v3/representatives.npy
data/fingerprints/79/centroid.npy
data/fingerprints/79/embeddings.npy
data/fingerprints/79/faiss.index
data/fingerprints/79/metadata.json
data/fingerprints/79/patch_centroid.npy
data/fingerprints/79/patch_embeddings.npy
data/fingerprints/79/patch_representatives.npy
data/fingerprints/79/representatives.npy
data/fingerprints/79_v31/centroid.npy
data/fingerprints/79_v31/embeddings.npy
data/fingerprints/79_v31/faiss.index
data/fingerprints/79_v31/metadata.json
data/fingerprints/79_v31/patch_centroid.npy
data/fingerprints/79_v31/patch_embeddings.npy
data/fingerprints/79_v31/patch_representatives.npy
data/fingerprints/79_v31/representatives.npy
data/fingerprints/79_v32/centroid.npy
data/fingerprints/79_v32/color_embeddings.npy
data/fingerprints/79_v32/embeddings.npy
data/fingerprints/79_v32/environment_embeddings.npy
data/fingerprints/79_v32/faiss.index
data/fingerprints/79_v32/metadata.json
data/fingerprints/79_v32/representative_indices.npy
data/fingerprints/79_v32/representatives.npy
data/fingerprints/79_v32/spatial_embeddings.npy
data/fingerprints/79_v33/centroid.npy
data/fingerprints/79_v33/color_embeddings.npy
data/fingerprints/79_v33/embeddings.npy
data/fingerprints/79_v33/environment_embeddings.npy
data/fingerprints/79_v33/faiss.index
data/fingerprints/79_v33/metadata.json
data/fingerprints/79_v33/representative_indices.npy
data/fingerprints/79_v33/representatives.npy
data/fingerprints/79_v33/spatial_embeddings.npy
data/fingerprints/80/centroid.npy
data/fingerprints/80/embeddings.npy
data/fingerprints/80/faiss.index
data/fingerprints/80/metadata.json
data/fingerprints/80/patch_centroid.npy
data/fingerprints/80/patch_embeddings.npy
data/fingerprints/80/patch_representatives.npy
data/fingerprints/80/representatives.npy
data/fingerprints/80_v31/centroid.npy
data/fingerprints/80_v31/embeddings.npy
data/fingerprints/80_v31/faiss.index
data/fingerprints/80_v31/metadata.json
data/fingerprints/80_v31/patch_centroid.npy
data/fingerprints/80_v31/patch_embeddings.npy
data/fingerprints/80_v31/patch_representatives.npy
data/fingerprints/80_v31/representatives.npy
data/fingerprints/80_v32/centroid.npy
data/fingerprints/80_v32/color_embeddings.npy
data/fingerprints/80_v32/embeddings.npy
data/fingerprints/80_v32/environment_embeddings.npy
data/fingerprints/80_v32/faiss.index
data/fingerprints/80_v32/metadata.json
data/fingerprints/80_v32/representative_indices.npy
data/fingerprints/80_v32/representatives.npy
data/fingerprints/80_v32/spatial_embeddings.npy
data/fingerprints/80_v33/centroid.npy
data/fingerprints/80_v33/color_embeddings.npy
data/fingerprints/80_v33/embeddings.npy
data/fingerprints/80_v33/environment_embeddings.npy
data/fingerprints/80_v33/faiss.index
data/fingerprints/80_v33/metadata.json
data/fingerprints/80_v33/representative_indices.npy
data/fingerprints/80_v33/representatives.npy
data/fingerprints/80_v33/spatial_embeddings.npy
data/fingerprints/81/centroid.npy
data/fingerprints/81/embeddings.npy
data/fingerprints/81/faiss.index
data/fingerprints/81/metadata.json
data/fingerprints/81/patch_centroid.npy
data/fingerprints/81/patch_embeddings.npy
data/fingerprints/81/patch_representatives.npy
data/fingerprints/81/representatives.npy
data/fingerprints/81_v31/centroid.npy
data/fingerprints/81_v31/embeddings.npy
data/fingerprints/81_v31/faiss.index
data/fingerprints/81_v31/metadata.json
data/fingerprints/81_v31/patch_centroid.npy
data/fingerprints/81_v31/patch_embeddings.npy
data/fingerprints/81_v31/patch_representatives.npy
data/fingerprints/81_v31/representatives.npy
data/fingerprints/81_v32/centroid.npy
data/fingerprints/81_v32/color_embeddings.npy
data/fingerprints/81_v32/embeddings.npy
data/fingerprints/81_v32/environment_embeddings.npy
data/fingerprints/81_v32/faiss.index
data/fingerprints/81_v32/metadata.json
data/fingerprints/81_v32/representative_indices.npy
data/fingerprints/81_v32/representatives.npy
data/fingerprints/81_v32/spatial_embeddings.npy
data/fingerprints/81_v33/centroid.npy
data/fingerprints/81_v33/color_embeddings.npy
data/fingerprints/81_v33/embeddings.npy
data/fingerprints/81_v33/environment_embeddings.npy
data/fingerprints/81_v33/faiss.index
data/fingerprints/81_v33/metadata.json
data/fingerprints/81_v33/representative_indices.npy
data/fingerprints/81_v33/representatives.npy
data/fingerprints/81_v33/spatial_embeddings.npy
data/fingerprints/82/centroid.npy
data/fingerprints/82/embeddings.npy
data/fingerprints/82/faiss.index
data/fingerprints/82/metadata.json
data/fingerprints/82/patch_centroid.npy
data/fingerprints/82/patch_embeddings.npy
data/fingerprints/82/patch_representatives.npy
data/fingerprints/82/representatives.npy
data/fingerprints/82_v31/centroid.npy
data/fingerprints/82_v31/embeddings.npy
data/fingerprints/82_v31/faiss.index
data/fingerprints/82_v31/metadata.json
data/fingerprints/82_v31/patch_centroid.npy
data/fingerprints/82_v31/patch_embeddings.npy
data/fingerprints/82_v31/patch_representatives.npy
data/fingerprints/82_v31/representatives.npy
data/fingerprints/82_v32/centroid.npy
data/fingerprints/82_v32/color_embeddings.npy
data/fingerprints/82_v32/embeddings.npy
data/fingerprints/82_v32/environment_embeddings.npy
data/fingerprints/82_v32/faiss.index
data/fingerprints/82_v32/metadata.json
data/fingerprints/82_v32/representative_indices.npy
data/fingerprints/82_v32/representatives.npy
data/fingerprints/82_v32/spatial_embeddings.npy
data/fingerprints/82_v33/centroid.npy
data/fingerprints/82_v33/color_embeddings.npy
data/fingerprints/82_v33/embeddings.npy
data/fingerprints/82_v33/environment_embeddings.npy
data/fingerprints/82_v33/faiss.index
data/fingerprints/82_v33/metadata.json
data/fingerprints/82_v33/representative_indices.npy
data/fingerprints/82_v33/representatives.npy
data/fingerprints/82_v33/spatial_embeddings.npy
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-12 22:26:05

Да. Теперь картина понятна. **Переходим дальше именно на v3.3 compact**, старые версии не трогаем.

По твоему последнему выводу есть несколько важных моментов.

### 1. Текущая v3.3 уже реально работает

У тебя успешно загружены:

- `78_v33`
- `79_v33`
- `80_v33`
- `81_v33`
- `82_v33`

И результаты выглядят осмысленно:

- `001–005` → уверенно `78_v33`
- `006–007` → уверенно `80_v33`
- `008–009` → **AMBIGUOUS**, потому что разница между кандидатами практически нулевая.

Например:

```text
008.JPG
79_v33  0.8843
78_v33  0.8835
margin  0.0008
```

Это как раз полезный результат: система **не притворяется, что знает ответ**, когда две конструкции практически одинаковы.

---

### 2. 83/84/85 пока НЕ участвуют

В твоём последнем:

```bash
find data/fingerprints -maxdepth 2 -type f | sort
```

их вообще нет.

То есть сейчас recognizer физически не может сравнивать:

```text
78
79
80
81
82
83
84
85
```

Он видит только:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
```

Поэтому следующий шаг — **создать 83_v33, 84_v33 и 85_v33 тем же самым v3.3 compact алгоритмом**.

---

## 3. Твой `scene_analyzer.py` в основе правильный

По показанной части я **не стал бы сейчас менять CompactDescriptor**.

У тебя:

```text
environment = 640
color       = 48
spatial     = 32
global      = 768
```

и веса:

```text
global       0.70
environment  0.20
color        0.07
spatial      0.03
```

Это соответствует текущей архитектуре v3.3 compact.

Но есть **один технический недостаток в `recognizer.py`**.

Ты уже один раз вычисляешь:

```python
queries = self.embedder.embed_paths(paths)
```

но потом это вычисление фактически не используется.

Дальше для **каждого fingerprint** вызывается:

```python
self.analyzer.compare(
    Path(path),
    fingerprint_id,
)
```

а внутри `compare()` снова:

```python
query_global = self.embedder.embed_paths(
    [Path(image_path)]
)[0]
```

То есть для 9 фотографий и 8 fingerprints DINO может прогоняться намного больше раз, чем необходимо.

Это **не ошибка результатов**, но это лишняя нагрузка на RTX 3060.

---

# Сейчас ничего не переделываем

Я предлагаю сначала получить полноценный эксперимент:

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

После этого посмотрим, **как меняется разделение 78/79/80/81/82**, особенно проблемных:

```text
008.JPG
009.JPG
```

И вот это уже будет хороший тест v3.3.

---

## Шаг 1 — проверь папки 83/84/85

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== INPUT DATA ====="
find data/input -maxdepth 2 -type f | sort | grep -E '/(83|84|85)/'
```

Если у тебя они действительно лежат:

```text
data/input/83/
data/input/84/
data/input/85/
```

то сразу создаём v3.3.

### 83

```bash
uv run scene-fingerprint create 83_v33 data/input/83
```

### 84

```bash
uv run scene-fingerprint create 84_v33 data/input/84
```

### 85

```bash
uv run scene-fingerprint create 85_v33 data/input/85
```

**Не создавай `83`, `84`, `85` поверх старых. Именно `_v33`.**

---

## Шаг 2 — убедимся, что все восемь fingerprint'ов готовы

После создания:

```bash
echo "===== V3.3 FINGERPRINTS ====="

for id in 78_v33 79_v33 80_v33 81_v33 82_v33 83_v33 84_v33 85_v33; do
    echo
    echo "### $id"
    ls -1 data/fingerprints/$id
done
```

У каждого должны быть:

```text
centroid.npy
embeddings.npy
environment_embeddings.npy
color_embeddings.npy
spatial_embeddings.npy
representatives.npy
representative_indices.npy
faiss.index
metadata.json
```

---

# Шаг 3 — затем один общий тест

```bash
uv run scene-fingerprint recognize \
    data/input/new \
    --top-k 8 \
    --threshold 0.65
```

Здесь я специально предлагаю:

```text
--top-k 8
```

потому что теперь у нас **8 равноправных конструкций**.

И это особенно важно для твоей задачи: 83/84/85 не должны быть «дополнительными» или иметь меньший вес. Они такие же самостоятельные reference scenes, как 78–82.

---

## Что нас особенно интересует

После этого сравним:

```text
001
002
003
004
005
006
007
008
009
```

и посмотрим не только `MATCH`, но и:

```text
GLOBAL
ENVIRONMENT
COLOR
SPATIAL
FINAL
MARGIN
BEST IMAGE
```

Особенно интересны случаи типа:

```text
79_v33  0.8843
78_v33  0.8835
81_v33  0.8814
```

Если после добавления 83–85 получится, например:

```text
79_v33  0.8843
83_v33  0.8839
78_v33  0.8835
```

это уже даст нам информацию о том, **что именно путает модель**.

---

### И ещё важный момент

**Пока не удаляй старые fingerprints.**

Оставляем всё:

```text
78
78_patch
78_v3
78_v31
78_v32
78_v33

...

82_v33
83_v33
84_v33
85_v33
```

Старые версии нам сейчас пригодятся как контрольные точки. После того как убедимся, что v3.3 действительно лучше разделяет конструкции, можно будет спокойно почистить архив.

**Сейчас сделай создание `83_v33`, `84_v33`, `85_v33`.** Если какая-то команда выдаст ошибку — пришли её целиком, и будем чинить именно её, не переписывая рабочую часть v3.3.

---

### 👤 **User** — 2026-08-12 22:27:46

===== INPUT DATA =====
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint create 83_v33 data/input/83
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2...
Downloading: "https://github.com/facebookresearch/dinov2/zipball/main" to /home/alexice/.cache/torch/hub/main.zip
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/scene-fingerprint", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/cli.py", line 286, in main
    embedder = SceneEmbedder(
               ^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/embedder.py", line 37, in __init__
    self.model = torch.hub.load(
                 ^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/torch/hub.py", line 661, in load
    repo_or_dir = _get_cache_or_reload(
                  ^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/torch/hub.py", line 314, in _get_cache_or_reload
    download_url_to_file(url, cached_file, progress=False)
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/torch/hub.py", line 749, in download_url_to_file
    with urlopen(req) as u:
         ^^^^^^^^^^^^
  File "/usr/lib/python3.12/urllib/request.py", line 215, in urlopen
    return opener.open(url, data, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/urllib/request.py", line 515, in open
    response = self._open(req, data)
               ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/urllib/request.py", line 532, in _open
    result = self._call_chain(self.handle_open, protocol, protocol +
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/urllib/request.py", line 492, in _call_chain
    result = func(*args)
             ^^^^^^^^^^^
  File "/usr/lib/python3.12/urllib/request.py", line 1392, in https_open
    return self.do_open(http.client.HTTPSConnection, req,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/urllib/request.py", line 1348, in do_open
    r = h.getresponse()
        ^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/http/client.py", line 1457, in getresponse
    response.begin()
  File "/usr/lib/python3.12/http/client.py", line 336, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/http/client.py", line 305, in _read_status
    raise RemoteDisconnected("Remote end closed connection without"
http.client.RemoteDisconnected: Remote end closed connection without response
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-12 22:27:53

Да, здесь проблема **не в `83_v33` и не в fingerprint.py**. Сломалась загрузка DINOv2.

Смотри на разницу:

При предыдущем `recognize` было:

```text
Using cache found in
/home/alexice/.cache/torch/hub/facebookresearch_dinov2_main
```

А сейчас:

```text
Downloading:
"https://github.com/facebookresearch/dinov2/zipball/main"
```

То есть `torch.hub` **перестал видеть/использовать уже имеющийся локальный cache** и пытается скачать репозиторий GitHub. GitHub соединение оборвалось:

```text
RemoteDisconnected:
Remote end closed connection without response
```

### Главное: ничего из v3.3 не сломалось

`83_v33` даже не начал создаваться. Поэтому его каталог либо отсутствует, либо пустой.

---

# Делаем сначала проверку cache

**Не меняй пока никакие `.py` файлы.**

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TORCH HUB CACHE ====="
ls -lah ~/.cache/torch/hub/

echo
echo "===== DINO CACHE ====="
ls -lah ~/.cache/torch/hub/facebookresearch_dinov2_main | head -30

echo
echo "===== DINOV2 FILE ====="
ls -lah ~/.cache/torch/hub/facebookresearch_dinov2_main/hubconf.py
```

И ещё:

```bash
echo "===== 83 FINGERPRINT ====="
ls -lah data/fingerprints/83_v33 2>/dev/null || echo "83_v33 does not exist"
```

---

## Если `facebookresearch_dinov2_main` существует

Судя по твоему предыдущему успешному запуску, **он должен существовать**.

Тогда сначала попробуем заставить PyTorch использовать именно его, вообще без интернета.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

export TORCH_HOME="$HOME/.cache/torch"

uv run scene-fingerprint create 83_v33 data/input/83
```

Если опять увидишь:

```text
Downloading: "https://github.com/facebookresearch/dinov2/zipball/main"
```

**остановись и пришли вывод.**

---

# Почему это произошло

Твой текущий `embedder.py` содержит:

```python
self.model = torch.hub.load(
    "facebookresearch/dinov2",
    "dinov2_vitb14",
)
```

Это означает:

1. `torch.hub` ищет репозиторий в cache;
2. если cache корректно найден — использует его;
3. если не найден — пытается скачать `facebookresearch/dinov2`;
4. сейчас он решил, что локального репозитория нет/он недоступен;
5. GitHub не отдал ZIP → запуск остановился.

При этом **сам DINOv2 у тебя уже был загружен ранее**, потому что предыдущий запуск показывал:

```text
Using cache found in
/home/alexice/.cache/torch/hub/facebookresearch_dinov2_main
```

Поэтому я пока **не хочу переустанавливать DINO, Python, torch или v3.3**. Это было бы лишним.

---

### И ещё важное

После восстановления cache мы продолжим ровно отсюда:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
→ 83_v33
→ 84_v33
→ 85_v33
```

И затем сделаем общий тест **всех 8 конструкций**, потому что именно это нам нужно для более точного разделения похожих адресов.

Сначала пришли вывод четырёх проверок cache выше.

---

### 👤 **User** — 2026-08-12 22:28:32

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TORCH HUB CACHE ====="
ls -lah ~/.cache/torch/hub/

echo
echo "===== DINO CACHE ====="
ls -lah ~/.cache/torch/hub/facebookresearch_dinov2_main | head -30

echo
echo "===== DINOV2 FILE ====="
ls -lah ~/.cache/torch/hub/facebookresearch_dinov2_main/hubconf.py
===== TORCH HUB CACHE =====
total 8.0K
drwxrwxr-x 2 alexice alexice 4.0K Aug 12 22:27 .
drwxrwxr-x 3 alexice alexice 4.0K Aug 12 22:27 ..
-rw-rw-r-- 1 alexice alexice    0 Aug 12 22:27 trusted_list

===== DINO CACHE =====
ls: cannot access '/home/alexice/.cache/torch/hub/facebookresearch_dinov2_main': No such file or directory

===== DINOV2 FILE =====
ls: cannot access '/home/alexice/.cache/torch/hub/facebookresearch_dinov2_main/hubconf.py': No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "===== 83 FINGERPRINT ====="
ls -lah data/fingerprints/83_v33 2>/dev/null || echo "83_v33 does not exist"
===== 83 FINGERPRINT =====
83_v33 does not exist
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-12 22:28:34

Отлично, теперь причина **точно установлена**.

Локального DINOv2 cache действительно нет:

```text
~/.cache/torch/hub/
└── trusted_list
```

а:

```text
~/.cache/torch/hub/facebookresearch_dinov2_main
```

отсутствует.

При этом **fingerprints 78_v33–82_v33 целы** — им уже сохранённые DINO embeddings не нужны для чтения. Поэтому предыдущий `recognize` и мог работать до исчезновения cache.

Нам сейчас нужно восстановить **тот же самый `dinov2_vitb14`**, не менять v3.3.

### Важный момент

Я бы не стал снова просто запускать:

```bash
uv run scene-fingerprint create ...
```

потому что он опять полезет на GitHub и может снова оборваться.

Сначала проверим, есть ли у тебя уже **весовая модель DINOv2** в старом cache или где-нибудь в проекте.

Выполни один блок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== DINO FILES IN HOME ====="
find ~/.cache ~/.local ~/projects ~/Desktop \
    -type f \
    \( -iname "*dinov2*" -o -iname "*.pth" \) \
    2>/dev/null | head -100

echo
echo "===== TORCH HUB ====="
find ~/.cache/torch -maxdepth 4 -type f 2>/dev/null | head -100

echo
echo "===== PROJECT ====="
find . -type f \
    \( -iname "*dinov2*" -o -iname "*.pth" \) \
    2>/dev/null | head -100
```

### Почему именно так

В твоей истории уже был загружен:

```text
dinov2_vitb14_pretrain.pth
```

и ранее использовался cache:

```text
/home/alexice/.cache/torch/hub/facebookresearch_dinov2_main
```

Если `.pth` **ещё сохранился**, мы сможем восстановить загрузку DINO без повторного скачивания огромного репозитория и без изменения архитектуры v3.3.

Если же ничего не найдётся — тогда установим DINOv2 заново, но **зафиксируем локальную копию**, чтобы больше не зависеть от GitHub при каждом создании fingerprint.

**Пока никаких файлов проекта не меняй.** Пришли вывод этого блока.

---

### 👤 **User** — 2026-08-12 22:29:15

83_v33 does not exist
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== DINO FILES IN HOME ====="
find ~/.cache ~/.local ~/projects ~/Desktop \
    -type f \
    $ -iname "*dinov2*" -o -iname "*.pth" $ \
    2>/dev/null | head -100

echo
echo "===== TORCH HUB ====="
find ~/.cache/torch -maxdepth 4 -type f 2>/dev/null | head -100

echo
echo "===== PROJECT ====="
find . -type f \
    $ -iname "*dinov2*" -o -iname "*.pth" $ \
    2>/dev/null | head -100
===== DINO FILES IN HOME =====
/home/alexice/.cache/uv/archive-v0/7rWm_57BzmWgbnEt/distutils-precedence.pth
/home/alexice/.cache/uv/archive-v0/G4BmGBbA3Ylk9hme/random_chat.pth
/home/alexice/.cache/uv/archive-v0/xg3A0ZpsAWlFazdt/_cuda_bindings_redirector.pth
/home/alexice/.cache/uv/archive-v0/mre0IBirRxyg-6HK/distutils-precedence.pth
/home/alexice/.cache/uv/archive-v0/r68_Urr4eEFCMx6n/random_chat.pth
/home/alexice/.cache/uv/archive-v0/LHWRUo6DS57mVh-Q/kornia/feature/dedode/transformer/dinov2.py
/home/alexice/.cache/uv/archive-v0/aRMB1iuvmMAgUaLn/transformers/models/dinov2/modeling_dinov2.py
/home/alexice/.cache/uv/archive-v0/aRMB1iuvmMAgUaLn/transformers/models/dinov2/configuration_dinov2.py
/home/alexice/.cache/uv/archive-v0/aRMB1iuvmMAgUaLn/transformers/models/dinov2_with_registers/modular_dinov2_with_registers.py
/home/alexice/.cache/uv/archive-v0/aRMB1iuvmMAgUaLn/transformers/models/dinov2_with_registers/modeling_dinov2_with_registers.py
/home/alexice/.cache/uv/archive-v0/aRMB1iuvmMAgUaLn/transformers/models/dinov2_with_registers/configuration_dinov2_with_registers.py
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2/modeling_dinov2.py
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2/configuration_dinov2.py
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2/__pycache__/configuration_dinov2.cpython-312.pyc
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2/__pycache__/modeling_dinov2.cpython-312.pyc
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/modular_dinov2_with_registers.py
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/modeling_dinov2_with_registers.py
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/configuration_dinov2_with_registers.py
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/__pycache__/modular_dinov2_with_registers.cpython-312.pyc
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/__pycache__/configuration_dinov2_with_registers.cpython-312.pyc
/home/alexice/.local/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/__pycache__/modeling_dinov2_with_registers.cpython-312.pyc
/home/alexice/.local/lib/python3.12/site-packages/distutils-precedence.pth
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/_virtualenv.pth
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/transformers/models/dinov2/modeling_dinov2.py
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/transformers/models/dinov2/configuration_dinov2.py
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/modular_dinov2_with_registers.py
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/modeling_dinov2_with_registers.py
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/transformers/models/dinov2_with_registers/configuration_dinov2_with_registers.py
/home/alexice/projects/scene_fingerprint_mvp/.venv/lib/python3.12/site-packages/distutils-precedence.pth
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/_virtualenv.pth
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/__editable__.scene_fingerprint-0.2.0.pth
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/distutils-precedence.pth
/home/alexice/projects/yes/envs/unr_gen_gradio/lib/python3.10/site-packages/distutils-precedence.pth
/home/alexice/projects/yes/envs/unr-gen/lib/python3.11/site-packages/distutils-precedence.pth
/home/alexice/projects/yes/envs/albion_ai/lib/python3.11/site-packages/distutils-precedence.pth
/home/alexice/projects/yes/lib/python3.13/site-packages/conda-site.pth
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2/modeling_dinov2.py
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2/configuration_dinov2.py
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2/__pycache__/configuration_dinov2.cpython-313.pyc
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2/__pycache__/modeling_dinov2.cpython-313.pyc
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2_with_registers/modular_dinov2_with_registers.py
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2_with_registers/modeling_dinov2_with_registers.py
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2_with_registers/configuration_dinov2_with_registers.py
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2_with_registers/__pycache__/configuration_dinov2_with_registers.cpython-313.pyc
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2_with_registers/__pycache__/modeling_dinov2_with_registers.cpython-313.pyc
/home/alexice/projects/yes/lib/python3.13/site-packages/transformers/models/dinov2_with_registers/__pycache__/modular_dinov2_with_registers.cpython-313.pyc
/home/alexice/projects/yes/lib/python3.13/site-packages/distutils-precedence.pth
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2.py
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_configs/dinov2_with_registers_base.json
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_configs/dinov2_large.json
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_configs/dinov2_base.json
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_configs/dinov2_with_registers_small.json
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_configs/dinov2_with_registers_large.json
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_configs/dinov2_small.json
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/dinov2_with_windowed_attn.py
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/__pycache__/dinov2_with_windowed_attn.cpython-313.pyc
/home/alexice/projects/yes/lib/python3.13/site-packages/surya/common/rfdetr/models/backbone/__pycache__/dinov2.cpython-313.pyc
/home/alexice/projects/yes/pkgs/python-3.13.13-h6add32d_100_cp313/lib/python3.13/site-packages/conda-site.pth
/home/alexice/projects/yes/pkgs/setuptools-82.0.1-pyh332efcf_0/site-packages/distutils-precedence.pth
/home/alexice/projects/yes/pkgs/setuptools-83.0.0-pyh332efcf_0/site-packages/distutils-precedence.pth
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2/modeling_dinov2.py
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2/configuration_dinov2.py
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2/__pycache__/modeling_dinov2.cpython-311.pyc
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2/__pycache__/configuration_dinov2.cpython-311.pyc
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2_with_registers/modular_dinov2_with_registers.py
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2_with_registers/modeling_dinov2_with_registers.py
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2_with_registers/configuration_dinov2_with_registers.py
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2_with_registers/__pycache__/configuration_dinov2_with_registers.cpython-311.pyc
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2_with_registers/__pycache__/modeling_dinov2_with_registers.cpython-311.pyc
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/transformers/models/dinov2_with_registers/__pycache__/modular_dinov2_with_registers.cpython-311.pyc
/home/alexice/projects/AlbionAI/env/lib/python3.11/site-packages/distutils-precedence.pth
/home/alexice/projects/random_chat/.venv/lib/python3.13/site-packages/_virtualenv.pth
/home/alexice/projects/random_chat/.venv/lib/python3.13/site-packages/random_chat.pth

===== TORCH HUB =====
/home/alexice/.cache/torch/hub/trusted_list

===== PROJECT =====
./.venv/lib/python3.12/site-packages/_virtualenv.pth
./.venv/lib/python3.12/site-packages/__editable__.scene_fingerprint-0.2.0.pth
./.venv/lib/python3.12/site-packages/distutils-precedence.pth
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-12 22:29:16

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed SceneEmbedder, DINOv2 loading, model location, and fingerprint workflow**
>
> 
>
> Worked for 6s

Да. Сейчас **83_v33 не создан**, и проблема не в `scene_analyzer.py`, `recognizer.py` или `fingerprint.py`.

Проблема конкретно здесь:

```text
SceneEmbedder
    ↓
torch.hub.load(...)
    ↓
https://github.com/facebookresearch/dinov2/zipball/main
    ↓
RemoteDisconnected
```

Причём мы уже видим важный факт: **старого torch hub cache сейчас нет**:

```text
~/.cache/torch/hub/facebookresearch_dinov2_main
```

отсутствует.

И найденный тобой `transformers/models/dinov2/...` — это **код Transformers, а не веса модели**. Самого `dinov2_vitb14_pretrain.pth` среди найденных файлов сейчас нет.

### Главное

**83/84/85 оставляем равноправными:**

```text
78
79
80
81
82
83
84
85
```

И для эксперимента они должны участвовать **одинаково**, без какого-либо специального приоритета 83–85.

Также я бы пока **не трогал твой v3.3 `SceneAnalyzer`**. По показанному коду архитектура правильная для текущего эксперимента:

```text
DINO global       70%
environment       20%
color              7%
spatial            3%
patch              0%
```

Но у тебя есть ещё один важный технический момент: `recognizer.py` сейчас делает DINO embedding всех query-картинок заранее:

```python
queries = self.embedder.embed_paths(paths)
```

а затем `SceneAnalyzer.compare()` **ещё раз** вызывает:

```python
self.embedder.embed_paths([Path(image_path)])
```

То есть сейчас query изображения прогоняются через DINO **дважды**. Это потом оптимизируем. Сейчас не надо смешивать две проблемы.

---

## Сейчас восстановим именно рабочий DINO

Сначала покажи мне **текущий `embedder.py`**. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== EMBEDDER.PY ====="
sed -n '1,420p' app/core/embedder.py

echo
echo "===== PYPROJECT ====="
sed -n '1,300p' pyproject.toml

echo
echo "===== OLD PROJECT EMBEDDER ====="
if [ -f ~/projects/scene_fingerprint_mvp/app/core/embedder.py ]; then
    sed -n '1,420p' ~/projects/scene_fingerprint_mvp/app/core/embedder.py
else
    echo "OLD EMBEDDER NOT FOUND"
fi
```

И отдельно найдём **реальные веса**, включая файлы, которые могли иметь другое имя:

```bash
echo "===== POSSIBLE DINO WEIGHTS ====="

find /home/alexice \
    -type f \
    \( \
        -iname "*.pth" \
        -o -iname "*.pt" \
        -o -iname "*.bin" \
        -o -iname "*.safetensors" \
    \) \
    2>/dev/null \
    | grep -Ei 'dino|vitb|dinov2|facebook' \
    | head -200
```

И проверим Hugging Face cache:

```bash
echo "===== HUGGINGFACE CACHE ====="

find ~/.cache/huggingface \
    -maxdepth 5 \
    -type f \
    2>/dev/null \
    | grep -Ei 'dinov2|vit-base|facebook' \
    | head -200
```

### Пока ничего не переустанавливай

Не надо сейчас:

- удалять `.venv`;
- пересоздавать fingerprint 78–82;
- менять `scene_analyzer.py`;
- менять веса v3.3;
- скачивать DINO вручную ещё раз;
- создавать `83_v33` заново.

Сначала посмотрим **какой именно `SceneEmbedder` у тебя сейчас стоит и где в предыдущей рабочей версии были веса**.

После этих четырёх выводов я дам **конкретную замену `embedder.py`**, чтобы `83_v33`, затем `84_v33` и `85_v33` создавались тем же DINO, что использовался для 78–82.

---

### 👤 **User** — 2026-08-12 22:30:06

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02/data/input$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== EMBEDDER.PY ====="
sed -n '1,420p' app/core/embedder.py

echo
echo "===== PYPROJECT ====="
sed -n '1,300p' pyproject.toml

echo
echo "===== OLD PROJECT EMBEDDER ====="
if [ -f ~/projects/scene_fingerprint_mvp/app/core/embedder.py ]; then
    sed -n '1,420p' ~/projects/scene_fingerprint_mvp/app/core/embedder.py
else
    echo "OLD EMBEDDER NOT FOUND"
fi
===== EMBEDDER.PY =====
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

class SceneEmbedder:
    """DINOv2 ViT-B/14 global embedding service.

    v3.2 Compact deliberately does NOT extract or store
    DINO patch tokens.

    Output:
        global embedding: [N, 768]
    """

    def __init__(self, settings):
        self.settings = settings
        self.device = torch.device(settings.device)

        print(f"[SceneEmbedder] device={self.device}")

        if self.device.type == "cuda":
            print(
                f"[SceneEmbedder] GPU="
                f"{torch.cuda.get_device_name(0)}"
            )
            print(
                f"[SceneEmbedder] VRAM="
                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )

        print("[SceneEmbedder] Loading DINOv2...")

        self.model = torch.hub.load(
            "facebookresearch/dinov2",
            "dinov2_vitb14",
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        self.dimension = 768

        self.transform = transforms.Compose([
            transforms.Resize(
                256,
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        print(
            f"[SceneEmbedder] embedding dimension="
            f"{self.dimension}"
        )
        print(
            "[SceneEmbedder] patch extraction=DISABLED "
            "(v3.2 compact)"
        )
        print("[SceneEmbedder] Ready.")

    def _prepare_batch(self, images):
        return torch.stack([
            self.transform(image)
            for image in images
        ]).to(
            self.device,
            non_blocking=True,
        )

    @torch.inference_mode()
    def embed_images(
        self,
        images: list[Image.Image],
        batch_size=None,
    ):
        batch_size = (
            batch_size
            or self.settings.batch_size
        )

        vectors = []

        for i in range(
            0,
            len(images),
            batch_size,
        ):
            batch_images = images[
                i:i + batch_size
            ]

            batch = self._prepare_batch(
                batch_images
            )

            features = self.model(batch)

            features = torch.nn.functional.normalize(
                features,
                dim=1,
            )

            vectors.append(
                features.float()
                .cpu()
                .numpy()
            )

        if not vectors:
            return np.empty(
                (0, self.dimension),
                dtype=np.float32,
            )

        return np.concatenate(
            vectors,
            axis=0,
        ).astype("float32")

    def embed_paths(self, paths):
        from .image import load_image

        images = [
            load_image(path)
            for path in paths
        ]

        return self.embed_images(images)

===== PYPROJECT =====
[project]
name = "scene-fingerprint"
version = "0.2.0"
description = "Scene-based visual fingerprinting and recognition MVP"
requires-python = ">=3.12,<3.13"
dependencies = [
    "nicegui>=2.24,<3",
    "torch>=2.13,<2.14",
    "torchvision>=0.28,<0.29",
    "pillow>=12",
    "numpy>=2.5,<3",
    "faiss-cpu>=1.15,<2",
    "opencv-python-headless>=5,<6",
    "tqdm>=4.70,<5",
]

[tool.uv]
package = true

[project.scripts]
scene-fingerprint = "app.cli:main"

===== OLD PROJECT EMBEDDER =====
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class SceneEmbedder:
    """
    UI-independent visual embedding service.

    The current MVP uses DINOv2 as a general visual feature extractor.
    It does NOT train a LoRA and does NOT attempt OCR.
    """
    def __init__(self, settings):
        self.settings = settings
        self.device = torch.device(settings.device)
        self.processor = AutoImageProcessor.from_pretrained(settings.model_name)
        self.model = AutoModel.from_pretrained(settings.model_name)
        self.model.to(self.device).eval()

    @torch.inference_mode()
    def embed_images(self, images: list[Image.Image], batch_size: int = 16):
        vectors = []
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            inputs = self.processor(images=batch, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            outputs = self.model(**inputs)

            # DINOv2: CLS token as compact scene representation.
            vec = outputs.last_hidden_state[:, 0, :]
            vec = torch.nn.functional.normalize(vec, dim=-1)
            vectors.append(vec.cpu().numpy())

        return np.concatenate(vectors, axis=0).astype("float32")

    def embed_paths(self, paths):
        from app.core.image import load_image
        return self.embed_images([load_image(p) for p in paths])
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---


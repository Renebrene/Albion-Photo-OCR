## СЕССИЯ: Использование первого кандидата

**Создано:** 2026-08-14 23:31:05
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb)

---

### 👤 **User** — 2026-08-14 23:31:04

нет. даже если кандидат слишком слабый - давай все равно его использовать

---

### 🤖 **Assistant** — 2026-08-14 23:31:05

Да. Тогда меняем логику: **первый кандидат используем всегда**, независимо от его confidence/threshold.

То есть сейчас нам не нужно делать:

```python
if score < threshold:
    return None
```

или:

```python
if best_score < threshold:
    reject()
```

Вместо этого:

```python
best_candidate = candidates[0]

# Используем первого кандидата всегда,
# даже если similarity очень низкая.
return best_candidate
```

При этом **оценку score сохраняем** - она нам пригодится для диагностики:

```text
Фото → кандидат №1 → адрес 78 → score 0.31 → ПРИНЯТ
Фото → кандидат №1 → адрес 82 → score 0.47 → ПРИНЯТ
Фото → кандидат №1 → адрес 79 → score 0.68 → ПРИНЯТ
```

То есть `threshold` больше **не должен блокировать назначение адреса**. Он может остаться только как информационный параметр.

И это хорошо соответствует твоей идее: если система не уверена, **она всё равно должна привязать фотографию к наиболее похожему уже известному адресу**, а не оставлять её без адреса.

Причём я бы сделал ещё одно важное изменение: **после первого распознавания использовать результат первого кандидата для создания/обновления слепка нового адреса**, чтобы следующие фотографии этого же адреса постепенно подтягивались к нему. Это позволит построить именно тот механизм, который ты описывал ранее.

---

### 👤 **User** — 2026-08-14 23:31:44

делаем

---

### 🤖 **Assistant** — 2026-08-14 23:31:45

Да. Делаем именно так.

Логика нового распознавания будет:

1. Для каждой новой фотографии ищем кандидатов.
2. **Берём кандидата №1 всегда**, даже при очень низком score.
3. Копируем фото в каталог этого адреса.
4. Score сохраняем в метаданных.
5. Если это новый/слабый адрес — используем первый найденный кандидат как начальную привязку.
6. После этого можем пересчитать/обновить слепок адреса на основе новых фотографий.
7. **Никаких `threshold → reject`**.

Но прежде чем править код вслепую, лучше продолжить с текущей версией проекта `scene_fingerprint_mvp_v02` и посмотреть актуальный `recognizer.py`/CLI. Тогда я дам точечную замену, не сломав v33.

Пришли вывод:

```bash
cd ~/scene_fingerprint_mvp_v02

sed -n '1,260p' app/core/recognizer.py
```

и:

```bash
sed -n '1,320p' app/cli.py
```

Если `cli.py` у тебя называется иначе — покажи:

```bash
find app -maxdepth 2 -type f | sort
```

После этого переделаем распознавание так, чтобы **первый кандидат принимался всегда**.

---

### 👤 **User** — 2026-08-14 23:35:55

======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/scene_fingerprint_mvp_v02

sed -n '1,260p' app/core/recognizer.py
bash: cd: /home/alexice/scene_fingerprint_mvp_v02: No such file or directory
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,320p' app/cli.py
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
                f"{candidate['id']:<14} "
                f"{candidate['score']:.4f}"
            )

def main():
    parser = build_parser()
    args = parser.parse_args()

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    if args.command == "create":

        folder = Path(
            args.folder
        )

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: "
                f"{folder}"
            )

        embedder = SceneEmbedder(
            settings
        )

        manager = FingerprintManager(
            settings,
            embedder,
        )

        metadata = manager.create(
            args.fingerprint,
            folder,
            embedder,
        )

        print()

        print(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    if args.command == "analyze":

        folder = Path(
            args.folder
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:35:56

Да, вижу текущую реализацию. И здесь важный момент: **не нужно просто убрать `threshold`**. Сейчас решение о `NO_MATCH` формируется через `confidence/status`, поэтому надо изменить именно финальную логику `recognizer.py`.

У тебя вывод оборвался примерно на середине файла. Сначала покажи оставшуюся часть `recognizer.py` — от места после:

```python
"color": float(
    score.get(
        "color_score",
        0.0,
    )
),
```

до конца файла:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '120,420p' app/core/recognizer.py
```

**Пока ничего не меняй.**

После этого я дам конкретную замену, которая будет делать:

```text
TOP CANDIDATE
      ↓
всегда принимаем
      ↓
даже score = 0.20 / 0.35 / 0.48
      ↓
адрес кандидата №1
      ↓
сохраняем score + confidence
```

При этом `HIGH / PROBABLE / AMBIGUOUS / NO_MATCH` можно оставить как **оценку качества**, но `NO_MATCH` больше не будет означать «не назначать адрес».

И отдельно затем сделаем второй этап — **обновление слепка по принятым фотографиям**, чтобы механизм действительно мог самообучаться на новых снимках, а не просто всегда выбирать первого кандидата.

---

### 👤 **User** — 2026-08-14 23:38:52

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/scene_fingerprint_mvp_v02

sed -n '1,260p' app/core/recognizer.py
bash: cd: /home/alexice/scene_fingerprint_mvp_v02: No such file or directory
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:38:53

Да, теперь понятно. Команда `cd` у тебя была неправильная — проект находится здесь:

```bash
~/projects/scene_fingerprint_mvp_v02
```

А `recognizer.py` действительно обрезан на середине. Нам **не надо гадать, что находится ниже**, потому что именно там формируется `best_id`, `confidence`, `status` и `NO_MATCH`.

Выполни сейчас ровно это:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '180,420p' app/core/recognizer.py
```

Если вывода будет недостаточно, сразу:

```bash
wc -l app/core/recognizer.py
```

и:

```bash
sed -n '180,520p' app/core/recognizer.py
```

После этого я дам тебе **готовую замену конкретного участка**, без переписывания всего проекта.

Целевая логика будет такой:

```text
кандидаты
   ↓
сортировка по score
   ↓
№1 = всегда выбранный адрес
   ↓
score сохраняем
   ↓
confidence сохраняем как показатель качества
   ↓
STATUS = ASSIGNED
```

То есть даже:

```text
score = 0.31
confidence = NO_MATCH
```

будет означать:

```text
MATCH = адрес кандидата №1
STATUS = ASSIGNED
```

а не:

```text
MATCH = NONE
```

**`threshold=0.65` при этом больше не будет отбрасывать первый кандидат.** Мы можем оставить параметр CLI для совместимости со старыми командами, но фактически использовать его только при необходимости для диагностики.

---

### 👤 **User** — 2026-08-14 23:39:43

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '180,420p' app/core/recognizer.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ wc -l app/core/recognizer.py
397 app/core/recognizer.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '180,520p' app/core/recognizer.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:39:44

Отлично. Теперь всё видно. Причина ровно здесь:

```python
# Threshold is still an absolute safety gate.
if best_score < threshold:
    best_id = None
    status = "NO_MATCH"
else:
    best_id = best["id"]
```

**Меняем только эту логику.** Сам рейтинг кандидатов, score, margin и confidence оставляем — они нам нужны.

Я предлагаю сделать ещё лучше: `status` будет показывать качество распознавания, но **адрес всегда будет назначен**.

### 1. Сделай резервную копию

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/core/recognizer.py app/core/recognizer.py.backup_before_force_match
```

### 2. Замени участок

Выполни:

```bash
python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''            # Threshold is still an absolute safety gate.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
'''

new = '''            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
            else:
                status = self._status_from_confidence(
                    confidence
                )
'''

if old not in text:
    raise SystemExit(
        "ERROR: target block was not found. "
        "File was NOT modified."
    )

p.write_text(text.replace(old, new))

print("OK: recognizer.py updated.")
print("Threshold is now informational; first candidate is always assigned.")
PY
```

### 3. Проверяем

```bash
grep -n -A18 -B5 "Always use the best available candidate" \
    app/core/recognizer.py
```

Должно получиться примерно:

```text
# Always use the best available candidate.
#
# The threshold is NO LONGER a rejection gate.
# Even a weak candidate is accepted as the best
# available address. The score/confidence are kept
# for diagnostics.
best_id = best["id"]

if best_score < threshold:
    status = "FORCED_MATCH"
else:
    status = self._status_from_confidence(
        confidence
    )
```

### Что теперь будет

Например, было:

```text
PHOTO: IMG_001.jpg

1. 78_v33    0.48
2. 82_v33    0.45
3. 79_v33    0.41

threshold = 0.65
```

**Раньше:**

```text
MATCH      NONE
SCORE      0.4800
CONFIDENCE NO_MATCH
STATUS     NO_MATCH
```

**Теперь:**

```text
MATCH      78_v33
SCORE      0.4800
CONFIDENCE NO_MATCH
STATUS     FORCED_MATCH
```

То есть:

> **78_v33 — это не обязательно хороший match, но это лучший из имеющихся кандидатов, поэтому фотографию относим туда.**

И это именно то, что ты сейчас хочешь.

---

### Но есть важный момент

`query_embedding` у тебя сейчас вычисляется:

```python
queries = self.embedder.embed_paths(paths)
```

но дальше практически **не используется** — окончательное сравнение делает:

```python
self.analyzer.compare(
    Path(path),
    fingerprint_id,
)
```

Поэтому следующим шагом я бы **не стал сразу обновлять fingerprint после каждого фото**.

Сначала проверим, что новая политика выбора работает на реальных фотографиях:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize \
    data/input/new \
    --top-k 5 \
    --threshold 0.65
```

Если каталог с тестовыми новыми фотографиями у тебя называется иначе — подставь его.

**Пока не делаем самообновление слепка.** Сначала посмотрим распределение `FORCED_MATCH`, `AMBIGUOUS`, `PROBABLE_MATCH`, `CONFIDENT`. Если первый кандидат действительно в большинстве случаев оказывается правильным, следующим шагом сделаем механизм:

```text
НОВАЯ ФОТО
    ↓
TOP-1
    ↓
назначение адреса
    ↓
пополнение набора адреса
    ↓
пересчёт fingerprint
    ↓
следующая фотография
    ↓
TOP-1 уже с улучшенным слепком
```

Это будет гораздо интереснее простого `threshold=0`.

---

### 👤 **User** — 2026-08-14 23:40:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''            # Threshold is still an absolute safety gate.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
'''

new = '''            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
PYint("Threshold is now informational; first candidate is always assigned.")
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:40:18

Да, здесь две проблемы:

1. У тебя в системе нет команды `python`, есть `python3`.
2. И главное — ты случайно вставил строку `PYint(...)` вместо завершающего `PY`. Поэтому файл **не изменился**.

Поскольку проект у тебя запускается через `uv`, лучше использовать его Python. Сделаем безопасно.

### 1. Сначала проверь, что файл не изменился

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -n -A12 -B3 "Threshold is still" app/core/recognizer.py
```

Должен быть старый блок.

### 2. Сделай резервную копию

```bash
cp app/core/recognizer.py app/core/recognizer.py.backup_before_force_match
```

### 3. Теперь выполни исправленный вариант

**Важно: последняя строка должна быть именно `PY` — без каких-либо символов после неё.**

```bash
uv run python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''            # Threshold is still an absolute safety gate.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
'''

new = '''            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
            else:
                status = self._status_from_confidence(
                    confidence
                )
'''

if old not in text:
    raise SystemExit(
        "ERROR: target block was not found. File was NOT modified."
    )

p.write_text(text.replace(old, new))

print("OK: recognizer.py updated.")
print("First candidate is now always assigned.")
PY
```

### 4. Проверяем

```bash
grep -n -A18 -B5 "Always use the best available candidate" \
    app/core/recognizer.py
```

И ещё проверим синтаксис:

```bash
uv run python -m py_compile app/core/recognizer.py
```

Если получишь:

```text
OK
```

или просто отсутствие ошибок — всё нормально.

После этого **не запускай пока весь распознаватель**. Покажи мне вывод двух последних команд. Затем проверим работу на твоём наборе фотографий.

---

### 👤 **User** — 2026-08-14 23:40:36

int_mvp_v02

grep -n -A12 -B3 "Threshold is still" app/core/recognizer.py
340-                )
341-            )
342-
343:            # Threshold is still an absolute safety gate.
344-            if best_score < threshold:
345-                best_id = None
346-                status = "NO_MATCH"
347-            else:
348-                best_id = best["id"]
349-
350-            results.append(
351-                {
352-                    "file": str(path),
353-
354-                    "best_id": best_id,
355-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:40:37

Отлично — файл **не изменён**, всё в порядке. Сейчас в нём старый блок.

Теперь выполни только эту команду целиком:

```bash
uv run python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''            # Threshold is still an absolute safety gate.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
'''

new = '''            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
            else:
                status = self._status_from_confidence(
                    confidence
                )
'''

if old not in text:
    raise SystemExit(
        "ERROR: target block was not found. File was NOT modified."
    )

p.write_text(text.replace(old, new))

print("OK: recognizer.py updated.")
print("First candidate is now always assigned.")
PY
```

Затем сразу:

```bash
grep -n -A18 -B5 "Always use the best available candidate" app/core/recognizer.py
```

И:

```bash
uv run python -m py_compile app/core/recognizer.py
```

**Пришли вывод этих двух команд.**

---

### 👤 **User** — 2026-08-14 23:41:10

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n -A18 -B5 "Always use the best available candidate" app/core/recognizer.py
338-                self._status_from_confidence(
339-                    confidence
340-                )
341-            )
342-
343:            # Always use the best available candidate.
344-            #
345-            # The threshold is NO LONGER a rejection gate.
346-            # Even a weak candidate is accepted as the best
347-            # available address. The score/confidence are kept
348-            # for diagnostics.
349-            best_id = best["id"]
350-
351-            if best_score < threshold:
352-                status = "FORCED_MATCH"
353-            else:
354-                status = self._status_from_confidence(
355-                    confidence
356-                )
357-
358-            results.append(
359-                {
360-                    "file": str(path),
361-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/core/recognizer.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:41:11

Отлично. **Изменение применилось, синтаксис корректный.**

Теперь поведение именно такое:

- `best_id` всегда равен ID первого кандидата.
- `threshold` больше **не отбрасывает** кандидата.
- Если `score < threshold` → `status = FORCED_MATCH`.
- Если `score >= threshold` → сохраняется нормальный статус `CONFIDENT / PROBABLE_MATCH / AMBIGUOUS`.
- `score`, `margin` и `confidence` остаются в результате для анализа качества.

Теперь можем проверить на реальных фотографиях.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize \
    data/input/new \
    --top-k 5 \
    --threshold 0.65
```

Если твой тестовый каталог называется не `data/input/new`, подставь фактический путь.

**Пришли весь вывод распознавания.** Особенно интересуют несколько фотографий с низким score — посмотрим, действительно ли TOP-1 выглядит разумно.

Пока **не меняем слепки и не добавляем новые фотографии в fingerprints**. Сначала проверяем чистое распознавание.

---

### 👤 **User** — 2026-08-14 23:46:16

можно как то распараллелить вычисления на разные ядра процессора

---

### 🤖 **Assistant** — 2026-08-14 23:46:17

Да. И в твоём случае **это имеет смысл**, но важно правильно распараллелить.

Сейчас у тебя основное узкое место, скорее всего, вот здесь:

```python
for path, query_embedding in zip(paths, queries):
    ...
    for fingerprint_id, data in fingerprints:
        score = self.analyzer.compare(
            Path(path),
            fingerprint_id,
        )
```

То есть фотографии и fingerprint'ы фактически сравниваются последовательно.

### Я бы сделал так

Не распараллеливать DINO на CPU — у тебя RTX 3060, и `embed_paths()` уже должен использовать GPU.

А распараллелить **сравнение фотографий с fingerprint'ами на CPU**.

Схема:

```text
                 200–300 фотографий
                         │
                         ▼
                  DINO на GPU
                         │
                         ▼
              ┌────────────────────┐
              │ 768-d embeddings   │
              └────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       CPU ядро 1     CPU ядро 2     CPU ядро 3 ...
          │              │              │
       compare()      compare()      compare()
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   TOP-1 / TOP-K
```

Но есть **ещё более важный вариант**.

Сейчас `query_embedding` вычисляется:

```python
queries = self.embedder.embed_paths(paths)
```

а затем `self.analyzer.compare()` снова получает:

```python
Path(path)
```

То есть есть риск, что внутри `compare()` изображение снова читается и вычисляются дополнительные признаки.

Если `compare()` действительно повторно обрабатывает изображение, то оптимизация может дать **очень большой прирост**.

### Вариант, который я предлагаю

Сделать worker pool:

```python
from concurrent.futures import ThreadPoolExecutor
```

и распределять:

```text
IMG001 → CPU worker 1
IMG002 → CPU worker 2
IMG003 → CPU worker 3
IMG004 → CPU worker 4
...
```

Например, если у тебя 12 CPU threads:

```python
workers = 10
```

GPU при этом продолжает заниматься DINO.

---

### Но есть нюанс с PyTorch

Если внутри `SceneAnalyzer` используется PyTorch / NumPy, простое увеличение количества потоков не всегда ускоряет работу. Иногда получается:

```text
12 Python workers
       ↓
12 × PyTorch threads
       ↓
144 конкурирующих потока
       ↓
CPU перегружен
       ↓
становится МЕДЛЕННЕЕ
```

Поэтому я бы сделал управляемый параметр:

```bash
--workers 8
```

и мог запускать:

```bash
uv run scene-fingerprint recognize \
    data/input/new \
    --top-k 5 \
    --workers 8
```

---

### Ещё лучше — распараллелить по fingerprint

Если у тебя, например:

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

то для одной фотографии можно одновременно считать:

```text
                 IMG
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
      78          79         80 ...
       │          │          │
       ▼          ▼          ▼
     score       score      score
       └──────────┼──────────┘
                  ▼
                TOP-1
```

Это особенно эффективно, если fingerprint'ов станет **десятки или сотни**.

---

### А вот когда адресов станет много

Я бы вообще убрал полный цикл:

```text
300 фотографий
×
100 fingerprint
=
30 000 compare()
```

и сделал двухступенчатый поиск:

```text
                 ФОТО
                   │
                   ▼
             DINO embedding
                   │
                   ▼
             FAISS поиск
                   │
             TOP 10 адресов
                   │
                   ▼
       подробный SceneAnalyzer
                   │
                   ▼
               TOP-1
```

Тогда вместо:

```text
300 × 100 = 30 000
```

получаем примерно:

```text
300 × 10 = 3 000
```

а при сотнях адресов выигрыш будет ещё намного больше.

---

**Но сейчас я бы не стал сразу переписывать архитектуру.** У нас уже есть рабочий `recognizer.py`, и сначала надо посмотреть, **что именно делает `SceneAnalyzer.compare()`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' app/core/scene_analyzer.py
```

Пришли вывод. По нему я скажу, **где именно поставить multiprocessing/ThreadPool и сколько workers оптимально для твоей RTX 3060 + CPU**, чтобы не получить обратное замедление.

---

### 👤 **User** — 2026-08-14 23:47:39

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' app/core/scene_analyzer.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:47:42

Вот теперь видно важную вещь: **распараллеливание действительно стоит делать, и даже более эффективно, чем я предполагал.**

Главная проблема сейчас — не CPU, а вот это:

```python
query_global = self.embedder.embed_paths(
    [Path(image_path)]
)[0]
```

`recognizer.py` уже один раз вычисляет:

```python
queries = self.embedder.embed_paths(paths)
```

но затем `SceneAnalyzer.compare()` **заново запускает DINO для каждой фотографии и каждого fingerprint**.

То есть при 300 фото и 10 адресах потенциально получается до:

```text
300 × 10 = 3000
```

повторных DINO-вызовов.

Это гораздо хуже, чем отсутствие многопоточности.

### Поэтому предлагаю сначала исправить архитектуру

Сделаем так:

```text
300 фотографий
      │
      ▼
ОДИН проход DINO на GPU
      │
      ├── embedding IMG001
      ├── embedding IMG002
      ├── ...
      └── embedding IMG300
             │
             ▼
      CPU / NumPy / OpenCV
             │
       параллельные compare
             │
             ▼
       TOP-1 / TOP-K
```

И передавать уже рассчитанный `query_embedding` в `compare()`:

```python
compare(
    image_path,
    fingerprint_id,
    query_global=query_embedding,
)
```

Тогда DINO **вообще не будет повторно запускаться**.

А вот `environment/color/spatial` — действительно CPU-задачи, и их уже можно распараллелить.

Но прежде чем менять это, нужен остаток `scene_analyzer.py`, потому что сейчас вывод оборвался на:

```python
best_index = int(
```

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '300,520p' app/core/scene_analyzer.py
```

Пришли вывод.

После этого я предложу сразу **правильную оптимизацию в два этапа**:

1. убрать повторные DINO-вызовы — это даст основной прирост;
2. затем добавить контролируемое использование CPU-ядер, например `--workers 8`.

И только после этого будем думать об FAISS/масштабировании на большое количество адресов.

---

### 👤 **User** — 2026-08-14 23:48:25

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '300,520p' app/core/scene_analyzer.py
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

        spatial_score = (
            self.descriptor_similarity(
                query_spatial,
                data[
                    "spatial_embeddings"
                ],
            )
        )

        final_score = (
            self.GLOBAL_WEIGHT
            * global_score
            + self.ENVIRONMENT_WEIGHT
            * environment_score
            + self.COLOR_WEIGHT
            * color_score
            + self.SPATIAL_WEIGHT
            * spatial_score
        )

        return {
            "global_score": float(
                global_score
            ),
            "best_image_score": float(
                best_image_score
            ),
            "patch_score": 0.0,
            "color_score": float(
                color_score
            ),
            "spatial_score": float(
                spatial_score
            ),
            "environment_score": float(
                environment_score
            ),
            "final_score": float(
                final_score
            ),
            "best_image": best_image,
            "fingerprint_version": (
                data["metadata"]
                .get(
                    "version",
                    "3.3",
                )
            ),
        }

    def analyze(
        self,
        folder,
        fingerprint_id,
    ):
        from .image import image_files

        paths = image_files(folder)

        for path in paths:
            result = self.compare(
                Path(path),
                fingerprint_id,
            )

            result["file"] = str(path)

            yield result
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:48:26

Да. Теперь картина полная.

**Самое важное:** сейчас распараллеливать CPU — не первый приоритет. У тебя есть гораздо более серьёзное узкое место.

### Что сейчас происходит

Для каждой фотографии `recognizer.py` уже делает один DINO-проход:

```text
300 фото
↓
embed_paths(paths)
↓
300 embeddings
```

Но потом для **каждого fingerprint** `compare()` снова делает:

```python
query_global = self.embedder.embed_paths(
    [Path(image_path)]
)[0]
```

Если 300 фотографий и 10 адресов:

```text
300 × 10 = 3000 повторных DINO inference
```

Причём один и тот же embedding фотографии вычисляется снова и снова.

Это нужно убрать в первую очередь.

---

# Что предлагаю сделать

Изменяем `SceneAnalyzer.compare()` так, чтобы он мог принимать уже рассчитанный embedding:

```python
compare(
    image_path,
    fingerprint_id,
    query_global=query_embedding,
)
```

Тогда схема станет:

```text
             300 фотографий
                    │
                    ▼
              DINO на GPU
                    │
                    ▼
            300 embeddings
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     CPU          CPU          CPU
   address 78   address 79   address 80
       │            │            │
       └────────────┼────────────┘
                    ▼
                 TOP-1
```

И только `environment / color / spatial` будут рассчитываться на CPU.

---

## А вот здесь уже можно использовать ядра

После исправления DINO мы можем сделать:

```text
RTX 3060
    ↓
DINO embeddings

CPU:
    worker 1 → фото 1
    worker 2 → фото 2
    worker 3 → фото 3
    ...
    worker 8 → фото 8
```

Я бы начал с **6–8 workers**, а не сразу со всех ядер.

Потому что OpenCV и NumPy сами могут создавать дополнительные потоки.

---

# Но есть ещё более сильная оптимизация

Посмотри на эти три операции:

```python
CompactDescriptor.environment(...)
CompactDescriptor.color(...)
CompactDescriptor.spatial(...)
```

Они вызываются **для каждого сравнения с каждым fingerprint**.

То есть если:

```text
300 фотографий
10 адресов
```

мы сейчас считаем:

```text
environment: 3000 раз
color:       3000 раз
spatial:     3000 раз
```

Хотя дескрипторы фотографии **не зависят от fingerprint**.

Их тоже надо вычислять один раз:

```text
Фото
 │
 ├── DINO embedding       ← 1 раз
 ├── environment          ← 1 раз
 ├── color                ← 1 раз
 └── spatial              ← 1 раз
          │
          ▼
       сравнение
          │
     ┌────┼────┐
     ▼    ▼    ▼
    78   79   80 ...
```

Это уже даст очень существенное ускорение.

---

# Поэтому я предлагаю сделать v3.4

Не просто добавить multiprocessing, а нормально перестроить вычисления:

### Сейчас

```text
PHOTO
 ├─ DINO × fingerprints
 ├─ environment × fingerprints
 ├─ color × fingerprints
 └─ spatial × fingerprints
```

### После оптимизации

```text
PHOTO
 ├─ DINO ────────────────┐
 ├─ environment ─────────┤
 ├─ color ────────────────┤
 └─ spatial ──────────────┤
                          ▼
                  сравнение с FP
                    78 79 80...
```

То есть для 300 фото и 10 fingerprint'ов вместо условных:

```text
3000 DINO
3000 environment
3000 color
3000 spatial
```

получим:

```text
300 DINO
300 environment
300 color
300 spatial
```

А уже **сами матричные сравнения** NumPy выполнит очень быстро.

---

## И ещё один плюс

У тебя уже есть:

```python
query_embedding
```

в `recognizer.py`, но сейчас он фактически бесполезен.

После изменения мы наконец начнём его использовать.

---

### Я предлагаю не делать пока multiprocessing

Сначала делаем **кэширование всех признаков одной фотографии**, затем замеряем скорость.

После этого уже добавим:

```bash
--workers 8
```

если CPU действительно остаётся узким местом.

Это безопаснее и даст нам возможность понять, **что именно ограничивает скорость**, а не просто загрузить все ядра CPU.

Если согласен, следующим сообщением дам **готовую замену `scene_analyzer.py` + небольшую замену `recognizer.py`**, которую можно вставить командами из терминала.

---

### 👤 **User** — 2026-08-14 23:55:41

Если согласен, следующим сообщением дам **готовую замену** **`scene_analyzer.py`** **+ небольшую замену** **`recognizer.py`**, которую можно вставить командами из терминала.

---

### 🤖 **Assistant** — 2026-08-14 23:55:43

Да. Делаем. Причём я предлагаю **сразу сделать правильную оптимизацию**, а не просто добавить многопоточность.

Будем менять две вещи:

1. `SceneAnalyzer.compare()` получит уже рассчитанный DINO embedding.
2. `environment / color / spatial` для каждой фотографии будут рассчитываться **один раз**, а не заново для каждого адреса.

После этого уже измерим скорость и, если потребуется, добавим `--workers`.

### 1. Сначала резервные копии

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/core/scene_analyzer.py app/core/scene_analyzer.py.backup_before_optimization
cp app/core/recognizer.py app/core/recognizer.py.backup_before_optimization

echo "BACKUPS CREATED"
```

### 2. Я дам тебе готовую замену `scene_analyzer.py`

Но есть один важный момент: **не хочу сейчас присылать сокращённую версию файла**, потому что у тебя уже рабочая v3.3 и мы должны сохранить всю текущую логику.

Сделаем безопаснее: сначала изменим `SceneAnalyzer` минимально.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from pathlib import Path

p = Path("app/core/scene_analyzer.py")
text = p.read_text()

old = '''    def compare(
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
'''

new = '''    def compare(
        self,
        image_path: Path,
        fingerprint_id: str,
        query_global=None,
        query_environment=None,
        query_color=None,
        query_spatial=None,
    ):
        data = self.manager.load(
            fingerprint_id
        )

        # Reuse precomputed descriptors when supplied.
        # This prevents recalculating the same image features
        # for every fingerprint.
        if query_global is None:
            query_global = (
                self.embedder.embed_paths(
                    [Path(image_path)]
                )[0]
            )

        query_global = np.asarray(
            query_global,
            dtype=np.float32,
        )

        if query_environment is None:
            query_environment = (
                CompactDescriptor.environment(
                    Path(image_path)
                )
            )

        if query_color is None:
            query_color = (
                CompactDescriptor.color(
                    Path(image_path)
                )
            )

        if query_spatial is None:
            query_spatial = (
                CompactDescriptor.spatial(
                    Path(image_path)
                )
            )
'''

if old not in text:
    raise SystemExit(
        "ERROR: target block not found. File was NOT modified."
    )

text = text.replace(old, new)

old2 = '''        query_environment = (
            CompactDescriptor.environment(
                Path(image_path)
            )
        )

        environment_score = (
'''

new2 = '''        environment_score = (
'''

if old2 not in text:
    raise SystemExit(
        "ERROR: environment block not found. File was NOT modified."
    )

text = text.replace(old2, new2)

old3 = '''        query_color = (
            CompactDescriptor.color(
                Path(image_path)
            )
        )

        color_score = (
'''

new3 = '''        color_score = (
'''

if old3 not in text:
    raise SystemExit(
        "ERROR: color block not found. File was NOT modified."
    )

text = text.replace(old3, new3)

old4 = '''        query_spatial = (
            CompactDescriptor.spatial(
                Path(image_path)
            )
        )

        spatial_score = (
'''

new4 = '''        spatial_score = (
'''

if old4 not in text:
    raise SystemExit(
        "ERROR: spatial block not found. File was NOT modified."
    )

text = text.replace(old4, new4)

p.write_text(text)

print("OK: SceneAnalyzer optimized for descriptor reuse.")
PY
```

### 3. Проверяем синтаксис

```bash
uv run python -m py_compile app/core/scene_analyzer.py
```

Если ошибок нет — отлично.

### 4. Теперь меняем `recognizer.py`

Нам нужно передавать уже рассчитанные признаки.

Сейчас у тебя:

```python
for path, query_embedding in zip(
    paths,
    queries,
):
    ranked = []
```

Заменим на предварительный расчёт:

```bash
uv run python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''        results = []

        for path, query_embedding in zip(
            paths,
            queries,
        ):
            ranked = []
'''

new = '''        results = []

        # Calculate CPU descriptors ONCE per image.
        # They do not depend on the fingerprint.
        query_descriptors = {}

        for path in paths:
            print(
                f"[Recognizer] Descriptors: "
                f"{Path(path).name}"
            )

            query_descriptors[str(path)] = {
                "environment": (
                    self.analyzer.__class__.__mro__[0]
                    and __import__(
                        "app.core.scene_analyzer",
                        fromlist=["CompactDescriptor"],
                    ).CompactDescriptor.environment(
                        Path(path)
                    )
                ),
                "color": (
                    __import__(
                        "app.core.scene_analyzer",
                        fromlist=["CompactDescriptor"],
                    ).CompactDescriptor.color(
                        Path(path)
                    )
                ),
                "spatial": (
                    __import__(
                        "app.core.scene_analyzer",
                        fromlist=["CompactDescriptor"],
                    ).CompactDescriptor.spatial(
                        Path(path)
                    )
                ),
            }

        for path, query_embedding in zip(
            paths,
            queries,
        ):
            ranked = []

            descriptors = query_descriptors[
                str(path)
            ]
'''

if old not in text:
    raise SystemExit(
        "ERROR: recognizer target block not found. File was NOT modified."
    )

text = text.replace(old, new)

old2 = '''                    score = self.analyzer.compare(
                        Path(path),
                        fingerprint_id,
                    )
'''

new2 = '''                    score = self.analyzer.compare(
                        Path(path),
                        fingerprint_id,
                        query_global=query_embedding,
                        query_environment=descriptors[
                            "environment"
                        ],
                        query_color=descriptors[
                            "color"
                        ],
                        query_spatial=descriptors[
                            "spatial"
                        ],
                    )
'''

if old2 not in text:
    raise SystemExit(
        "ERROR: compare call not found. File was NOT modified."
    )

text = text.replace(old2, new2)

p.write_text(text)

print("OK: Recognizer now reuses DINO and CPU descriptors.")
PY
```

После этого:

```bash
uv run python -m py_compile app/core/recognizer.py
```

Если обе проверки проходят без вывода — оптимизация установлена.

---

### Что мы получим

Было:

```text
300 фото × 10 адресов

DINO:         ~3000 раз
Environment:  ~3000 раз
Color:        ~3000 раз
Spatial:      ~3000 раз
```

Станет:

```text
300 фото

DINO:         300 раз
Environment:  300 раз
Color:        300 раз
Spatial:      300 раз

после этого:
300 × 10
только математическое сравнение
```

И вот **после этого** имеет смысл распараллеливание CPU. Скорее всего, после устранения повторных вычислений скорость уже вырастет очень заметно.

Пока выполни оба блока и пришли результат:

```bash
uv run python -m py_compile app/core/scene_analyzer.py
```

и

```bash
uv run python -m py_compile app/core/recognizer.py
```

Затем сделаем контрольный запуск и сравним скорость **до/после**.

---

### 👤 **User** — 2026-08-14 23:57:48

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/core/scene_analyzer.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/core/recognizer.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-14 23:57:51

Отлично. Оба файла компилируются — **синтаксически всё нормально**.

Но я хочу сразу поправить один момент в предыдущем изменении: в `recognizer.py` я использовал неудачный динамический импорт `__import__(...)`. Он работает, но для нашего проекта это лишняя сложность. Лучше сделать нормальный импорт `CompactDescriptor`.

Сначала проверим текущую работу оптимизации на реальном наборе, **ничего больше пока не меняя**.

### 1. Посмотрим количество фотографий

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/input/new -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l
```

Если каталога `data/input/new` нет, покажи:

```bash
find data/input -maxdepth 2 -type d | sort
```

### 2. Запустим распознавание с замером времени

```bash
/usr/bin/time -f '\nREAL TIME: %E\nCPU: %P' \
uv run scene-fingerprint recognize \
data/input/new \
--top-k 5 \
--threshold 0.65
```

Если фотографий 200–300, **первый запуск может быть ещё не показательным** из-за загрузки модели и прогрева GPU.

### 3. Важный момент

Сейчас мы ещё **не включали распараллеливание CPU**.

Сначала хочу увидеть реальное время после устранения:

- повторных DINO inference;
- повторного `environment`;
- повторного `color`;
- повторного `spatial`.

После этого уже можно сделать следующий уровень:

```text
GPU
 └── DINO: один проход

CPU
 ├── worker 1
 ├── worker 2
 ├── worker 3
 ├── ...
 └── worker N
```

И добавить в CLI:

```bash
--workers 8
```

Причём я бы сделал автоматический выбор количества ядер, например:

```text
CPU 8 потоков  → 6 workers
CPU 16 потоков → 10 workers
CPU 24 потока  → 14 workers
```

а не забивать CPU на 100%, чтобы система оставалась отзывчивой.

**Сейчас запусти замер времени и пришли вывод.** Особенно интересует последняя строка `REAL TIME`.

---

### 👤 **User** — 2026-08-14 23:59:04

сколько оптимально положить фото в new

---


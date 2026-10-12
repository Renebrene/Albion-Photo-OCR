### 🔧 **Ошибка в `recognizer.py` — исправляем**

Ошибка возникает из-за **неправильного вставления shell-команды в Python-файл**. В предыдущем ответе я ошибочно вставил строку:

```python
cd ~/projects/scene_fingerprint_mvp_v02
```

внутрь `recognizer.py`, что вызывает `SyntaxError`.

---

### ✅ **Правильный `recognizer.py` (без shell-команд)**

Замени содержимое файла `app/core/recognizer.py` на следующий код:

```python
from __future__ import annotations

from pathlib import Path

import numpy as np

from .image import image_files
from .scene_analyzer import SceneAnalyzer

class SceneRecognizer:
    """
    Recognition engine for Scene Fingerprint v3.x / v3.2 compact.

    Pipeline:

        1. Load all valid fingerprints.
        2. Calculate global DINO similarity for every fingerprint.
        3. Keep a larger candidate pool.
        4. Calculate the full SceneAnalyzer score.
        5. Rank by FINAL score.
        6. Apply threshold to FINAL.

    v3.2 compact does NOT use DINO patch embeddings.
    """

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

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _normalize(vectors):
        vectors = np.asarray(
            vectors,
            dtype=np.float32,
        )

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        norms = np.linalg.norm(
            vectors,
            axis=1,
            keepdims=True,
        )

        norms[norms == 0] = 1.0

        return vectors / norms

    @staticmethod
    def _is_v32(data):
        metadata = data.get(
            "metadata",
            {},
        )

        return (
            str(
                metadata.get(
                    "version",
                    "",
                )
            ) == "3.2"
        )

    @staticmethod
    def _has_compact_descriptors(data):
        required = (
            "environment_embeddings",
            "color_embeddings",
            "spatial_embeddings",
        )

        return all(
            key in data
            for key in required
        )

    # ---------------------------------------------------------
    # Main recognition
    # ---------------------------------------------------------

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        folder = Path(folder)

        paths = image_files(folder)

        if not paths:
            return []

        print(
            f"[Recognizer] Query images: {len(paths)}"
        )

        # -----------------------------------------------------
        # Load fingerprints
        # -----------------------------------------------------

        fingerprints = []

        for metadata in self.manager.list_fingerprints():

            fingerprint_id = metadata.get(
                "id"
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

            # -------------------------------------------------
            # v3.2 compact
            # -------------------------------------------------

            if self._is_v32(data):

                if not self._has_compact_descriptors(
                    data
                ):
                    print(
                        f"[Recognizer] SKIP "
                        f"{fingerprint_id}: "
                        f"incomplete v3.2 compact"
                    )
                    continue

                fingerprints.append(
                    (
                        fingerprint_id,
                        data,
                    )
                )

                continue

            # -------------------------------------------------
            # Older fingerprints
            #
            # We don't use them for the compact v3.2
            # recognition database.
            # -------------------------------------------------

            print(
                f"[Recognizer] SKIP old fingerprint "
                f"{fingerprint_id} "
                f"(version="
                f"{data.get('metadata', {}).get('version', '?')})"
            )

        if not fingerprints:

            raise ValueError(
                "No compatible v3.2 compact fingerprints "
                "found."
            )

        print(
            "[Recognizer] Fingerprints: "
            + ", ".join(
                fp_id
                for fp_id, _ in fingerprints
            )
        )

        # -----------------------------------------------------
        # Query global embeddings
        # -----------------------------------------------------

        queries = self.embedder.embed_paths(
            paths
        )

        queries = self._normalize(
            queries
        )

        results = []

        # -----------------------------------------------------
        # Process every image
        # -----------------------------------------------------

        for path, query_embedding in zip(
            paths,
            queries,
        ):

            # -------------------------------------------------
            # Stage 1:
            # global centroid pre-ranking
            # -------------------------------------------------

            pre_candidates = []

            for fingerprint_id, data in fingerprints:

                centroid = np.asarray(
                    data["centroid"],
                    dtype=np.float32,
                ).reshape(-1)

                global_score = self._cosine(
                    query_embedding,
                    centroid,
                )

                pre_candidates.append(
                    (
                        fingerprint_id,
                        global_score,
                    )
                )

            pre_candidates.sort(
                key=lambda item: item[1],
                reverse=True,
            )

            # -------------------------------------------------
            # Stage 2:
            # full v3.2 comparison
            #
            # With only 5-20 fingerprints this is cheap.
            # Use ALL fingerprints rather than only top few.
            # This is important when compact descriptors
            # overturn the global ranking.
            # -------------------------------------------------

            ranked = []

            for fingerprint_id, _ in pre_candidates:

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
                        f"[Recognizer] "
                        f"SKIP {fingerprint_id} "
                        f"for {Path(path).name}: "
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
                                0
                            )
                        ),

                        "environment": float(
                            score.get(
                                "environment_score",
                                0
                            )
                        ),

                        "color": float(
                            score.get(
                                "color_score",
                                0
                            )
                        ),

                        "spatial": float(
                            score.get(
                                "spatial_score",
                                0
                            )
                        ),

                        "best_image": score.get(
                            "best_image"
                        ),

                        "best_image_score": float(
                            score.get(
                                "best_image_score",
                                0
                            )
                        ),
                    }
                )

            # -------------------------------------------------
            # Final ranking
            # -------------------------------------------------

            ranked.sort(
                key=lambda item: item["score"],
                reverse=True,
            )

            ranked = ranked[
                :max(1, int(top_k))
            ]

            if ranked:

                best = ranked[0]

                best_id = best["id"]
                best_score = best["score"]

                if best_score < threshold:
                    best_id = None

            else:

                best_id = None
                best_score = 0.0

            results.append(
                {
                    "file": str(path),

                    "best_id": best_id,

                    "score": float(
                        best_score
                    ),

                    "candidates": ranked,
                }
            )

        return results

    # ---------------------------------------------------------
    # Cosine
    # ---------------------------------------------------------

    @staticmethod
    def _cosine(a, b):

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
```

---

### ✅ **Проверка синтаксиса**

```bash
uv run python -m py_compile app/core/recognizer.py
```

Должно вернуться **без ошибок**.

---

### 🔄 **Дополнительные шаги**

1. **Убедись, что `cli.py` передаёт три аргумента:**

   ```python
   recognizer = SceneRecognizer(
       settings,
       embedder,
       manager,
   )
   ```

   Проверь с помощью:

   ```bash
   sed -n '100,190p' app/cli.py
   ```

   В секции `recognize` должно быть:

   ```python
   embedder = SceneEmbedder(settings)
   manager = FingerprintManager(settings, embedder)
   recognizer = SceneRecognizer(settings, embedder, manager)
   ```

2. **Создай новые `*_v32` для 79–82:**

   ```bash
   uv run scene-fingerprint create 79_v32 data/input/79
   uv run scene-fingerprint create 80_v32 data/input/80
   uv run scene-fingerprint create 81_v32 data/input/81
   uv run scene-fingerprint create 82_v32 data/input/82
   ```

3. **Запусти снова:**

   ```bash
   uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65
   ```

---

### 📌 **Что будет дальше**

Если всё правильно, ты увидишь:

```text
[Recognizer] Query images: 9
[Recognizer] Fingerprints: 78_v32, 79_v32, 80_v32, 81_v32, 82_v32
```

и матрицу сцен, где `78_v32` будет отличаться от `79_v32` и т. д.

---

Если всё ещё возникают ошибки, напиши, что именно не работает — я помогу.
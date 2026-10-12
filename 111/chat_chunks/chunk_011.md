## СЕССИЯ: LORA

**Создано:** 2026-08-07 22:33:24
**Обновлено:** 2026-08-19 17:08:04
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c)

---

### 🤖 **Assistant** — 2026-08-10 21:14:56

> **Reconstructing v3.3 Fingerprinting and CLI Files**
>
> 
>
> Worked for 14s

Да. Я нашёл в истории именно тот вариант, который мы делали для **v3.3 compact + confidence/margin**, а также текущую структуру `embedder.py` с обязательным `settings`. Поэтому ниже даю согласованный комплект, а не смесь старых v3/v3.2 файлов.

Важно: **v3.3 остаётся compact** - никаких DINO patch tokens. В fingerprint сохраняются только global 768 + environment 640 + color 48 + spatial 32. Это соответствует твоему уже успешно созданному `78_v32`; новая версия будет `78_v33`. В истории также зафиксировано, что v3.3 должен добавлять confidence/margin без увеличения fingerprint. `Pasted text.txt`

### 1. `app/core/scene_analyzer.py`

```python
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
```

---

### 2. `app/core/fingerprint.py`

Здесь принципиальный момент: **v3.3 не хранит patch embeddings**, поэтому размер fingerprint остаётся компактным. Структура соответствует найденному в истории v3.3 варианту: `embeddings`, `centroid`, `representatives`, `representative_indices`, три compact descriptor массива, FAISS и metadata. `Pasted text.txt`

```python
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

            "embeddings": np.load(
                output / "embeddings.npy"
            ),

            "centroid": np.load(
                output / "centroid.npy"
            ),

            "representatives": np.load(
                output / "representatives.npy"
            ),

            "representative_indices": np.load(
                output
                / "representative_indices.npy"
            ),

            "environment_embeddings": np.load(
                output
                / "environment_embeddings.npy"
            ),

            "color_embeddings": np.load(
                output
                / "color_embeddings.npy"
            ),

            "spatial_embeddings": np.load(
                output
                / "spatial_embeddings.npy"
            ),

            "index": faiss.read_index(
                str(
                    output
                    / "faiss.index"
                )
            ),

            "patch_available": False,
        }
```

---

### 3. `app/core/recognizer.py`

Здесь уже добавляем именно то, ради чего мы переходили на v3.3: **score + second score + margin + confidence + status**. В истории этот блок был именно так задуман: HIGH / PROBABLE / AMBIGUOUS / NO_MATCH. `Pasted text.txt`

```python
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
```

---

### 4. `app/cli.py`

Здесь исправляю главную проблему последних запусков: у тебя `SceneEmbedder` **требует `settings`**, что подтверждено текущим `embedder.py`; старый вариант с `SceneEmbedder()` был неправильным и именно поэтому ты получил `TypeError`. `кусщп.docx`

```python
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

        analyzer = SceneAnalyzer(
            embedder,
            manager,
        )

        for result in analyzer.analyze(
            folder,
            args.fingerprint,
        ):
            print_analyze_result(
                result["file"],
                result,
            )

        return 0

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    if args.command == "recognize":

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

        recognizer = SceneRecognizer(
            settings,
            embedder,
            manager,
        )

        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
            )
        )

        if args.json:
            print(
                json.dumps(
                    results,
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for result in results:
                print_recognition_result(
                    result
                )

        return 0

    parser.print_help()

    return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Что сейчас сделать

**Старые fingerprint'ы не трогаем.** Создаём именно новую базу:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/fingerprints/78_v33

uv run python -m py_compile \
  app/cli.py \
  app/core/scene_analyzer.py \
  app/core/recognizer.py \
  app/core/fingerprint.py \
  app/core/embedder.py
```

Если компиляция прошла без ошибок:

```bash
uv run scene-fingerprint create \
  78_v33 \
  data/input/78
```

Потом:

```bash
uv run scene-fingerprint recognize \
  data/input/new \
  --top-k 5 \
  --threshold 0.65
```

И отдельно проверим одну базу:

```bash
uv run scene-fingerprint analyze \
  data/input/new \
  --fingerprint 78_v33
```

**Ожидаемая структура `78_v33`:**

```text
embeddings.npy
centroid.npy
representatives.npy
representative_indices.npy
environment_embeddings.npy
color_embeddings.npy
spatial_embeddings.npy
faiss.index
metadata.json
```

То есть **никаких `patch_embeddings.npy`**. Это принципиальное отличие от patch-token версии. Твой предыдущий v3.2 уже имел именно такой компактный набор файлов. `Pasted text.txt`

И ещё важный момент: я специально не стал использовать старый `upgrade_v3.sh` как готовый источник - он относится к другой ветке, где v3 использовал настоящие DINO patch tokens и `patch_embeddings.npy`. `upgrade_v3.sh` Для нашей текущей задачи нужен именно **v3.3 compact**.

После запуска `create 78_v33` пришли **весь вывод**, особенно последние строки с shapes и `metadata`. Тогда сразу проверим, что v3.3 действительно собрался правильно, и перейдём к качеству `recognize`. `Pasted text.txt`

---

### 👤 **User** — 2026-08-10 21:18:56

[Attachment: Pasted text(8).txt]

---

### 🤖 **Assistant** — 2026-08-10 21:18:59

> **Retrieved and reconstructed complete v3.3 scene fingerprint source files**
>
> 
>
> Worked for 13s

Да. **Нашёл файлы в истории чата / File Library.** И теперь видно, где именно мы остановились.

Главное: у нас уже есть **рабочая v3.3 compact**, что подтверждается вашим запуском:

- `78_v33` создаётся как `version: 3.3`;
- `environment=(82, 640)`;
- `color=(82, 48)`;
- `spatial=(82, 32)`;
- patch storage отключён;
- `recognize` уже выдаёт `HIGH / PROBABLE`;
- старые `3.2` корректно отбрасываются как несовместимые. `Pasted text.txt` `Pasted text.txt`

Но я вижу **важный момент**: найденные куски истории содержат несколько разных поколений `v3`, поэтому **нельзя просто брать старый `upgrade_v3.sh`** - там ещё patch-token архитектура и `version=3`, а нам нужна именно **v3.3 compact без patch storage**. `upgrade_v3.sh`

### Что предлагаю сделать сейчас

Не переписывать проект вслепую. Берём именно ту архитектуру, которая уже дала ваш успешный результат `78_v33`, и доводим её до чистой версии:

```text
v3.3 compact
├── DINOv2 global       768
├── environment        640
├── color                48
├── spatial              32
├── patch storage         0
│
├── final score
│   ├── global       0.70
│   ├── environment  0.20
│   ├── color        0.07
│   └── spatial      0.03
│
└── recognition
    ├── absolute score
    ├── second best
    ├── margin
    ├── HIGH
    ├── PROBABLE
    ├── AMBIGUOUS
    └── NO_MATCH
```

Именно такая схема соответствует созданному вами `78_v33`. `Pasted text.txt`

### И ещё одна важная проблема

В текущем результате:

```text
001 → 78_v33 0.9476
002 → 78_v33 0.9477
003 → 78_v33 0.9518
...
006 → 78_v33 0.8128
007 → 78_v33 0.8198
008 → 78_v33 0.8835
009 → 78_v33 0.8860
```

для `78_v33` единственного доступного fingerprint `SECOND=0.0000`, поэтому:

```text
MARGIN = SCORE
CONFIDENCE = HIGH/PROBABLE
```

**это пока не настоящий margin между конкурентами.** Это следствие того, что из базы v3.3 у вас сейчас фактически только `78_v33`; остальные fingerprints - старые версии и правильно отфильтрованы. `Pasted text.txt`

То есть следующий этап я бы сделал так:

1. **Не менять v3.3 compact descriptor.**
2. Исправить `recognizer`, чтобы он не называл результат `HIGH` только потому, что второго кандидата нет.
3. Если кандидат один - выдавать, например:
   ```text
   CONFIDENCE   HIGH_SINGLE
   STATUS       CONFIDENT_SINGLE
   ```
4. Когда появятся `79_v33`, `80_v33`, `81_v33`, `82_v33`, margin начнёт иметь реальный смысл.
5. Затем уже проверим **ложные совпадения между 78/79/80/81/82** - это сейчас гораздо важнее дальнейшего усложнения модели.

Я нашёл исходники `v3.3` в истории и могу продолжить **именно с этой версии, не возвращаясь к patch-token v3**. `Pasted text.txt`

---

### 👤 **User** — 2026-08-10 21:20:56

продолжаем на версии 3,3

---

### 🤖 **Assistant** — 2026-08-10 21:20:57

Продолжаем **строго с v3.3 compact**. Текущую рабочую базу не ломаем.

Следующий шаг я бы сделал не `v3.4`, а **нормально довёл v3.3 до полноценного распознавания нескольких fingerprint'ов**.

Сейчас у нас уже подтверждено:

```text
78_v33
DINO global       768
environment       640
color              48
spatial            32
patch storage       0
```

и `recognize` работает. `Pasted text.txt`

### Что делаем сейчас

**Этап 1 - создаём v3.3 для всех наборов:**

```bash
rm -rf data/fingerprints/79_v33
uv run scene-fingerprint create 79_v33 data/input/79

rm -rf data/fingerprints/80_v33
uv run scene-fingerprint create 80_v33 data/input/80

rm -rf data/fingerprints/81_v33
uv run scene-fingerprint create 81_v33 data/input/81

rm -rf data/fingerprints/82_v33
uv run scene-fingerprint create 82_v33 data/input/82
```

После этого должно быть:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
```

И только они должны участвовать в `recognize`.

### Этап 2 - контроль

Запускаем:

```bash
uv run scene-fingerprint recognize \
    data/input/new \
    --top-k 5 \
    --threshold 0.65
```

Тогда `SECOND` уже не будет `0.0000`.

Например:

```text
## 008.JPG

MATCH        79_v33
SCORE        0.8843
SECOND       78_v33
MARGIN       0.0010
CONFIDENCE   AMBIGUOUS
STATUS       REVIEW
```

И это **гораздо более полезный результат**, чем нынешний:

```text
MATCH        78_v33
SCORE        0.9476
SECOND       0.0000
MARGIN       0.9476
CONFIDENCE   HIGH
```

Потому что сейчас `78_v33` - единственный v3.3 fingerprint, а значит margin фактически ничего не говорит. Старые `3.2` правильно исключаются. `Pasted text.txt`

### Важный момент

**Не трогаем сейчас:**

- DINOv2;
- веса `0.70 / 0.20 / 0.07 / 0.03`;
- environment 640;
- color 48;
- spatial 32;
- отсутствие patch tokens;
- формат fingerprint.

Сначала получаем честное сравнение:

```text
new image
     ↓
 ┌─────────┐
 │ 78_v33  │
 │ 79_v33  │
 │ 80_v33  │
 │ 81_v33  │
 │ 82_v33  │
 └─────────┘
     ↓
 ranking
     ↓
score + second + margin
     ↓
confidence
```

**Сделай сейчас команды создания `79_v33`-`82_v33` выше и пришли весь вывод `recognize`.** По нему уже будем настраивать пороги `HIGH / PROBABLE / AMBIGUOUS / NO_MATCH`, а не гадать.

---

### 👤 **User** — 2026-08-10 21:23:28

(base) alexice\@NEURO:\~/projects/scene\_fingerprint\_mvp\_v02$ uv run scene-fingerprint recognize 
data/input/new 
\--top-k 5 
\--threshold 0.65
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2...
Using cache found in /home/alexice/.cache/torch/hub/facebookresearch\_dinov2\_main
/home/alexice/.cache/torch/hub/facebookresearch\_dinov2\_main/dinov2/layers/swiglu\_ffn.py:51: UserWarning: xFormers is not available (SwiGLU)
warnings.warn("xFormers is not available (SwiGLU)")
/home/alexice/.cache/torch/hub/facebookresearch\_dinov2\_main/dinov2/layers/attention.py:33: UserWarning: xFormers is not available (Attention)
warnings.warn("xFormers is not available (Attention)")
/home/alexice/.cache/torch/hub/facebookresearch\_dinov2\_main/dinov2/layers/block.py:40: UserWarning: xFormers is not available (Block)
warnings.warn("xFormers is not available (Block)")
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (v3.2 compact)
[SceneEmbedder] Ready.
[Recognizer] Query images: 9
[Recognizer] SKIP 78: Fingerprint '78' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 78\_patch: Fingerprint '78\_patch' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 78\_v3: Fingerprint '78\_v3' is incomplete. Missing: color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 78\_v31: Fingerprint '78\_v31' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 78\_v32: Fingerprint '78\_v32' is version '3.2', expected '3.3'
[Recognizer] SKIP 79: Fingerprint '79' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 79\_v31: Fingerprint '79\_v31' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 79\_v32: Fingerprint '79\_v32' is version '3.2', expected '3.3'
[Recognizer] SKIP 80: Fingerprint '80' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 80\_v31: Fingerprint '80\_v31' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 80\_v32: Fingerprint '80\_v32' is version '3.2', expected '3.3'
[Recognizer] SKIP 81: Fingerprint '81' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 81\_v31: Fingerprint '81\_v31' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 81\_v32: Fingerprint '81\_v32' is version '3.2', expected '3.3'
[Recognizer] SKIP 82: Fingerprint '82' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 82\_v31: Fingerprint '82\_v31' is incomplete. Missing: representative\_indices.npy, environment\_embeddings.npy, color\_embeddings.npy, spatial\_embeddings.npy
[Recognizer] SKIP 82\_v32: Fingerprint '82\_v32' is version '3.2', expected '3.3'
[Recognizer] Fingerprints: 78\_v33, 79\_v33, 80\_v33, 81\_v33, 82\_v33

## 001.JPG

MATCH        78\_v33
SCORE        0.9476
SECOND       0.8521
MARGIN       0.0956
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo076.JPG

TOP CANDIDATES

1. 78\_v33         0.9476
2. 79\_v33         0.8521
3. 82\_v33         0.8379
4. 81\_v33         0.8306
5. 80\_v33         0.8204

## 002.JPG

MATCH        78\_v33
SCORE        0.9477
SECOND       0.8578
MARGIN       0.0899
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo076.JPG

TOP CANDIDATES

1. 78\_v33         0.9477
2. 79\_v33         0.8578
3. 82\_v33         0.8471
4. 81\_v33         0.8326
5. 80\_v33         0.8247

## 003.JPG

MATCH        78\_v33
SCORE        0.9518
SECOND       0.8704
MARGIN       0.0813
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo040.JPG

TOP CANDIDATES

1. 78\_v33         0.9518
2. 79\_v33         0.8704
3. 82\_v33         0.8516
4. 81\_v33         0.8510
5. 80\_v33         0.8379

## 004.JPG

MATCH        78\_v33
SCORE        0.9417
SECOND       0.8657
MARGIN       0.0760
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo021.JPG

TOP CANDIDATES

1. 78\_v33         0.9417
2. 79\_v33         0.8657
3. 82\_v33         0.8547
4. 81\_v33         0.8467
5. 80\_v33         0.8348

## 005.JPG

MATCH        78\_v33
SCORE        0.9472
SECOND       0.8573
MARGIN       0.0898
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo040.JPG

TOP CANDIDATES

1. 78\_v33         0.9472
2. 79\_v33         0.8573
3. 81\_v33         0.8394
4. 82\_v33         0.8377
5. 80\_v33         0.8267

## 006.JPG

MATCH        80\_v33
SCORE        0.9666
SECOND       0.8217
MARGIN       0.1449
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   011.JPG

TOP CANDIDATES

1. 80\_v33         0.9666
2. 82\_v33         0.8217
3. 78\_v33         0.8128
4. 79\_v33         0.8107
5. 81\_v33         0.8057

## 007.JPG

MATCH        80\_v33
SCORE        0.9678
SECOND       0.8344
MARGIN       0.1334
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   012.JPG

TOP CANDIDATES

1. 80\_v33         0.9678
2. 82\_v33         0.8344
3. 78\_v33         0.8198
4. 81\_v33         0.8106
5. 79\_v33         0.8063

## 008.JPG

MATCH        79\_v33
SCORE        0.8843
SECOND       0.8835
MARGIN       0.0008
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (46).JPG

TOP CANDIDATES

1. 79\_v33         0.8843
2. 78\_v33         0.8835
3. 81\_v33         0.8814
4. 82\_v33         0.8591
5. 80\_v33         0.8501

## 009.JPG

MATCH        79\_v33
SCORE        0.8871
SECOND       0.8860
MARGIN       0.0010
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (59).JPG

TOP CANDIDATES

1. 79\_v33         0.8871
2. 78\_v33         0.8860
3. 81\_v33         0.8847
4. 82\_v33         0.8671
5. 80\_v33         0.8514
   (base) alexice\@NEURO:\~/projects/scene\_fingerprint\_mvp\_v02$

---

### 🤖 **Assistant** — 2026-08-10 21:23:28

Да. **v3.3 compact сейчас реально работает.** По этому выводу мы уже можем зафиксировать базовую точку и двигаться дальше.

### Что получилось

| Query | Match | Score | Margin | Confidence |
|---|---|---:|---:|---|
| 001 | 78_v33 | 0.9476 | 0.0956 | HIGH |
| 002 | 78_v33 | 0.9477 | 0.0899 | HIGH |
| 003 | 78_v33 | 0.9518 | 0.0813 | HIGH |
| 004 | 78_v33 | 0.9417 | 0.0760 | HIGH |
| 005 | 78_v33 | 0.9472 | 0.0898 | HIGH |
| 006 | 80_v33 | 0.9666 | 0.1449 | HIGH |
| 007 | 80_v33 | 0.9678 | 0.1334 | HIGH |
| 008 | 79_v33 | 0.8843 | **0.0008** | AMBIGUOUS |
| 009 | 79_v33 | 0.8871 | **0.0010** | AMBIGUOUS |

Главное: **confidence/margin уже работает правильно**. 008 и 009 не объявляются уверенным совпадением, хотя их абсолютный score высокий.

### Но есть важный момент

Сейчас v3.3 фактически показывает:

- `001–005 → 78`
- `006–007 → 80`
- `008–009 → 79`, но практически ничья с `78/81`

То есть следующая задача — **не повышать threshold**, а улучшить различимость близких fingerprint'ов.

И ещё важнее: у нас сейчас:

```text
GLOBAL_WEIGHT       = 0.70
ENVIRONMENT_WEIGHT  = 0.20
COLOR_WEIGHT        = 0.07
SPATIAL_WEIGHT      = 0.03
```

А `spatial` почти всегда очень высокий:

```text
0.97–0.99
```

Поэтому он мало помогает различать сцены. Аналогично `environment` у соседних fingerprint'ов часто очень близок.

### Я предлагаю v3.3.1

Не менять размер fingerprint'ов и не возвращать patch tokens.

Сделать следующий небольшой апгрейд:

1. **оставить DINO global 768**
2. оставить compact descriptors
3. добавить нормальную **confidence-модель**
4. использовать **margin + абсолютный score**
5. добавить **relative ranking**
6. для близких кандидатов применять дополнительный пересчёт
7. явно разделить:
   - `CONFIDENT`
   - `LIKELY`
   - `AMBIGUOUS`
   - `NO_MATCH`
8. выводить `best_image` и score
9. сохранить совместимость только с `v3.3`
10. **не увеличивать размер fingerprint**

То есть архитектуру сейчас не ломаем — сначала доводим качество распознавания.

И ещё: строки

```text
SKIP 78_v32 ... expected '3.3'
```

— **это нормально**. Старые v3.2 специально отфильтрованы. Сейчас recognizer использует только:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
```

### Следующий шаг

Я бы сейчас **не переписывал четыре файла вслепую**. У нас уже есть рабочий v3.3, поэтому лучше сделать **v3.3.1 поверх него**, сохранив рабочую часть.

Если идём дальше, я дам тебе **готовые целиком `scene_analyzer.py + recognizer.py + fingerprint.py + cli.py` для v3.3.1**, чтобы ты просто заменил файлы и выполнил:

```bash
uv run python -m py_compile \
app/core/scene_analyzer.py \
app/core/recognizer.py \
app/core/fingerprint.py \
app/cli.py
```

а затем пересоздадим только `78_v33 ... 82_v33` и проведём контрольный recognize.

---

### 👤 **User** — 2026-08-10 21:25:23

идём дальше

---

### 🤖 **Assistant** — 2026-08-10 21:25:24

Идём. Сейчас лучше сделать **v3.3.1 без изменения формата fingerprint**: улучшим именно ранжирование и confidence, не трогая рабочий compact descriptor.

Первое изменение — **для близких кандидатов учитывать не только `final_score`, но и margin**, чтобы случаи вроде `008/009` не выглядели почти так же уверенно, как `001–007`.

Сначала пришли текущий **полный** `app/core/recognizer.py` и `app/core/scene_analyzer.py` после перехода на v3.3 — именно те версии, которые сейчас дали приведённый вывод. Я на их основе дам готовые четыре файла без риска снова сломать рабочую v3.3.

---

### 👤 **User** — 2026-08-10 21:25:55

from **future** import annotations

from pathlib import Path

import numpy as np

from .image import image\_files
from .scene\_analyzer import SceneAnalyzer

class SceneRecognizer:
"""
Scene Fingerprint v3.3 compact recognizer.

```
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
```

---

### 🤖 **Assistant** — 2026-08-10 21:25:56

Да, вижу текущий `recognizer.py`. Он рабочий, но здесь есть важная проблема v3.3: **`embedder.embed_paths()` вызывается один раз, а затем `SceneAnalyzer.compare()` заново считает DINO для каждой пары `query × fingerprint`**. При 9 изображениях и 5 fingerprint это 45 повторных DINO-прогонов.

Для v3.3.1 сначала исправим архитектуру, а затем уже будем калибровать confidence. **Размер fingerprint не увеличиваем.**

Нужны ещё текущие версии:

- `app/core/scene_analyzer.py`
- `app/core/fingerprint.py`
- `app/cli.py`

Пришли их целиком, как сделал с `recognizer.py`. После этого я дам **готовые 4 файла v3.3.1**, а не куски кода, с:

- одним DINO pass на query;
- переиспользованием global embedding;
- compact descriptors без patch tokens;
- `score`;
- `second_score`;
- `margin`;
- `confidence`;
- `status`;
- нормальным `--json`;
- строгой совместимостью с `3.3`;
- без увеличения размера fingerprint;
- обратной совместимостью CLI-команд `create`, `analyze`, `recognize`.

И после замены файлов пойдём по контрольной последовательности:

```bash
uv run python -m py_compile \
app/core/scene_analyzer.py \
app/core/recognizer.py \
app/core/fingerprint.py \
app/cli.py
```

затем пересоздадим `78_v33–82_v33` и сравним результаты `001–009` с текущей базовой точкой.

---

### 👤 **User** — 2026-08-12 22:17:06

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

        analyzer = SceneAnalyzer(
            embedder,
            manager,
        )

        for result in analyzer.analyze(
            folder,
            args.fingerprint,
        ):
            print_analyze_result(
                result["file"],
                result,
            )

        return 0

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    if args.command == "recognize":

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

        recognizer = SceneRecognizer(
            settings,
            embedder,
            manager,
        )

        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
            )
        )

        if args.json:
            print(
                json.dumps(
                    results,
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for result in results:
                print_recognition_result(
                    result
                )

        return 0

    parser.print_help()

    return 1

if __name__ == "__main__":
    sys.exit(main())

[Attachment: Pasted text(9).txt]

[Attachment: Pasted text (2).txt]

---

### 🤖 **Assistant** — 2026-08-12 22:17:07

Да. Теперь у нас уже **реально рабочая база v3.3 compact**: `recognizer.py`, `cli.py` и `fingerprint.py` согласованы по версии `3.3`.

По текущему результату я бы **не менял архитектуру вслепую**. Следующий шаг — проверить/довести `scene_analyzer.py`, потому что именно он определяет итоговый `FINAL` score.

И важный момент: твой текущий `recognizer.py` делает лишнюю работу — он один раз считает `embed_paths()`, а затем `SceneAnalyzer.compare()` фактически снова работает с изображением. Это можно оптимизировать в следующем шаге.

### Что уже подтверждено

Сейчас v3.3:

- DINOv2 ViT-B/14 → `768`
- patch tokens полностью отключены
- `global` — 70%
- `environment` — 20%
- `color` — 7%
- `spatial` — 3%
- 16 representative images
- FAISS IndexFlatIP
- `margin` используется для определения уверенности
- старые `v3.2` fingerprints корректно отбрасываются
- `78_v33 ... 82_v33` успешно загружаются
- распознавание работает

И результат уже очень хороший:

| Query | Match | Score | Margin | Решение |
|---|---|---:|---:|---|
| 001 | 78_v33 | .9476 | .0956 | HIGH |
| 002 | 78_v33 | .9477 | .0899 | HIGH |
| 003 | 78_v33 | .9518 | .0813 | HIGH |
| 004 | 78_v33 | .9417 | .0760 | HIGH |
| 005 | 78_v33 | .9472 | .0898 | HIGH |
| 006 | 80_v33 | .9666 | .1449 | HIGH |
| 007 | 80_v33 | .9678 | .1334 | HIGH |
| 008 | 79_v33 | .8843 | .0008 | **AMBIGUOUS** |
| 009 | 79_v33 | .8871 | .0010 | **AMBIGUOUS** |

То есть **система уже правильно понимает главное различие**: 001–007 уверенные, а 008–009 похожи сразу на несколько сцен.

### Но сейчас надо сделать v3.3 правильно

Следующим сообщением я предлагаю сделать именно:

**`scene_analyzer.py v3.3 compact`**

и после этого провести контрольный тест:

```bash
uv run python -m py_compile \
app/core/scene_analyzer.py \
app/core/recognizer.py \
app/core/fingerprint.py \
app/cli.py
```

затем:

```bash
uv run scene-fingerprint recognize \
data/input/new \
--top-k 5 \
--threshold 0.65
```

После этого уже сравним **v3.2 → v3.3**, а не будем просто переписывать код.

Если хочешь идти дальше прямо сейчас — **присылай текущий `scene_analyzer.py` целиком**, и я дам тебе готовую финальную версию `v3.3 compact`, совместимую именно с тем `fingerprint.py`, который ты сейчас показал.

---

### 👤 **User** — 2026-08-12 22:22:44

у меня есть еще 83,84,85 для эксмериментов  . scene analyzer у меня такой. если с ним что то не так ищи рабочую выше в чате

[Attachment: Pasted text(10).txt]

---


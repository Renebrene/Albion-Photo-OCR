## СЕССИЯ: LORA

**Создано:** 2026-08-07 22:33:24
**Обновлено:** 2026-08-19 17:08:04
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c)

---

### 🤖 **Assistant** — 2026-08-08 18:16:52

Да. Ниже готовый `upgrade_v31.sh`. Он **не удаляет старую версию**, перед заменой делает backup и добавляет отдельный формат `v3.1`.

Создай файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
nano upgrade_v31.sh
```

и вставь туда:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="backup_v31_${STAMP}"

echo "=========================================="
echo " Scene Fingerprint v3.1 upgrade"
echo "=========================================="
echo
echo "Project: $PROJECT"
echo "Backup : $BACKUP"
echo

mkdir -p "$BACKUP/app/core"

echo "[1/7] Backing up current core..."

for f in \
    app/cli.py \
    app/core/embedder.py \
    app/core/fingerprint.py \
    app/core/recognizer.py \
    app/core/scene_analyzer.py
do
    if [ -f "$f" ]; then
        cp "$f" "$BACKUP/$f"
    fi
done

echo "[2/7] Writing v3.1 embedder..."

cat > app/core/embedder.py <<'PY'
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

class SceneEmbedder:
    """
    DINOv2 based scene embedding.

    v3.1 produces:
      - global embedding
      - patch tokens
      - environment embedding
      - color descriptor

    Environment deliberately uses spatial crops so the central
    construction does not completely dominate the fingerprint.
    """

    def __init__(self, settings):
        self.settings = settings

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[SceneEmbedder] device={self.device}")

        if self.device == "cuda":
            gpu = torch.cuda.get_device_name(0)
            vram = (
                torch.cuda.get_device_properties(0).total_memory
                / 1024**3
            )

            print(f"[SceneEmbedder] GPU={gpu}")
            print(f"[SceneEmbedder] VRAM={vram:.1f} GB")

        print("[SceneEmbedder] Loading DINOv2...")

        self.model = torch.hub.load(
            "facebookresearch/dinov2",
            "dinov2_vitb14",
        )

        self.model.eval()
        self.model.to(self.device)

        self.dimension = 768
        self.patch_grid = 16
        self.patch_count = self.patch_grid * self.patch_grid

        self.transform = transforms.Compose(
            [
                transforms.Resize(
                    (224, 224),
                    interpolation=transforms.InterpolationMode.BICUBIC,
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406),
                    std=(0.229, 0.224, 0.225),
                ),
            ]
        )

        print(f"[SceneEmbedder] embedding dimension={self.dimension}")
        print(
            f"[SceneEmbedder] patch grid="
            f"{self.patch_grid}x{self.patch_grid} "
            f"({self.patch_count} tokens)"
        )
        print("[SceneEmbedder] Ready.")

    def _image_tensor(self, image: Image.Image) -> torch.Tensor:
        return self.transform(image.convert("RGB")).unsqueeze(0)

    @torch.inference_mode()
    def _forward(self, image: Image.Image):
        tensor = self._image_tensor(image).to(self.device)

        features = self.model.forward_features(tensor)

        cls = features["x_norm_clstoken"]
        patches = features["x_norm_patchtokens"]

        cls = torch.nn.functional.normalize(cls, dim=1)
        patches = torch.nn.functional.normalize(patches, dim=2)

        return (
            cls[0].detach().cpu().numpy().astype(np.float32),
            patches[0].detach().cpu().numpy().astype(np.float32),
        )

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        a = a.astype(np.float32)
        b = b.astype(np.float32)

        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)

        if na == 0 or nb == 0:
            return 0.0

        return float(np.dot(a, b) / (na * nb))

    def _environment_crops(self, image: Image.Image):
        """
        Four spatial regions.

        The center is intentionally smaller in the environment descriptor.
        """

        w, h = image.size

        crops = {
            "top": image.crop(
                (0, 0, w, int(h * 0.50))
            ),

            "middle": image.crop(
                (0, int(h * 0.25), w, int(h * 0.78))
            ),

            "bottom": image.crop(
                (0, int(h * 0.55), w, h)
            ),

            "full": image,
        }

        return crops

    def _color_descriptor(self, image: Image.Image) -> np.ndarray:
        """
        Compact RGB/HSV-like spatial color descriptor.

        4x4 spatial cells × RGB mean/std.
        """

        img = np.asarray(
            image.convert("RGB").resize((128, 128)),
            dtype=np.float32,
        ) / 255.0

        features = []

        for gy in range(4):
            for gx in range(4):
                y0 = gy * 32
                y1 = (gy + 1) * 32
                x0 = gx * 32
                x1 = (gx + 1) * 32

                cell = img[y0:y1, x0:x1]

                mean = cell.mean(axis=(0, 1))
                std = cell.std(axis=(0, 1))

                features.extend(mean.tolist())
                features.extend(std.tolist())

        vec = np.asarray(features, dtype=np.float32)

        norm = np.linalg.norm(vec)

        if norm > 0:
            vec /= norm

        return vec

    def embed_image(self, path: str | Path):
        path = Path(path)

        with Image.open(path) as im:
            image = im.convert("RGB")

            global_vec, patches = self._forward(image)

            # Environment is built from spatial crops.
            env_vectors = []

            crops = self._environment_crops(image)

            for name in ("top", "middle", "bottom", "full"):
                env_cls, _ = self._forward(crops[name])
                env_vectors.append(env_cls)

            # Weight:
            # top      30%
            # middle   20%
            # bottom   30%
            # full     20%
            environment = (
                0.30 * env_vectors[0]
                + 0.20 * env_vectors[1]
                + 0.30 * env_vectors[2]
                + 0.20 * env_vectors[3]
            )

            norm = np.linalg.norm(environment)

            if norm > 0:
                environment /= norm

            color = self._color_descriptor(image)

            return {
                "global": global_vec,
                "patches": patches,
                "environment": environment.astype(np.float32),
                "color": color.astype(np.float32),
            }

    def embed_paths(
        self,
        paths: Iterable[str | Path],
        return_full: bool = True,
    ):
        paths = [Path(p) for p in paths]

        globals_ = []
        patches_ = []
        environments_ = []
        colors_ = []

        for index, path in enumerate(paths, 1):
            print(
                f"\r[SceneEmbedder] {index}/{len(paths)} "
                f"{path.name}",
                end="",
                flush=True,
            )

            result = self.embed_image(path)

            globals_.append(result["global"])
            patches_.append(result["patches"])
            environments_.append(result["environment"])
            colors_.append(result["color"])

        if paths:
            print()

        result = {
            "global": np.stack(globals_).astype(np.float32),
            "patches": np.stack(patches_).astype(np.float32),
            "environment": np.stack(environments_).astype(np.float32),
            "color": np.stack(colors_).astype(np.float32),
            "paths": [str(p) for p in paths],
        }

        if return_full:
            return result

        return result["global"]
PY

echo "[3/7] Writing v3.1 fingerprint manager..."

cat > app/core/fingerprint.py <<'PY'
from __future__ import annotations

import json
import shutil
from pathlib import Path

import faiss
import numpy as np

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

class FingerprintManager:

    def __init__(self, settings, embedder):
        self.settings = settings
        self.embedder = embedder

        self.root = Path(settings.fingerprints_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, fingerprint_id: str) -> Path:
        return self.root / fingerprint_id

    def _files(self, fingerprint_id: str):
        out = self._dir(fingerprint_id)

        return {
            "global": out / "global_embeddings.npy",
            "patch": out / "patch_embeddings.npy",
            "environment": out / "environment_embeddings.npy",
            "color": out / "color_features.npy",
            "centroid": out / "centroid.npy",
            "representatives": out / "representatives.npy",
            "environment_representatives": out
            / "environment_representatives.npy",
            "faiss": out / "faiss.index",
            "metadata": out / "metadata.json",
        }

    def _image_paths(self, folder):
        folder = Path(folder)

        return sorted(
            p
            for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        )

    def _normalize_rows(self, x):
        x = np.asarray(x, dtype=np.float32)

        norms = np.linalg.norm(x, axis=1, keepdims=True)
        norms[norms == 0] = 1

        return x / norms

    def _representatives(self, vectors, count=16):
        """
        Select diverse representative vectors using a greedy farthest
        point strategy.
        """

        vectors = self._normalize_rows(vectors)

        n = len(vectors)

        if n <= count:
            return vectors.copy()

        centroid = vectors.mean(axis=0)
        centroid /= max(np.linalg.norm(centroid), 1e-12)

        selected = [int(np.argmax(vectors @ centroid))]
        distances = 1.0 - vectors @ vectors[selected[0]]

        for _ in range(1, count):
            idx = int(np.argmax(distances))

            if idx in selected:
                break

            selected.append(idx)

            d = 1.0 - vectors @ vectors[idx]
            distances = np.minimum(distances, d)

        return vectors[selected]

    def create(self, fingerprint_id: str, folder):
        folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        paths = self._image_paths(folder)

        if not paths:
            raise ValueError(
                f"No images found in {folder}"
            )

        out = self._dir(fingerprint_id)

        if out.exists():
            print(
                f"[Fingerprint] Replacing existing fingerprint "
                f"'{fingerprint_id}'"
            )
            shutil.rmtree(out)

        out.mkdir(parents=True)

        print(
            f"[Fingerprint v3.1] Creating "
            f"'{fingerprint_id}' from {len(paths)} images"
        )

        data = self.embedder.embed_paths(paths)

        global_vectors = self._normalize_rows(data["global"])
        patch_vectors = self._normalize_rows(
            data["patch"].reshape(-1, data["patch"].shape[-1])
            if "patch" in data
            else data["patches"].reshape(
                -1,
                data["patches"].shape[-1],
            )
        )

        environment_vectors = self._normalize_rows(
            data["environment"]
        )

        color_vectors = self._normalize_rows(
            data["color"]
        )

        np.save(
            out / "global_embeddings.npy",
            global_vectors,
        )

        np.save(
            out / "patch_embeddings.npy",
            data["patches"].astype(np.float32),
        )

        np.save(
            out / "environment_embeddings.npy",
            environment_vectors,
        )

        np.save(
            out / "color_features.npy",
            color_vectors,
        )

        centroid = global_vectors.mean(axis=0)
        centroid /= max(np.linalg.norm(centroid), 1e-12)

        np.save(
            out / "centroid.npy",
            centroid.astype(np.float32),
        )

        representatives = self._representatives(
            global_vectors,
            count=min(16, len(global_vectors)),
        )

        environment_representatives = self._representatives(
            environment_vectors,
            count=min(16, len(environment_vectors)),
        )

        np.save(
            out / "representatives.npy",
            representatives.astype(np.float32),
        )

        np.save(
            out / "environment_representatives.npy",
            environment_representatives.astype(np.float32),
        )

        index = faiss.IndexFlatIP(
            global_vectors.shape[1]
        )

        index.add(global_vectors.astype(np.float32))

        faiss.write_index(
            index,
            str(out / "faiss.index"),
        )

        metadata = {
            "id": fingerprint_id,
            "version": "3.1",
            "images": len(paths),
            "dimension": int(global_vectors.shape[1]),
            "patch_grid": [16, 16],
            "patch_tokens_per_image": 256,
            "representatives": len(representatives),
            "environment_representatives": len(
                environment_representatives
            ),
            "image_names": [
                p.name for p in paths
            ],
            "weights": {
                "global": 0.15,
                "patch": 0.20,
                "environment": 0.50,
                "color": 0.15,
            },
        }

        (out / "metadata.json").write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return (
            f"Fingerprint '{fingerprint_id}' created: "
            f"{len(paths)} images, "
            f"environment vectors={len(environment_vectors)}, "
            f"patch tokens={len(data['patches']) * 256}"
        )

    def load(self, fingerprint_id):
        files = self._files(fingerprint_id)

        required = [
            "global",
            "patch",
            "environment",
            "color",
            "centroid",
            "representatives",
            "environment_representatives",
            "faiss",
            "metadata",
        ]

        missing = [
            name
            for name in required
            if not files[name].exists()
        ]

        if missing:
            raise FileNotFoundError(
                f"Fingerprint '{fingerprint_id}' is incomplete. "
                f"Missing: {', '.join(missing)}"
            )

        return {
            "global": np.load(files["global"]),
            "patch": np.load(files["patch"]),
            "environment": np.load(
                files["environment"]
            ),
            "color": np.load(files["color"]),
            "centroid": np.load(files["centroid"]),
            "representatives": np.load(
                files["representatives"]
            ),
            "environment_representatives": np.load(
                files["environment_representatives"]
            ),
            "index": faiss.read_index(
                str(files["faiss"])
            ),
            "metadata": json.loads(
                files["metadata"].read_text(
                    encoding="utf-8"
                )
            ),
        }

    def list_fingerprints(self):
        result = []

        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir():
                continue

            metadata = directory / "metadata.json"

            if not metadata.exists():
                continue

            try:
                data = json.loads(
                    metadata.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                continue

            result.append(data)

        return result
PY

echo "[4/7] Writing v3.1 recognizer..."

cat > app/core/recognizer.py <<'PY'
from __future__ import annotations

from pathlib import Path

import numpy as np

class SceneRecognizer:

    GLOBAL_WEIGHT = 0.15
    PATCH_WEIGHT = 0.20
    ENV_WEIGHT = 0.50
    COLOR_WEIGHT = 0.15

    def __init__(self, settings, embedder):
        self.settings = settings
        self.embedder = embedder

        from app.core.fingerprint import FingerprintManager

        self.manager = FingerprintManager(
            settings,
            embedder,
        )

    @staticmethod
    def _cosine(a, b):
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)

        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)

        if na == 0 or nb == 0:
            return 0.0

        return float(
            np.dot(a, b) / (na * nb)
        )

    def _patch_score(self, query_patches, ref_patches):
        """
        Compare query patches against the reference patch cloud.

        Instead of requiring exact spatial alignment, each query patch
        searches for its closest reference patch.
        """

        q = query_patches.astype(np.float32)
        r = ref_patches.astype(np.float32)

        q /= np.maximum(
            np.linalg.norm(q, axis=1, keepdims=True),
            1e-12,
        )

        r /= np.maximum(
            np.linalg.norm(r, axis=1, keepdims=True),
            1e-12,
        )

        similarity = q @ r.T

        best = similarity.max(axis=1)

        # Trim the weakest 25% to reduce influence of sky/noise.
        best = np.sort(best)

        keep = best[int(len(best) * 0.25):]

        return float(keep.mean())

    def _environment_score(
        self,
        query_environment,
        reference_environment,
        representatives,
    ):
        direct = self._cosine(
            query_environment,
            reference_environment,
        )

        if len(representatives):
            rep_scores = [
                self._cosine(
                    query_environment,
                    rep,
                )
                for rep in representatives
            ]

            representative_score = max(
                rep_scores
            )
        else:
            representative_score = direct

        # Favor the representative similarity slightly.
        return (
            0.40 * direct
            + 0.60 * representative_score
        )

    def _color_score(self, query_color, reference_color):
        return self._cosine(
            query_color,
            reference_color,
        )

    def _score(self, query, reference):
        global_score = self._cosine(
            query["global"],
            reference["global"].mean(axis=0),
        )

        patch_score = self._patch_score(
            query["patches"],
            reference["patch"],
        )

        environment_score = self._environment_score(
            query["environment"],
            reference["environment"].mean(axis=0),
            reference["environment_representatives"],
        )

        color_score = self._color_score(
            query["color"],
            reference["color"].mean(axis=0),
        )

        final = (
            self.GLOBAL_WEIGHT * global_score
            + self.PATCH_WEIGHT * patch_score
            + self.ENV_WEIGHT * environment_score
            + self.COLOR_WEIGHT * color_score
        )

        return {
            "score": float(final),
            "global": float(global_score),
            "patch": float(patch_score),
            "environment": float(environment_score),
            "color": float(color_score),
        }

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        fingerprints = []

        for fp in self.manager.list_fingerprints():
            try:
                data = self.manager.load(fp["id"])

                # v3.1 only.
                if data["metadata"].get("version") != "3.1":
                    continue

                fingerprints.append(
                    (fp["id"], data)
                )

            except FileNotFoundError:
                continue

        if not fingerprints:
            raise RuntimeError(
                "No v3.1 fingerprints found."
            )

        paths = sorted(
            p
            for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower()
            in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
                ".tif",
                ".tiff",
            }
        )

        for path in paths:
            query = self.embedder.embed_image(path)

            candidates = []

            for fingerprint_id, reference in fingerprints:
                result = self._score(
                    query,
                    reference,
                )

                candidates.append(
                    {
                        "id": fingerprint_id,
                        **result,
                    }
                )

            candidates.sort(
                key=lambda x: x["score"],
                reverse=True,
            )

            candidates = candidates[:top_k]

            best = candidates[0]

            yield {
                "file": str(path),
                "best_id": (
                    best["id"]
                    if best["score"] >= threshold
                    else None
                ),
                "score": best["score"],
                "candidates": candidates,
            }

    def analyze(
        self,
        folder,
        fingerprint_id,
    ):
        folder = Path(folder)

        reference = self.manager.load(
            fingerprint_id
        )

        if reference["metadata"].get("version") != "3.1":
            raise ValueError(
                f"Fingerprint '{fingerprint_id}' "
                f"is not v3.1"
            )

        paths = sorted(
            p
            for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower()
            in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
                ".tif",
                ".tiff",
            }
        )

        for path in paths:
            query = self.embedder.embed_image(path)

            scores = self._score(
                query,
                reference,
            )

            global_score = scores["global"]
            patch_score = scores["patch"]
            environment_score = scores[
                "environment"
            ]
            color_score = scores["color"]

            # Find closest source image using global vectors.
            global_scores = [
                self._cosine(
                    query["global"],
                    vector,
                )
                for vector in reference["global"]
            ]

            best_index = int(
                np.argmax(global_scores)
            )

            image_names = reference[
                "metadata"
            ].get("image_names", [])

            best_image = (
                image_names[best_index]
                if best_index < len(image_names)
                else f"image_{best_index}"
            )

            yield {
                "file": str(path),
                "global_score": global_score,
                "patch_score": patch_score,
                "environment_score": environment_score,
                "color_score": color_score,
                "final_score": scores["score"],
                "best_image": best_image,
            }
PY

echo "[5/7] Writing v3.1 scene analyzer..."

cat > app/core/scene_analyzer.py <<'PY'
from __future__ import annotations

from app.core.recognizer import SceneRecognizer

class SceneAnalyzer:

    def __init__(self, settings, embedder):
        self.recognizer = SceneRecognizer(
            settings,
            embedder,
        )

    def analyze(
        self,
        folder,
        fingerprint_id,
    ):
        yield from self.recognizer.analyze(
            folder,
            fingerprint_id,
        )
PY

echo "[6/7] Writing CLI..."

cat > app/cli.py <<'PY'
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer
from app.core.scene_analyzer import SceneAnalyzer

def main():
    parser = argparse.ArgumentParser(
        description="Scene fingerprinting and recognition"
    )

    sub = parser.add_subparsers(
        dest="cmd",
        required=True,
    )

    create = sub.add_parser(
        "create",
        help="Create a v3.1 fingerprint from an image folder",
    )

    create.add_argument(
        "id",
        help="Fingerprint ID",
    )

    create.add_argument(
        "folder",
        help="Folder containing reference images",
    )

    recognize = sub.add_parser(
        "recognize",
        help="Recognize images against v3.1 fingerprints",
    )

    recognize.add_argument(
        "folder",
        help="Folder containing query images",
    )

    recognize.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    recognize.add_argument(
        "--threshold",
        type=float,
        default=0.65,
    )

    analyze = sub.add_parser(
        "analyze",
        help="Analyze scene similarity components",
    )

    analyze.add_argument(
        "folder",
        help="Folder containing query images",
    )

    analyze.add_argument(
        "--fingerprint",
        required=True,
        help="v3.1 fingerprint ID",
    )

    args = parser.parse_args()

    embedder = SceneEmbedder(settings)

    if args.cmd == "create":
        manager = FingerprintManager(
            settings,
            embedder,
        )

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        print(
            manager.create(
                args.id,
                folder,
            )
        )

        return

    if args.cmd == "recognize":
        recognizer = SceneRecognizer(
            settings,
            embedder,
        )

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        for result in recognizer.recognize_folder(
            folder,
            args.top_k,
            args.threshold,
        ):
            print(result)

        return

    if args.cmd == "analyze":
        analyzer = SceneAnalyzer(
            settings,
            embedder,
        )

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        for result in analyzer.analyze(
            folder,
            args.fingerprint,
        ):
            print()
            print(
                f"## {Path(result['file']).name}"
            )
            print()
            print(
                f"GLOBAL        "
                f"{result['global_score']:.4f}"
            )
            print(
                f"PATCH         "
                f"{result['patch_score']:.4f}"
            )
            print(
                f"ENVIRONMENT   "
                f"{result['environment_score']:.4f}"
            )
            print(
                f"COLOR         "
                f"{result['color_score']:.4f}"
            )
            print(
                f"FINAL         "
                f"{result['final_score']:.4f}"
            )
            print(
                f"BEST MATCH    "
                f"{result['best_image']}"
            )

        print()
        print("=" * 60)

if __name__ == "__main__":
    main()
PY

echo "[7/7] Syntax check..."

uv run python -m py_compile \
    app/cli.py \
    app/core/embedder.py \
    app/core/fingerprint.py \
    app/core/recognizer.py \
    app/core/scene_analyzer.py

echo
echo "=========================================="
echo " v3.1 INSTALLED"
echo "=========================================="
echo
echo "Backup:"
echo "  $BACKUP"
echo
echo "IMPORTANT:"
echo "  Old fingerprints were NOT modified."
echo
echo "Create v3.1 fingerprint:"
echo
echo "  uv run scene-fingerprint create 78_v31 data/input/78"
echo
echo "Analyze:"
echo
echo "  uv run scene-fingerprint analyze data/input/new --fingerprint 78_v31"
echo
echo "Recognize:"
echo
echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65"
echo
echo "Later:"
echo
echo "  uv run scene-fingerprint create 79_v31 data/input/79"
echo "  uv run scene-fingerprint create 80_v31 data/input/80"
echo "  uv run scene-fingerprint create 81_v31 data/input/81"
echo
echo "=========================================="
```

Затем:

```bash
chmod +x upgrade_v31.sh
./upgrade_v31.sh
```

### После установки

**Не удаляй пока `78`, `78_patch`, `78_v3`.**

Создай новый слепок:

```bash
uv run scene-fingerprint create 78_v31 data/input/78
```

Проверь:

```bash
ls -lah data/fingerprints/78_v31/
```

Там должны появиться:

```text
global_embeddings.npy
patch_embeddings.npy
environment_embeddings.npy
environment_representatives.npy
color_features.npy
centroid.npy
representatives.npy
faiss.index
metadata.json
```

Потом:

```bash
uv run scene-fingerprint analyze data/input/new --fingerprint 78_v31
```

И затем:

```bash
uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65
```

**Важный момент:** `79`, `80`, `81` лучше создавать именно как `79_v31`, `80_v31`, `81_v31`. Тогда у нас будет чистый эксперимент и можно будет сравнить старые и новые алгоритмы, не смешивая форматы.

---

### 👤 **User** — 2026-08-08 18:18:49

[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch grid=16x16 (256 tokens)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/scene-fingerprint", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/cli.py", line 137, in main
    for result in analyzer.analyze(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/scene_analyzer.py", line 19, in analyze
    yield from self.recognizer.analyze(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/recognizer.py", line 273, in analyze
    scores = self._score(
             ^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/recognizer.py", line 117, in _score
    patch_score = self._patch_score(
                  ^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/recognizer.py", line 62, in _patch_score
    similarity = q @ r.T
                 ~~^~~~~
ValueError: matmul: Input operand 1 has a mismatch in its core dimension 0, with gufunc signature (n?,k),(k,m?)->(n?,m?) (size 256 is different from 768)
(base) alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-08 18:18:52

Да. Ошибка уже очень конкретная: **v3.1 записала `patch_representatives` в несовместимом формате**.

Сейчас `_patch_score()` ожидает примерно:

- query patch tokens: `(256, 768)`
- representatives: `(N, 256, 768)`

а один из массивов фактически имеет размерность, где `256` оказался вместо `768`. Поэтому:

```text
ValueError: ... (size 256 is different from 768)
```

Это **не проблема DINOv2 и не GPU**. Это ошибка формата fingerprint v3.1.

### Сначала ничего не удаляй

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import numpy as np
from pathlib import Path

root = Path("data/fingerprints")

for fp in sorted(root.iterdir()):
    if not fp.is_dir():
        continue

    print(f"\n=== {fp.name} ===")

    for name in [
        "embeddings.npy",
        "centroid.npy",
        "representatives.npy",
        "patch_embeddings.npy",
        "patch_centroid.npy",
        "patch_representatives.npy",
    ]:
        p = fp / name
        if p.exists():
            a = np.load(p, mmap_mode="r")
            print(f"{name:25} shape={str(a.shape):25} dtype={a.dtype}")
PY
```

**Пришли мне весь вывод.**

Особенно интересуют:

```text
78_v3
78_v31
```

и размеры:

```text
patch_embeddings.npy
patch_representatives.npy
```

---

### Что, скорее всего, произошло

В v3.1 мы хотим хранить не просто один усреднённый patch-вектор, а **пространственную карту окружения**:

```text
16 × 16 patches
       ↓
256 × 768
```

То есть для каждого снимка:

```text
image
  ↓
DINOv2
  ↓
256 patch tokens
  ↓
256 × 768
```

А fingerprint должен содержать набор таких карт:

```text
82 images
   ↓
82 × 256 × 768
```

При этом для сравнения нужно делать не обычный:

```python
q @ r.T
```

а сравнение patch-карт, например:

```text
query:  256 × 768
reference: 256 × 768

        ↓

256 × 256 similarity matrix

        ↓

пространственно устойчивый score
```

И именно здесь я бы сейчас **не стал просто чинить одну строку**. Лучше сделать v3.1 правильно, чтобы:

1. `78_v3` не ломался;
2. `79`, `80`, `81` можно было создавать тем же CLI;
3. старые `78`, `78_patch`, `78_v3` продолжали работать;
4. fingerprint был независим от интерфейса;
5. потом поверх этого спокойно сделать NiceGUI;
6. можно было менять алгоритм распознавания, **не пересоздавая фотографии и не ломая базу**.

### И ещё важный момент

Твои результаты v3 уже показывают, что направление правильное:

```text
001 environment = 0.9599
002 environment = 0.9597
003 environment = 0.9696
004 environment = 0.9693
005 environment = 0.9656

006 environment = 0.9649
007 environment = 0.9555
008 environment = 0.9603
009 environment = 0.9651
```

То есть **окружение действительно очень хорошо отделяется от самой конструкции**.

И особенно интересно:

```text
006:
global       0.7598
patch        0.6655
environment  0.9649
```

Это именно тот случай, ради которого мы всё это делаем: **конструкция похожа плохо, а окружающая сцена говорит, что это тот же объект/место**.

Поэтому сейчас лучше исправить именно механизм хранения/сравнения patch-карт, а не возвращаться к обычному global embedding.

**Пришли вывод команды выше — после него дам точный готовый `upgrade_v31_fix.sh`, который можно будет просто запустить.**

---

### 👤 **User** — 2026-08-08 18:19:22

(base) alexice\@NEURO:\~/Desktop$ cd \~/projects/scene\_fingerprint\_mvp\_v02

uv run python - <<'PY'
import numpy as np
from pathlib import Path

root = Path("data/fingerprints")

for fp in sorted(root.iterdir()):
if not fp.is\_dir():
continue

```
print(f"\n=== {fp.name} ===")

for name in [
    "embeddings.npy",
    "centroid.npy",
    "representatives.npy",
    "patch_embeddings.npy",
    "patch_centroid.npy",
    "patch_representatives.npy",
]:
    p = fp / name
    if p.exists():
```

PY          print(f"{name:25} shape={str(a.shape):25} dtype={a.dtype}")

\=== 78 ===
embeddings.npy            shape=(82, 768)                 dtype=float32
centroid.npy              shape=(1, 768)                  dtype=float32
representatives.npy       shape=(16, 768)                 dtype=float32

\=== 78\_patch ===
embeddings.npy            shape=(82, 768)                 dtype=float32
centroid.npy              shape=(1, 768)                  dtype=float32
representatives.npy       shape=(16, 768)                 dtype=float32
patch\_embeddings.npy      shape=(82, 256, 768)            dtype=float32
patch\_centroid.npy        shape=(256, 768)                dtype=float32
patch\_representatives.npy shape=(16, 256, 768)            dtype=float32

\=== 78\_v3 ===
embeddings.npy            shape=(82, 768)                 dtype=float32
centroid.npy              shape=(1, 768)                  dtype=float32
representatives.npy       shape=(16, 768)                 dtype=float32
patch\_embeddings.npy      shape=(82, 256, 768)            dtype=float32
patch\_centroid.npy        shape=(256, 768)                dtype=float32
patch\_representatives.npy shape=(16, 256, 768)            dtype=float32

\=== 78\_v31 ===
centroid.npy              shape=(768,)                    dtype=float32
representatives.npy       shape=(16, 768)                 dtype=float32
patch\_embeddings.npy      shape=(82, 256, 768)            dtype=float32
(base) alexice\@NEURO:\~/projects/scene\_fingerprint\_mvp\_v02$

---

### 🤖 **Assistant** — 2026-08-08 18:19:24

Отлично. Теперь причина **точно установлена**.

`78_patch` и `78_v3` корректные:

```text
patch_embeddings       (82, 256, 768)
patch_centroid         (256, 768)
patch_representatives  (16, 256, 768)
```

А вот `78_v31` **неполный**:

```text
centroid.npy           (768,)
representatives.npy    (16, 768)
patch_embeddings       (82, 256, 768)

НЕТ:
patch_centroid.npy
patch_representatives.npy
```

Именно поэтому v3.1 падает при попытке сравнить patch tokens.

Но я бы сейчас не делал «быстрый фикс» `78_v31`. Лучше сделать нормальную **v3.1**, которая:

- исправляет формат fingerprint;
- автоматически проверяет целостность;
- не использует `78_v31`, если он недописан;
- сохраняет старые fingerprint;
- создаёт новый `78_v31` заново;
- корректно считает `environment`;
- совместима с текущими `create / recognize / analyze`.

### 1. Удаляем только битый `78_v31`

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/fingerprints/78_v31
```

`78`, `78_patch`, `78_v3` **не трогаем**.

### 2. Сначала проверим, что v3 действительно работает

```bash
uv run scene-fingerprint analyze \
    data/input/new \
    --fingerprint 78_v3
```

Если `78_v3` выдаёт результаты — отлично.

### 3. А теперь я бы сделал v3.1 немного иначе

Важный момент: **не нужно хранить отдельный `patch_centroid` как единственный источник environment score**.

Для нашей задачи правильнее:

```text
                     PHOTO
                       │
              ┌────────┴────────┐
              │                 │
          GLOBAL             PATCH MAP
         1 × 768            256 × 768
              │                 │
              │          ┌──────┴──────┐
              │          │             │
              │       spatial       texture/
              │       layout        environment
              │          │             │
              └──────────┴─────────────┘
                         │
                    fingerprint
```

И главное — **environment должен быть отдельной характеристикой**, а не просто остатком от global similarity.

Для твоей задачи я предлагаю v3.1:

```text
GLOBAL       20%
PATCH        25%
ENVIRONMENT  55%
```

Но environment при этом рассчитывать не одним DINO score, а из нескольких признаков:

```text
environment =
    DINO patch similarity
  + color/layout similarity
  + spatial similarity
```

Причём **центральную область изображения можно ослабить**, потому что там находится сама конструкция, которая у всех объектов почти одинаковая.

То есть условно:

```text
┌─────────────────────────────┐
│  ENVIRONMENT      ENVIRONMENT│
│                             │
│        ┌──────────┐         │
│        │          │         │
│        │ ОБЪЕКТ   │         │
│        │          │         │
│        └──────────┘         │
│                             │
│  ENVIRONMENT      ENVIRONMENT│
└─────────────────────────────┘
```

Это уже будет намного ближе к тому, что тебе реально нужно.

---

## Но прямо сейчас есть простой тест

После удаления битого fingerprint выполни:

```bash
uv run scene-fingerprint analyze \
    data/input/new \
    --fingerprint 78_v3
```

А затем:

```bash
uv run scene-fingerprint recognize \
    data/input/new \
    --top-k 5 \
    --threshold 0.65
```

**Не создавай пока 79/80/81.**

Я хочу сначала убедиться, что текущая v3 стабильно работает на `78_v3`. После этого дам тебе **готовый `upgrade_v31.sh` целиком**, который установит v3.1 атомарно и не оставит таких полуготовых fingerprint'ов.

И уже после него можно будет спокойно делать:

```bash
uv run scene-fingerprint create 79 data/input/79
uv run scene-fingerprint create 80 data/input/80
uv run scene-fingerprint create 81 data/input/81
```

Это будет хорошая контрольная выборка для проверки того, действительно ли **окружение различает 78/79/80/81**, а не просто узнаёт одну и ту же конструкцию.

---

### 👤 **User** — 2026-08-08 18:19:52

File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/scene-fingerprint", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/cli.py", line 137, in main
    for result in analyzer.analyze(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/scene_analyzer.py", line 19, in analyze
    yield from self.recognizer.analyze(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/recognizer.py", line 244, in analyze
    reference = self.manager.load(
                ^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/fingerprint.py", line 270, in load
    raise FileNotFoundError(
FileNotFoundError: Fingerprint '78_v3' is incomplete. Missing: global, color
(base) alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-08 18:19:53

Да. Теперь видно, что проблема уже **не в patch tokens**.

`78_v3` создан старой версией формата и содержит:

```text
global — есть
patch — есть
environment — есть
color — НЕТ
```

А текущий `FingerprintManager.load()` требует новый формат:

```text
global
color
patch
environment
```

То есть мы сейчас смешали **несколько поколений формата fingerprint**. Это моя ошибка в предыдущем шаге: я предложил проверять `78_v3` текущим loader'ом, хотя формат уже изменился.

### Я предлагаю сейчас прекратить латать старые версии

Сделаем **v3.1 с новым форматом и миграцией**, но при этом:

- `78` — оставить как есть;
- `78_patch` — оставить;
- `78_v3` — оставить;
- `78_v31` — удалить и создать заново;
- текущий код будет понимать старые fingerprint как legacy;
- новые fingerprint будут иметь единый формат;
- `load()` больше не будет падать из-за отсутствующего `color`;
- `create` будет писать fingerprint **атомарно**: сначала во временную директорию, затем rename;
- `recognize` сможет работать одновременно с `78`, `79`, `80`, `81`;
- `analyze` будет использовать именно новый environment score.

### Сейчас ничего больше не меняй

Сделай только:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/fingerprints/78_v31

ls -1 data/fingerprints
```

Должно остаться примерно:

```text
78
78_patch
78_v3
```

**И пока не создавай 79/80/81.**

Следующим сообщением я дам тебе **полный готовый `upgrade_v31.sh`**, который заменит нужные `fingerprint.py`, `recognizer.py`, `scene_analyzer.py` и `cli.py` согласованно, а не отдельными кусками.

После установки будет одна команда:

```bash
./upgrade_v31.sh
```

затем:

```bash
uv run scene-fingerprint create 78_v31 data/input/78
```

и уже после проверки:

```bash
uv run scene-fingerprint create 79 data/input/79
uv run scene-fingerprint create 80 data/input/80
uv run scene-fingerprint create 81 data/input/81
```

Это правильный момент, чтобы **зафиксировать формат базы**, прежде чем ты загрузишь 79–81.

---

### 👤 **User** — 2026-08-08 18:20:24

давай

---

### 🤖 **Assistant** — 2026-08-08 18:20:25

Делаем. Но я предлагаю сразу сделать **нормальную v3.1**, а не очередной патч поверх нескольких несовместимых форматов.

Важное изменение: `78_v31` будет создаваться атомарно и получит единый формат `global + color + patch + environment`. Старые `78`, `78_patch`, `78_v3` не трогаем.

Ниже — готовый скрипт. Он создаст резервную копию текущего `app/core`, заменит `fingerprint.py`, `recognizer.py`, `scene_analyzer.py` и `cli.py`, проверит синтаксис.

### 1. Создай скрипт

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano upgrade_v31.sh
```

Вставь **целиком**:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="backup_v31_${STAMP}"

echo "========================================"
echo " Scene Fingerprint v3.1 upgrade"
echo "========================================"
echo

echo "[1/5] Backup current core -> $BACKUP"

mkdir -p "$BACKUP/app/core"

for f in \
    app/core/fingerprint.py \
    app/core/recognizer.py \
    app/core/scene_analyzer.py \
    app/cli.py
do
    if [ -f "$f" ]; then
        cp "$f" "$BACKUP/$f"
    fi
done

echo "Backup created: $BACKUP"
echo

echo "[2/5] Writing fingerprint.py"

cat > app/core/fingerprint.py <<'PY'
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import faiss
import numpy as np

class FingerprintManager:
    """
    Fingerprint storage.

    v3.1 format:

        embeddings.npy
        centroid.npy
        representatives.npy
        faiss.index
        metadata.json

        patch_embeddings.npy
        patch_centroid.npy
        patch_representatives.npy

        color_embeddings.npy
        color_centroid.npy

        environment_embeddings.npy
        environment_centroid.npy

    Legacy fingerprints are still readable when possible.
    """

    def __init__(self, settings, embedder):
        self.settings = settings
        self.embedder = embedder

        self.root = Path(settings.fingerprints_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, fingerprint_id: str) -> Path:
        return self.root / fingerprint_id

    @staticmethod
    def _normalize_rows(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        norms = np.linalg.norm(x, axis=-1, keepdims=True)
        return x / np.maximum(norms, 1e-8)

    @staticmethod
    def _normalize_vector(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        norm = np.linalg.norm(x)
        return x / max(float(norm), 1e-8)

    def _image_files(self, folder) -> list[Path]:
        folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")

        exts = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".tif",
            ".tiff",
        }

        return sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in exts
        )

    def _color_descriptor(self, path: Path) -> np.ndarray:
        """
        Compact scene-color descriptor.

        Uses a low-resolution HSV histogram.
        This is deliberately independent from the DINO model.
        """

        from PIL import Image
        import cv2

        with Image.open(path) as im:
            rgb = np.asarray(im.convert("RGB").resize((128, 128)))

        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

        hist = cv2.calcHist(
            [hsv],
            [0, 1],
            None,
            [16, 8],
            [0, 180, 0, 256],
        )

        hist = hist.astype(np.float32).flatten()
        hist /= max(float(np.linalg.norm(hist)), 1e-8)

        return hist

    def _environment_descriptor(
        self,
        patch_tokens: np.ndarray,
        image_shape=None,
    ) -> np.ndarray:
        """
        Environment descriptor.

        We suppress the center of the image because the construction
        itself is intentionally not the main identification signal.

        DINOv2 ViT-B/14 gives 16x16 patch tokens for the current
        224x224 processing resolution.
        """

        x = np.asarray(patch_tokens, dtype=np.float32)

        if x.ndim != 2:
            raise ValueError(
                f"Expected patch tokens (N,D), got {x.shape}"
            )

        n, dim = x.shape

        side = int(round(n ** 0.5))

        if side * side != n:
            # Fallback: mean of all tokens.
            env = x.mean(axis=0)
            return self._normalize_vector(env)

        grid = x.reshape(side, side, dim)

        yy, xx = np.mgrid[0:side, 0:side]

        cx = (side - 1) / 2.0
        cy = (side - 1) / 2.0

        dx = (xx - cx) / max(cx, 1.0)
        dy = (yy - cy) / max(cy, 1.0)

        r2 = dx * dx + dy * dy

        # Keep peripheral environment.
        #
        # Center weight ~0.15
        # Outer area weight ~1.0
        weight = np.clip(0.15 + 0.85 * r2, 0.15, 1.0)

        weighted = grid * weight[..., None]

        env = weighted.sum(axis=(0, 1))
        env /= max(float(weight.sum()), 1e-8)

        return self._normalize_vector(env)

    def _build_representatives(
        self,
        embeddings: np.ndarray,
        count: int = 16,
    ) -> np.ndarray:

        x = self._normalize_rows(embeddings)

        if len(x) <= count:
            return x.copy()

        # Deterministic farthest-point sampling.
        selected = [0]

        similarities = x @ x[0]

        for _ in range(1, count):
            idx = int(np.argmin(similarities))
            selected.append(idx)

            sim = x @ x[idx]
            similarities = np.maximum(similarities, sim)

        return x[selected]

    def create(self, fingerprint_id: str, folder) -> dict:
        folder = Path(folder)
        images = self._image_files(folder)

        if not images:
            raise ValueError(f"No images found in {folder}")

        final_dir = self._path(fingerprint_id)

        if final_dir.exists():
            raise FileExistsError(
                f"Fingerprint '{fingerprint_id}' already exists. "
                f"Remove it first if you want to recreate it."
            )

        print(
            f"[Fingerprint] Creating '{fingerprint_id}' "
            f"from {len(images)} images"
        )

        # ---------------------------------------------------------
        # DINO global + patch tokens
        # ---------------------------------------------------------

        result = self.embedder.embed_paths(
            [str(p) for p in images],
            return_patches=True,
        )

        if isinstance(result, tuple):
            embeddings, patch_embeddings = result
        elif isinstance(result, dict):
            embeddings = result["embeddings"]
            patch_embeddings = result["patch_embeddings"]
        else:
            raise TypeError(
                "embed_paths(return_patches=True) must return "
                "(embeddings, patch_embeddings) or a dict"
            )

        embeddings = np.asarray(embeddings, dtype=np.float32)
        patch_embeddings = np.asarray(
            patch_embeddings,
            dtype=np.float32,
        )

        if embeddings.ndim != 2:
            raise ValueError(
                f"Global embeddings must be 2D, got {embeddings.shape}"
            )

        if patch_embeddings.ndim != 3:
            raise ValueError(
                "Patch embeddings must be 3D "
                f"(images, patches, dim), got {patch_embeddings.shape}"
            )

        if len(images) != len(embeddings):
            raise ValueError(
                f"Image count {len(images)} != embeddings "
                f"count {len(embeddings)}"
            )

        if patch_embeddings.shape[0] != len(images):
            raise ValueError(
                "Image count does not match patch embeddings"
            )

        embeddings = self._normalize_rows(embeddings)
        patch_embeddings = self._normalize_rows(patch_embeddings)

        # ---------------------------------------------------------
        # Global
        # ---------------------------------------------------------

        centroid = self._normalize_vector(
            embeddings.mean(axis=0)
        )[None, :]

        representatives = self._build_representatives(
            embeddings,
            count=min(16, len(embeddings)),
        )

        # ---------------------------------------------------------
        # Patch
        # ---------------------------------------------------------

        patch_centroid = patch_embeddings.mean(axis=0)
        patch_centroid = self._normalize_rows(
            patch_centroid
        )

        patch_representatives = patch_embeddings[
            :min(16, len(patch_embeddings))
        ].copy()

        # ---------------------------------------------------------
        # Color
        # ---------------------------------------------------------

        print("[Fingerprint] Building color descriptors...")

        color_embeddings = np.stack([
            self._color_descriptor(p)
            for p in images
        ]).astype(np.float32)

        color_embeddings = self._normalize_rows(
            color_embeddings
        )

        color_centroid = self._normalize_vector(
            color_embeddings.mean(axis=0)
        )

        # ---------------------------------------------------------
        # Environment
        # ---------------------------------------------------------

        print("[Fingerprint] Building environment descriptors...")

        environment_embeddings = np.stack([
            self._environment_descriptor(p)
            for p in patch_embeddings
        ]).astype(np.float32)

        environment_embeddings = self._normalize_rows(
            environment_embeddings
        )

        environment_centroid = self._normalize_vector(
            environment_embeddings.mean(axis=0)
        )

        # ---------------------------------------------------------
        # FAISS
        # ---------------------------------------------------------

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings.astype(np.float32))

        # ---------------------------------------------------------
        # Atomic write
        # ---------------------------------------------------------

        parent = self.root

        tmp_dir = Path(
            tempfile.mkdtemp(
                prefix=f".{fingerprint_id}.tmp-",
                dir=str(parent),
            )
        )

        try:
            np.save(
                tmp_dir / "embeddings.npy",
                embeddings,
            )

            np.save(
                tmp_dir / "centroid.npy",
                centroid,
            )

            np.save(
                tmp_dir / "representatives.npy",
                representatives,
            )

            faiss.write_index(
                index,
                str(tmp_dir / "faiss.index"),
            )

            np.save(
                tmp_dir / "patch_embeddings.npy",
                patch_embeddings,
            )

            np.save(
                tmp_dir / "patch_centroid.npy",
                patch_centroid,
            )

            np.save(
                tmp_dir / "patch_representatives.npy",
                patch_representatives,
            )

            np.save(
                tmp_dir / "color_embeddings.npy",
                color_embeddings,
            )

            np.save(
                tmp_dir / "color_centroid.npy",
                color_centroid,
            )

            np.save(
                tmp_dir / "environment_embeddings.npy",
                environment_embeddings,
            )

            np.save(
                tmp_dir / "environment_centroid.npy",
                environment_centroid,
            )

            metadata = {
                "id": fingerprint_id,
                "version": "3.1",
                "images": len(images),
                "dimension": int(embeddings.shape[1]),
                "patches": int(patch_embeddings.shape[1]),
                "patch_dimension": int(
                    patch_embeddings.shape[2]
                ),
                "representatives": int(
                    representatives.shape[0]
                ),
                "image_names": [
                    p.name for p in images
                ],
                "source_folder": str(folder),
                "features": {
                    "global": True,
                    "patch": True,
                    "color": True,
                    "environment": True,
                },
            }

            (
                tmp_dir / "metadata.json"
            ).write_text(
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            # Final validation before publish.
            required = [
                "embeddings.npy",
                "centroid.npy",
                "representatives.npy",
                "faiss.index",
                "metadata.json",
                "patch_embeddings.npy",
                "patch_centroid.npy",
                "patch_representatives.npy",
                "color_embeddings.npy",
                "color_centroid.npy",
                "environment_embeddings.npy",
                "environment_centroid.npy",
            ]

            missing = [
                f for f in required
                if not (tmp_dir / f).exists()
            ]

            if missing:
                raise RuntimeError(
                    "Fingerprint creation incomplete: "
                    + ", ".join(missing)
                )

            tmp_dir.rename(final_dir)

        except Exception:
            shutil.rmtree(
                tmp_dir,
                ignore_errors=True,
            )
            raise

        print(
            f"[Fingerprint] Created '{fingerprint_id}'"
        )

        return metadata

    def _is_legacy(self, path: Path) -> bool:
        return not (
            (path / "color_embeddings.npy").exists()
            and (path / "color_centroid.npy").exists()
            and (path / "environment_embeddings.npy").exists()
            and (path / "environment_centroid.npy").exists()
        )

    def load(self, fingerprint_id: str) -> dict:
        path = self._path(fingerprint_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Fingerprint '{fingerprint_id}' not found"
            )

        required = [
            "embeddings.npy",
            "centroid.npy",
            "representatives.npy",
            "faiss.index",
            "metadata.json",
        ]

        missing = [
            f for f in required
            if not (path / f).exists()
        ]

        if missing:
            raise FileNotFoundError(
                f"Fingerprint '{fingerprint_id}' is incomplete. "
                f"Missing: {', '.join(missing)}"
            )

        data = {
            "id": fingerprint_id,
            "path": path,
            "embeddings": np.load(
                path / "embeddings.npy"
            ),
            "centroid": np.load(
                path / "centroid.npy"
            ),
            "representatives": np.load(
                path / "representatives.npy"
            ),
            "index": faiss.read_index(
                str(path / "faiss.index")
            ),
            "metadata": json.loads(
                (path / "metadata.json").read_text(
                    encoding="utf-8"
                )
            ),
        }

        # Legacy / optional features.
        optional = {
            "patch_embeddings": "patch_embeddings.npy",
            "patch_centroid": "patch_centroid.npy",
            "patch_representatives": "patch_representatives.npy",
            "color_embeddings": "color_embeddings.npy",
            "color_centroid": "color_centroid.npy",
            "environment_embeddings": "environment_embeddings.npy",
            "environment_centroid": "environment_centroid.npy",
        }

        for key, filename in optional.items():
            p = path / filename

            if p.exists():
                data[key] = np.load(p)

        data["version"] = data["metadata"].get(
            "version",
            "legacy",
        )

        data["legacy"] = self._is_legacy(path)

        return data

    def list_fingerprints(self) -> list[dict]:
        result = []

        if not self.root.exists():
            return result

        for path in sorted(self.root.iterdir()):
            if not path.is_dir():
                continue

            metadata_path = path / "metadata.json"

            if not metadata_path.exists():
                continue

            try:
                metadata = json.loads(
                    metadata_path.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                continue

            result.append({
                "id": path.name,
                "images": metadata.get("images", 0),
                "dimension": metadata.get("dimension"),
                "representatives": metadata.get(
                    "representatives"
                ),
                "version": metadata.get(
                    "version",
                    "legacy",
                ),
                "features": metadata.get(
                    "features",
                    {},
                ),
                "image_names": metadata.get(
                    "image_names",
                    [],
                ),
            })

        return result
PY

echo "[3/5] Writing recognizer.py"

cat > app/core/recognizer.py <<'PY'
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.core.fingerprint import FingerprintManager
from app.core.image import load_image

class SceneRecognizer:

    def __init__(self, settings, embedder):
        self.settings = settings
        self.embedder = embedder
        self.manager = FingerprintManager(
            settings,
            embedder,
        )

    @staticmethod
    def _cosine(a, b):
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)

        if a.ndim == 1:
            a = a[None, :]

        if b.ndim == 1:
            b = b[None, :]

        a = a / np.maximum(
            np.linalg.norm(a, axis=-1, keepdims=True),
            1e-8,
        )

        b = b / np.maximum(
            np.linalg.norm(b, axis=-1, keepdims=True),
            1e-8,
        )

        return a @ b.T

    def _global_score(self, q, ref):
        q = np.asarray(q, dtype=np.float32)

        best = float(
            np.max(
                self._cosine(
                    q,
                    ref["representatives"],
                )
            )
        )

        centroid = float(
            self._cosine(
                q,
                ref["centroid"],
            )[0, 0]
        )

        return 0.75 * best + 0.25 * centroid

    def _patch_score(self, q, ref):
        if "patch_representatives" not in ref:
            return 0.0

        reps = np.asarray(
            ref["patch_representatives"],
            dtype=np.float32,
        )

        q = np.asarray(q, dtype=np.float32)

        if q.ndim != 2:
            return 0.0

        # Expected:
        #
        # q   = 256 x 768
        # reps = N x 256 x 768
        #

        if reps.ndim != 3:
            return 0.0

        if reps.shape[1:] != q.shape:
            return 0.0

        q = q / np.maximum(
            np.linalg.norm(q, axis=1, keepdims=True),
            1e-8,
        )

        reps = reps / np.maximum(
            np.linalg.norm(reps, axis=2, keepdims=True),
            1e-8,
        )

        scores = []

        for r in reps:
            sim = q @ r.T

            # Each query patch finds the most similar
            # reference patch.
            q_to_r = sim.max(axis=1).mean()

            # Symmetric direction.
            r_to_q = sim.max(axis=0).mean()

            scores.append(
                0.5 * q_to_r
                + 0.5 * r_to_q
            )

        return float(max(scores))

    def _environment_score(self, query_env, ref):
        if "environment_centroid" not in ref:
            return 0.0

        return float(
            self._cosine(
                query_env,
                ref["environment_centroid"],
            )[0, 0]
        )

    def _color_score(self, query_color, ref):
        if "color_centroid" not in ref:
            return 0.0

        return float(
            self._cosine(
                query_color,
                ref["color_centroid"],
            )[0, 0]
        )

    def _score(
        self,
        global_embedding,
        patch_embedding,
        color_embedding,
        environment_embedding,
        ref,
    ):

        global_score = self._global_score(
            global_embedding,
            ref,
        )

        patch_score = self._patch_score(
            patch_embedding,
            ref,
        )

        color_score = self._color_score(
            color_embedding,
            ref,
        )

        environment_score = self._environment_score(
            environment_embedding,
            ref,
        )

        if ref.get("legacy", False):
            # Preserve useful legacy behavior.
            final = (
                0.60 * global_score
                + 0.40 * patch_score
            )
        else:
            # v3.1 deliberately prioritizes environment.
            final = (
                0.20 * global_score
                + 0.20 * patch_score
                + 0.15 * color_score
                + 0.45 * environment_score
            )

        return {
            "score": float(final),
            "global": float(global_score),
            "patch": float(patch_score),
            "color": float(color_score),
            "environment": float(
                environment_score
            ),
        }

    def _embed_one(self, path):
        result = self.embedder.embed_paths(
            [str(path)],
            return_patches=True,
        )

        if isinstance(result, tuple):
            embeddings, patches = result
        else:
            embeddings = result["embeddings"]
            patches = result["patch_embeddings"]

        global_embedding = np.asarray(
            embeddings[0],
            dtype=np.float32,
        )

        patch_embedding = np.asarray(
            patches[0],
            dtype=np.float32,
        )

        # Reuse FingerprintManager's color logic.
        color_embedding = (
            self.manager._color_descriptor(
                Path(path)
            )
        )

        environment_embedding = (
            self.manager._environment_descriptor(
                patch_embedding
            )
        )

        return (
            global_embedding,
            patch_embedding,
            color_embedding,
            environment_embedding,
        )

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        fingerprints = (
            self.manager.list_fingerprints()
        )

        if not fingerprints:
            raise RuntimeError(
                "Fingerprint database is empty."
            )

        for path in sorted(folder.iterdir()):

            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
                ".tif",
                ".tiff",
            }:
                continue

            (
                global_embedding,
                patch_embedding,
                color_embedding,
                environment_embedding,
            ) = self._embed_one(path)

            candidates = []

            for fp in fingerprints:
                ref = self.manager.load(fp["id"])

                scores = self._score(
                    global_embedding,
                    patch_embedding,
                    color_embedding,
                    environment_embedding,
                    ref,
                )

                candidates.append({
                    "id": fp["id"],
                    **scores,
                })

            candidates.sort(
                key=lambda x: x["score"],
                reverse=True,
            )

            best = candidates[0]

            result = {
                "file": str(path),
                "best_id": (
                    best["id"]
                    if best["score"] >= threshold
                    else None
                ),
                "score": best["score"],
                "candidates": candidates[:top_k],
            }

            yield result

    def analyze(
        self,
        folder,
        fingerprint_id,
    ):
        folder = Path(folder)

        ref = self.manager.load(
            fingerprint_id
        )

        for path in sorted(folder.iterdir()):

            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
                ".tif",
                ".tiff",
            }:
                continue

            (
                global_embedding,
                patch_embedding,
                color_embedding,
                environment_embedding,
            ) = self._embed_one(path)

            scores = self._score(
                global_embedding,
                patch_embedding,
                color_embedding,
                environment_embedding,
                ref,
            )

            best_image = None

            if "embeddings" in ref:
                similarities = self._cosine(
                    global_embedding,
                    ref["embeddings"],
                )[0]

                idx = int(
                    np.argmax(similarities)
                )

                names = ref["metadata"].get(
                    "image_names",
                    [],
                )

                if idx < len(names):
                    best_image = names[idx]

            yield {
                "file": str(path),
                "global_score": scores["global"],
                "patch_score": scores["patch"],
                "color_score": scores["color"],
                "environment_score": scores[
                    "environment"
                ],
                "final_score": scores["score"],
                "best_image": best_image,
            }
PY

echo "[4/5] Writing scene_analyzer.py"

cat > app/core/scene_analyzer.py <<'PY'
from __future__ import annotations

from app.core.recognizer import SceneRecognizer

class SceneAnalyzer:

    def __init__(self, settings, embedder):
        self.recognizer = SceneRecognizer(
            settings,
            embedder,
        )

    def analyze(
        self,
        folder,
        fingerprint_id,
    ):
        yield from self.recognizer.analyze(
            folder,
            fingerprint_id,
        )
PY

echo "[5/5] Updating CLI"

cat > app/cli.py <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer
from app.core.scene_analyzer import SceneAnalyzer

def main():

    p = argparse.ArgumentParser(
        description="Scene fingerprinting and recognition"
    )

    sub = p.add_subparsers(
        dest="cmd",
        required=True,
    )

    c = sub.add_parser(
        "create",
        help="Create a fingerprint from an image folder",
    )

    c.add_argument(
        "id",
        help="Fingerprint ID",
    )

    c.add_argument(
        "folder",
        help="Folder containing images",
    )

    r = sub.add_parser(
        "recognize",
        help="Recognize images against fingerprints",
    )

    r.add_argument(
        "folder",
        help="Folder containing query images",
    )

    r.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    r.add_argument(
        "--threshold",
        type=float,
        default=0.65,
    )

    a = sub.add_parser(
        "analyze",
        help="Analyze scene similarity components",
    )

    a.add_argument(
        "folder",
        help="Folder containing query images",
    )

    a.add_argument(
        "--fingerprint",
        required=True,
        help="Fingerprint ID",
    )

    args = p.parse_args()

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    if args.cmd == "create":

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        embedder = SceneEmbedder(settings)

        manager = FingerprintManager(
            settings,
            embedder,
        )

        result = manager.create(
            args.id,
            folder,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return

    # ---------------------------------------------------------
    # RECOGNIZE
    # ---------------------------------------------------------

    if args.cmd == "recognize":

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        embedder = SceneEmbedder(settings)

        recognizer = SceneRecognizer(
            settings,
            embedder,
        )

        for result in recognizer.recognize_folder(
            folder,
            args.top_k,
            args.threshold,
        ):
            print(result)

        return

    # ---------------------------------------------------------
    # ANALYZE
    # ---------------------------------------------------------

    if args.cmd == "analyze":

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        embedder = SceneEmbedder(settings)

        analyzer = SceneAnalyzer(
            settings,
            embedder,
        )

        for result in analyzer.analyze(
            folder,
            args.fingerprint,
        ):

            print()
            print(
                f"## {Path(result['file']).name}"
            )

            print(
                f"GLOBAL        "
                f"{result['global_score']:.4f}"
            )

            print(
                f"PATCH         "
                f"{result['patch_score']:.4f}"
            )

            print(
                f"COLOR         "
                f"{result['color_score']:.4f}"
            )

            print(
                f"ENVIRONMENT   "
                f"{result['environment_score']:.4f}"
            )

            print(
                f"FINAL         "
                f"{result['final_score']:.4f}"
            )

            if result["best_image"]:
                print(
                    f"BEST MATCH    "
                    f"{result['best_image']}"
                )

        return

if __name__ == "__main__":
    main()
PY

echo
echo "Checking Python syntax..."

uv run python -m py_compile \
    app/cli.py \
    app/core/fingerprint.py \
    app/core/recognizer.py \
    app/core/scene_analyzer.py

echo
echo "========================================"
echo " v3.1 UPGRADE COMPLETE"
echo "========================================"
echo
echo "Backup:"
echo "  $BACKUP"
echo
echo "IMPORTANT:"
echo "  Old fingerprints were NOT modified."
echo
echo "Next:"
echo
echo "  rm -rf data/fingerprints/78_v31"
echo
echo "  uv run scene-fingerprint create 78_v31 data/input/78"
echo
echo "Then:"
echo
echo "  uv run scene-fingerprint analyze data/input/new --fingerprint 78_v31"
echo
echo "And:"
echo
echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65"
echo
```

Сохрани:

```text id="jlh6s1"
Ctrl+O
Enter
Ctrl+X
```

### 2. Запусти

```bash id="1k7rby"
chmod +x upgrade_v31.sh
./upgrade_v31.sh
```

Если в конце увидишь:

```text
v3.1 UPGRADE COMPLETE
```

переходим к созданию нового fingerprint.

### 3. Создай чистый `78_v31`

```bash id="8q9h2k"
rm -rf data/fingerprints/78_v31

uv run scene-fingerprint create 78_v31 data/input/78
```

**Обрати внимание:** теперь создание должно закончиться без частично созданной папки. Если где-то произойдёт ошибка, временная директория будет удалена, а `78_v31` не появится.

После этого проверь:

```bash id="r7yqk3"
find data/fingerprints/78_v31 -maxdepth 1 -type f -printf '%f\n' | sort
```

Должны быть:

```text
centroid.npy
color_centroid.npy
color_embeddings.npy
embeddings.npy
environment_centroid.npy
environment_embeddings.npy
faiss.index
metadata.json
patch_centroid.npy
patch_embeddings.npy
patch_representatives.npy
representatives.npy
```

### 4. И только после этого — анализ

```bash id="7v8q0d"
uv run scene-fingerprint analyze \
    data/input/new \
    --fingerprint 78_v31
```

Здесь нас особенно интересуют четыре группы:

```text
GLOBAL
PATCH
COLOR
ENVIRONMENT
```

и итог:

```text
FINAL
```

**Пока не создавай 79–81.** Сначала посмотрим этот вывод на `78_v31`. Если environment действительно ведёт себя так, как ожидаем, тогда уже можно делать 79, 80 и 81 и начинать настоящий тест разделения объектов по окружению.

---


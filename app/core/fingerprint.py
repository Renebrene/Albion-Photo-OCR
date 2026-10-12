from __future__ import annotations

import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
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

        embedder = (
            embedder
            or self.embedder
        )

        parent = output.parent
        parent.mkdir(parents=True, exist_ok=True)

        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{fingerprint_id}.tmp-",
                dir=parent,
            )
        )

        try:
            metadata = self._build_into(
                staging,
                fingerprint_id,
                paths,
                embedder,
            )

            # output is either absent or an empty leftover directory.
            if output.exists():
                output.rmdir()

            os.replace(staging, output)

        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        return metadata

    def _build_into(
        self,
        output,
        fingerprint_id,
        paths,
        embedder,
    ):
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

        # --------------------------------------------------
        # CPU compact descriptors
        #
        # One image load per worker + parallel processing.
        # --------------------------------------------------

        workers = min(
            6,
            max(
                1,
                len(paths),
            ),
        )

        print(
            f"[Fingerprint v3.3] "
            f"CPU workers={workers}"
        )

        def calculate_descriptors(path):
            path = Path(path)

            return CompactDescriptor.all(
                path
            )

        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:

            descriptor_results = list(
                executor.map(
                    calculate_descriptors,
                    paths,
                )
            )

        environment_embeddings = np.stack(
            [
                item[0]
                for item in descriptor_results
            ]
        ).astype(np.float32)

        color_embeddings = np.stack(
            [
                item[1]
                for item in descriptor_results
            ]
        ).astype(np.float32)

        spatial_embeddings = np.stack(
            [
                item[2]
                for item in descriptor_results
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
            f"{fingerprint_id}"
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

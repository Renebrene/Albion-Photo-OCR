from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import faiss
import numpy as np
from PIL import Image, ImageOps

from app.ingest.integrity import read_taken_at

from .image import image_files
from .scene_analyzer import CompactDescriptor

# A small strip of source photos, published next to the vectors: the originals
# are not kept, so this is the only picture of what a fingerprint was built from
# once its source folder is gone. Four photos in one row is enough to recognise
# an address and keeps the file tiny. Additive - nothing reads the vectors
# differently, and a fingerprint without it stays valid.
PREVIEW_NAME = "preview.jpg"
PREVIEW_COLUMNS = 4
PREVIEW_ROWS = 1
PREVIEW_CELL = (160, 120)
PREVIEW_QUALITY = 72


def sample_paths(paths, count):
    """
    Take *count* photos spread across a sorted list.

    A stride, not the first N: the files are usually sorted by name (i.e. by
    shooting order), so the first N would be one burst of shots from a single
    viewpoint. Nothing is copied - the builder reads these paths directly.
    """

    paths = list(paths)

    if count >= len(paths) or count <= 0:
        return paths

    stride = len(paths) / count

    return [paths[int(index * stride)] for index in range(count)]


def readable_paths(paths):
    """
    Split source paths into decodable images and skipped files.

    A corrupt file with an image extension must not fail the whole build: it is
    listed in metadata.json and the fingerprint is built from the rest. Full
    decoding happens later in the embedder; here `verify()` is enough to catch
    a file Pillow cannot even parse (a common case for truncated camera JPEGs).
    """

    readable = []
    skipped = []

    for path in paths:
        path = Path(path)

        try:
            with Image.open(path) as image:
                image.verify()

            readable.append(path)
        except Exception as exc:  # noqa: BLE001 - one bad file, not the build
            skipped.append(
                {"name": path.name, "error": type(exc).__name__}
            )

    return readable, skipped


def image_meta(paths):
    """
    [{name, taken_at}] for the source photos of a fingerprint.

    The originals are not kept: their names and capture dates are the only
    trace the registry needs, so they are captured here while the folder is
    still at hand. EXIF is best-effort - a photo without a date is still listed.
    """

    result = []

    for path in paths:
        path = Path(path)
        taken_at = None

        try:
            with Image.open(path) as image:
                if getattr(image, "n_frames", 1) > 1:
                    image.seek(0)

                taken_at = read_taken_at(image)
        except Exception:  # noqa: BLE001 - a broken EXIF must not fail a build
            taken_at = None

        result.append({"name": path.name, "taken_at": taken_at})

    return result


def build_preview(
    paths,
    output,
    *,
    columns=PREVIEW_COLUMNS,
    rows=PREVIEW_ROWS,
    cell=PREVIEW_CELL,
    quality=PREVIEW_QUALITY,
):
    """
    Compose a montage of up to columns*rows source photos into *output*.

    The photos are sampled with the same stride the build uses, so the montage
    shows the spread of viewpoints rather than one burst. A file that cannot be
    decoded is skipped; when nothing could be read nothing is written and None
    is returned - an unreadable source must never fail a build.
    """

    picks = sample_paths(list(paths), columns * rows)
    thumbs = []

    for path in picks:
        try:
            with Image.open(path) as image:
                if getattr(image, "n_frames", 1) > 1:
                    image.seek(0)

                thumbs.append(
                    ImageOps.fit(
                        image.convert("RGB"),
                        cell,
                        method=Image.LANCZOS,
                    )
                )
        except Exception:  # noqa: BLE001 - a broken photo must not fail a build
            continue

    if not thumbs:
        return None

    canvas = Image.new(
        "RGB",
        (cell[0] * columns, cell[1] * rows),
        (24, 24, 24),
    )

    for index, thumb in enumerate(thumbs):
        canvas.paste(
            thumb,
            ((index % columns) * cell[0], (index // columns) * cell[1]),
        )

    canvas.save(output, format="JPEG", quality=quality, optimize=True)

    return output


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
        descriptor_workers=None,
    ):
        self.settings = settings
        self.embedder = embedder

        # Threads for the CPU descriptor pass (one image load per worker).
        # Default 6 as before; a caller that already runs several builders in
        # parallel passes a smaller number so the cores are not oversubscribed.
        self.descriptor_workers = descriptor_workers

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
        *,
        max_photos=None,
        replace=False,
        source_folder=None,
        progress=None,
    ):
        """
        Build one fingerprint from every image in *folder* (recursively).

        max_photos  - use at most this many photos, spread across the folder
                      (the subset rule for new fingerprints). No file is copied:
                      the builder reads the sources where they are.
        progress    - progress(done, total, stage) called between batches; the
                      worker turns it into the job's progress bar and uses the
                      pauses between calls to notice a pause/cancel request.
        replace     - overwrite an existing fingerprint. The previous vectors are
                      moved aside first and only deleted once the new ones are
                      published, so a failed rebuild leaves the old fingerprint
                      in place.
        source_folder - recorded in metadata.json for the registry.
        """

        fingerprint_id = str(
            fingerprint_id
        )

        folder = Path(folder)

        paths = image_files(folder)

        if not paths:
            raise ValueError(
                f"No images found in {folder}"
            )

        # Unreadable files (truncated JPEGs, wrong content with an image
        # extension) are skipped and recorded instead of failing the build.
        paths, skipped = readable_paths(paths)

        if not paths:
            raise ValueError(
                "No readable images found in "
                f"{folder}: {len(skipped)} file(s) could not be decoded"
            )

        if skipped:
            print(
                f"[Fingerprint v3.3] skipped {len(skipped)} unreadable file(s): "
                + ", ".join(item["name"] for item in skipped[:10])
            )

        if max_photos:
            paths = sample_paths(paths, int(max_photos))

        output = self._path(
            fingerprint_id
        )

        previous = None

        if output.exists():
            existing = list(
                output.iterdir()
            )

            if existing and not replace:
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
                source_folder=source_folder,
                progress=progress,
                skipped=skipped,
            )

            # Move the old vectors aside only now that the new ones exist.
            if output.exists() and any(output.iterdir()):
                previous = Path(
                    tempfile.mkdtemp(
                        prefix=f".{fingerprint_id}.old-",
                        dir=parent,
                    )
                )
                previous.rmdir()
                os.replace(output, previous)
            elif output.exists():
                # An empty leftover directory.
                output.rmdir()

            os.replace(staging, output)

        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)

            if previous is not None and previous.exists() and not output.exists():
                os.replace(previous, output)

            raise

        if previous is not None:
            shutil.rmtree(previous, ignore_errors=True)

        return metadata

    def _build_into(
        self,
        output,
        fingerprint_id,
        paths,
        embedder,
        source_folder=None,
        progress=None,
        skipped=(),
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

        # The build has two equal halves: embeddings, then CPU descriptors.
        total_units = max(1, len(paths) * 2)

        def report(done, total, stage):
            if progress is not None:
                progress(done, total, stage)

        embeddings = embedder.embed_paths(
            paths,
            on_batch=lambda done, total: report(done, total_units, "эмбеддинги"),
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
            self.descriptor_workers or 6,
            max(
                1,
                len(paths),
            ),
        )

        print(
            f"[Fingerprint v3.3] "
            f"CPU workers={workers}"
        )

        descriptor_done = 0
        descriptor_lock = threading.Lock()

        def calculate_descriptors(path):
            nonlocal descriptor_done

            path = Path(path)

            descriptor = CompactDescriptor.all(
                path
            )

            with descriptor_lock:
                descriptor_done += 1
                report(len(paths) + descriptor_done, total_units, "дескрипторы")

            return descriptor

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

        # Small montage of the sources, published with the vectors (the window
        # shows it for a fingerprint whose source folder is long gone).
        preview = build_preview(paths, output / PREVIEW_NAME)

        metadata = {
            "id": fingerprint_id,
            "version": self.VERSION,
            # Where the reference photos came from and what they were: the
            # originals are not stored, so the registry keeps their names
            # and capture dates here (schema/024).
            "source_folder": str(source_folder) if source_folder else None,
            "image_meta": image_meta(paths),
            "model": str(
                getattr(
                    embedder,
                    "model_name",
                    self.settings.model_name,
                )
            ),
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
            # None when no source photo could be decoded for the montage.
            "preview": PREVIEW_NAME if preview else None,
            # Files with an image extension that could not be decoded; they
            # never entered the vectors.
            "skipped_images": list(skipped),
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

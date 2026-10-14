"""
Build (or rebuild) one fingerprint from a folder - the job entry point.

Called from the PostgreSQL job worker (job_type FINGERPRINT_BUILD), which is the
process that already runs the heavy work. The SQLite fingerprint queue
(app.pipeline.worker) remains for batch builds from the CLI; this path is what
the web window uses.

Nothing is copied and nothing is kept from the sources: the builder reads the
folder where it is, writes the vectors into data/fingerprints/<id>/ and records
the names and capture dates of the photos it used. After that the folder is not
needed again.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager


# One DINOv2 per process. The worker builds many fingerprints in its lifetime
# and loading the model costs over a second, so it is loaded once and reused
# (the SQLite worker in app/pipeline/worker.py loads it once in __init__ too).
_EMBEDDER_CACHE: dict[tuple[str, str], SceneEmbedder] = {}


def get_embedder() -> SceneEmbedder:
    """The process-wide embedder for the current model/device."""

    key = (settings.model_name, settings.device)

    embedder = _EMBEDDER_CACHE.get(key)

    if embedder is None:
        embedder = SceneEmbedder(settings)
        _EMBEDDER_CACHE[key] = embedder

    return embedder


def default_descriptor_workers() -> int:
    """
    Half the cores, at least one - a single build should not grab them all.

    Several builders run at once (worker --parallel), so the share is divided
    by that number: otherwise N builders each take half the cores and the
    descriptor pass oversubscribes the machine N times over.
    """

    parallel = max(1, int(os.getenv("SCENE_BUILD_PARALLEL", "1") or 1))

    return max(1, (os.cpu_count() or 1) // parallel // 2)


def build_fingerprint(
    fingerprint_id: str,
    folder: str,
    *,
    max_photos: int | None = None,
    replace: bool = True,
    progress=None,
) -> dict:
    """
    Build one fingerprint and refresh the registry.

    Returns a JSON-serialisable summary for the job row: the id, how many photos
    were used, the folder and the algorithm version.

    `progress(done, total, stage)` is handed to the builder; the worker uses it
    both for the progress bar and to notice a pause/cancel request.
    """

    from app.api import fingerprints as registry

    folder_path = Path(folder)

    if not folder_path.is_dir():
        raise ValueError("source folder not found")

    settings.fingerprints_dir.mkdir(parents=True, exist_ok=True)

    embedder = get_embedder()
    manager = FingerprintManager(
        settings,
        embedder,
        descriptor_workers=default_descriptor_workers(),
    )

    metadata = manager.create(
        fingerprint_id,
        folder_path,
        embedder,
        max_photos=max_photos,
        replace=replace,
        source_folder=str(folder_path),
        progress=progress,
    )

    # The registry mirrors metadata.json; syncing here means the new version is
    # visible in the window the moment the job finishes.
    sync = registry.sync_from_disk()

    return {
        "fingerprint_id": str(fingerprint_id),
        "folder": str(folder_path),
        "images": int(metadata.get("images") or 0),
        "version": metadata.get("version"),
        "max_photos": max_photos,
        "replaced": bool(replace),
        "versions_added": [
            item for item in sync["versions_added"] if item == str(fingerprint_id)
        ],
    }

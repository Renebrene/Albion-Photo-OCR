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


def _batch_recalc_needed(
    batch_id: str | None,
    job_id: int | None,
    current_replaced: bool,
) -> bool:
    """
    Should this finished build queue the one recalculation for its batch?

    ``build-batch`` runs several builders in parallel. Waiting for the last one
    avoids enqueueing a full pass per rebuilt fingerprint. The check is only a
    best-effort read: the recalculation itself is deduplicated by an advisory
    lock, so two last builders still cannot enqueue twice.
    """

    if not batch_id or job_id is None:
        return current_replaced

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM public.job_queue
                WHERE job_type = 'FINGERPRINT_BUILD'
                  AND status IN ('PENDING', 'RUNNING')
                  AND id <> %s
                  AND payload ->> 'batch_id' = %s
                LIMIT 1
                """,
                (int(job_id), str(batch_id)),
            )

            if cur.fetchone() is not None:
                return False

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM public.job_queue
                    WHERE job_type = 'FINGERPRINT_BUILD'
                      AND status = 'DONE'
                      AND payload ->> 'batch_id' = %s
                      AND result ->> 'replaced_existing' = 'true'
                )
                """,
                (str(batch_id),),
            )

            return bool(cur.fetchone()[0]) or current_replaced


def build_fingerprint(
    fingerprint_id: str,
    folder: str,
    *,
    max_photos: int | None = None,
    replace: bool = True,
    recalculate: bool = False,
    batch_id: str | None = None,
    job_id: int | None = None,
    progress=None,
) -> dict:
    """
    Build one fingerprint and refresh the registry.

    Returns a JSON-serialisable summary for the job row: the id, how many photos
    were used, the folder and the algorithm version.

    *recalculate* queues one full DINO+HYBRID pass when an existing fingerprint
    was actually replaced: the new vectors make every stored verdict stale.
    A brand-new fingerprint needs no recalculation.

    `progress(done, total, stage)` is handed to the builder; the worker uses it
    both for the progress bar and to notice a pause/cancel request.
    """

    from app.api import fingerprints as registry

    folder_path = Path(folder)

    if not folder_path.is_dir():
        raise ValueError("source folder not found")

    settings.fingerprints_dir.mkdir(parents=True, exist_ok=True)

    output = settings.fingerprints_dir / str(fingerprint_id)
    replaced_existing = output.is_dir() and any(output.iterdir())

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

    recalc = None
    recalc_error = None

    if recalculate and _batch_recalc_needed(
        batch_id, job_id, replaced_existing
    ):
        # The fingerprint files are already published, so a DINO job started
        # now reads the new vectors.
        try:
            from app.dino.recalc import enqueue_recalculation

            recalc = enqueue_recalculation(
                reason="замены",
                fingerprint_id=str(fingerprint_id),
            )
        except Exception as exc:  # noqa: BLE001 - the build itself succeeded
            recalc_error = type(exc).__name__

    return {
        "fingerprint_id": str(fingerprint_id),
        "folder": str(folder_path),
        "images": int(metadata.get("images") or 0),
        "skipped_images": metadata.get("skipped_images") or [],
        "version": metadata.get("version"),
        "max_photos": max_photos,
        "replaced": bool(replace),
        "replaced_existing": replaced_existing,
        "recalculated": bool(recalc),
        "recalc": recalc,
        "recalc_error": recalc_error,
        "versions_added": [
            item for item in sync["versions_added"] if item == str(fingerprint_id)
        ],
    }

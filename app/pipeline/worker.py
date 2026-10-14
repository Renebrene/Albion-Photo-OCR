"""
Fingerprint queue worker (the local SQLite queue, not the DINO batches).

Building a fingerprint is a CPU task: DINOv2 embeddings in batches plus a
parallel descriptor pass. One builder leaves most of the machine idle, so the
queue is drained by several builder processes at once by default - half of the
logical cores, as agreed for this project.

    python -m app.pipeline.worker                 # half the cores
    python -m app.pipeline.worker --workers 4     # explicit
    python -m app.pipeline.worker --workers 1     # old, sequential behaviour

Each builder claims jobs atomically from public SQLite `data/jobs.db`
(BEGIN IMMEDIATE), so several processes can share one queue safely. Every
builder loads its own copy of the model, therefore the per-process thread
budget is cores / builders: without that, N builders would each try to use
every core and the machine would thrash.

Nothing here touches the PostgreSQL pipeline (DINO batches, HYBRID, QWEN).
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue


def default_workers() -> int:
    """Half of the logical cores, at least one."""

    return max(1, (os.cpu_count() or 1) // 2)


def threads_per_worker(workers: int) -> int:
    """torch threads for one builder so that all of them fit the machine."""

    cores = os.cpu_count() or 1

    return max(1, cores // max(1, workers))


def descriptor_threads(workers: int) -> int:
    """Threads for the CPU descriptor pass of one builder."""

    return max(1, min(6, (os.cpu_count() or 1) // max(1, workers)))


class FingerprintWorker:

    def __init__(
        self,
        *,
        descriptor_workers: int | None = None,
        queue=None,
        manager=None,
    ):
        # queue/manager are injectable so the claim loop can be tested without
        # loading the model; production callers pass neither.
        self.queue = queue or JobQueue(
            settings.data_dir / "jobs.db"
        )

        if manager is not None:
            self.embedder = getattr(manager, "embedder", None)
            self.manager = manager
            return

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
            settings
        )

        self.manager = FingerprintManager(
            settings,
            self.embedder,
            descriptor_workers=descriptor_workers,
        )

    def run_once(self):
        job = self.queue.claim()

        if job is None:
            return False

        job_id = job["id"]
        fingerprint_id = job["fingerprint_id"]
        source_folder = Path(
            job["source_folder"]
        )

        print()
        print("=" * 60)
        print(f"[Worker] Job {job_id}")
        print(f"[Worker] Fingerprint: {fingerprint_id}")
        print(f"[Worker] Folder: {source_folder}")
        print("=" * 60)

        try:
            self.manager.create(
                fingerprint_id,
                source_folder,
                self.embedder,
            )

            self.queue.complete(
                job_id
            )

            print(
                f"[Worker] DONE: {fingerprint_id}"
            )

            return True

        except Exception as exc:
            self.queue.fail(
                job_id,
                repr(exc),
            )

            print(
                f"[Worker] FAILED: "
                f"{fingerprint_id}: {exc}"
            )

            return True

    def process_queue(self) -> int:
        """Drain the queue; returns how many jobs this builder processed."""

        processed = 0

        while True:
            if not self.run_once():
                break

            processed += 1

        return processed

    def run(self) -> None:
        print("[Worker] Starting batch processing")

        processed = self.process_queue()

        print()
        print("=" * 60)
        print(
            f"[Worker] Batch complete. "
            f"Processed: {processed}"
        )
        print("=" * 60)


def _builder_main(threads: int, descriptor_workers: int, label: str) -> None:
    """Entry point of one builder process."""

    # Torch reads these at import/first use; set them before the model loads.
    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(threads))

    try:
        import torch

        torch.set_num_threads(threads)
    except Exception:  # noqa: BLE001 - a missing torch is reported later
        pass

    worker = FingerprintWorker(
        descriptor_workers=descriptor_workers,
    )

    processed = worker.process_queue()

    print(f"[Worker {label}] processed {processed}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PhotoBAse fingerprint queue worker",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "parallel builders "
            f"(default: half the cores, {default_workers()} here)"
        ),
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="torch threads per builder (default: cores / builders)",
    )
    args = parser.parse_args()

    workers = max(1, args.workers or default_workers())
    threads = max(1, args.threads or threads_per_worker(workers))
    descriptors = descriptor_threads(workers)

    print(
        f"[Worker] builders={workers} torch_threads={threads} "
        f"descriptor_threads={descriptors} cores={os.cpu_count()}",
        flush=True,
    )

    if workers == 1:
        _builder_main(threads, descriptors, "1/1")
        return

    # spawn, not fork: the parent has not loaded torch, and spawn keeps a
    # child from inheriting half-initialised native state.
    context = mp.get_context("spawn")

    processes = [
        context.Process(
            target=_builder_main,
            args=(threads, descriptors, f"{index + 1}/{workers}"),
        )
        for index in range(workers)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    failed = [process.exitcode for process in processes if process.exitcode]

    if failed:
        raise SystemExit(f"builder(s) failed with exit codes: {failed}")


if __name__ == "__main__":
    main()

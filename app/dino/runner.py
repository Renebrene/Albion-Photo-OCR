from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.errors import redact_absolute_paths
from app.core.fingerprint import FingerprintManager
from app.core.scene_analyzer import CompactDescriptor
from app.dino.database import (
    DinoWorkItem,
    finish_batch,
    get_batch,
    get_batch_items,
    save_failure,
    save_success,
    start_batch,
    start_run,
)


HIGH_SCORE = 0.90
PROBABLE_SCORE = 0.80
HIGH_MARGIN = 0.03
PROBABLE_MARGIN = 0.015
DINO_THRESHOLD = 0.65


def default_workers() -> int:
    return max(1, (os.cpu_count() or 1) // 2)


def resolve_workers(workers: int | None = None) -> int:
    """
    Resolve the DINO worker count.

    Explicit value wins; otherwise SCENE_DINO_WORKERS is used (0 = automatic
    half-CPU, matching the documented default).
    """

    if workers is None:
        workers = settings.dino_workers

    if workers == 0:
        workers = default_workers()

    if workers < 1:
        raise ValueError("workers must be >= 1")

    return workers


def confidence_status(score: float, margin: float) -> tuple[str, str]:
    if score >= HIGH_SCORE and margin >= HIGH_MARGIN:
        return "HIGH", "CONFIDENT"

    if score >= PROBABLE_SCORE and margin >= PROBABLE_MARGIN:
        return "PROBABLE", "PROBABLE_MATCH"

    if score >= PROBABLE_SCORE:
        return "AMBIGUOUS", "AMBIGUOUS"

    return "NO_MATCH", "NO_MATCH"


def compare_loaded(
    query_global,
    query_environment,
    query_color,
    query_spatial,
    data,
) -> dict:
    centroid = data["centroid"]

    global_score = float(query_global @ centroid)

    image_scores = data["embeddings"] @ query_global
    best_index = int(image_scores.argmax())
    best_image_score = float(image_scores[best_index])

    image_names = data["metadata"].get("image_names", [])
    best_image = (
        image_names[best_index]
        if best_index < len(image_names)
        else None
    )

    def descriptor_similarity(query, references):
        scores = references @ query
        k = max(3, int(len(scores) * 0.10))
        k = min(k, len(scores))
        if k <= 0:
            return 0.0
        top_scores = sorted(
            (float(value) for value in scores),
            reverse=True,
        )[:k]
        return float(sum(top_scores) / len(top_scores))

    environment_score = descriptor_similarity(
        query_environment,
        data["environment_embeddings"],
    )

    color_score = descriptor_similarity(
        query_color,
        data["color_embeddings"],
    )

    spatial_score = descriptor_similarity(
        query_spatial,
        data["spatial_embeddings"],
    )

    final_score = (
        0.70 * global_score
        + 0.20 * environment_score
        + 0.07 * color_score
        + 0.03 * spatial_score
    )

    return {
        "score": float(final_score),
        "global": global_score,
        "environment": environment_score,
        "color": color_score,
        "spatial": spatial_score,
        "best_image": best_image,
        "best_image_score": best_image_score,
    }


class DinoRunner:
    """
    DINO v3.3 batch execution point.

    The current DINO execution is CPU-only.

    A batch is created separately and has fixed membership.
    Each completed photo is written to PostgreSQL immediately.
    """

    def __init__(self, workers: int = 1):
        self.workers = max(1, int(workers))

        # Settings is frozen, therefore create a separate CPU configuration.
        self.cpu_settings = replace(settings, device="cpu")

        print(f"[DINO Runner] CPU workers={self.workers}")
        print(f"[DINO Runner] device={self.cpu_settings.device}")
        print(f"[DINO Runner] model={self.cpu_settings.model_name}")

        self.embedder = SceneEmbedder(self.cpu_settings)

        self.manager = FingerprintManager(
            self.cpu_settings,
            self.embedder,
        )

        self.fingerprints = self._load_fingerprints()

    def _load_fingerprints(self):
        loaded = []

        for metadata in self.manager.list_fingerprints():
            fingerprint_id = metadata.get("id")

            if not fingerprint_id:
                continue

            try:
                data = self.manager.load(fingerprint_id)
            except (FileNotFoundError, ValueError, OSError) as exc:
                print(
                    f"[DINO Runner] SKIP fingerprint "
                    f"{fingerprint_id}: {exc}"
                )
                continue

            if data.get("metadata", {}).get("version") != "3.3":
                continue

            if data["embeddings"].shape[1] != 768:
                continue

            loaded.append((str(fingerprint_id), data))

        if not loaded:
            raise ValueError(
                "No compatible v3.3 / 768D fingerprints found."
            )

        print(
            "[DINO Runner] Fingerprints: "
            + ", ".join(
                fingerprint_id
                for fingerprint_id, _ in loaded
            )
        )

        return loaded

    def recognize_one(self, item: DinoWorkItem) -> dict:
        started = time.perf_counter()
        path = Path(item.source_path)

        query_global = self.embedder.embed_paths([path])[0]

        image = CompactDescriptor._load(path)

        (
            query_environment,
            query_color,
            query_spatial,
        ) = CompactDescriptor.all_from_image(image)

        ranked = []

        for fingerprint_id, data in self.fingerprints:
            result = compare_loaded(
                query_global=query_global,
                query_environment=query_environment,
                query_color=query_color,
                query_spatial=query_spatial,
                data=data,
            )

            ranked.append(
                {
                    "id": fingerprint_id,
                    "score": result["score"],
                    "global": result["global"],
                    "environment": result["environment"],
                    "color": result["color"],
                    "spatial": result["spatial"],
                    "best_image": result["best_image"],
                    "best_image_score": result["best_image_score"],
                }
            )

        ranked.sort(
            key=lambda candidate: candidate["score"],
            reverse=True,
        )
        ranked = ranked[:5]

        if not ranked:
            raise ValueError(
                f"No DINO candidates for {item.photo_id}"
            )

        best_score = float(ranked[0]["score"])
        second_score = (
            float(ranked[1]["score"])
            if len(ranked) > 1
            else 0.0
        )
        margin = best_score - second_score

        confidence, status = confidence_status(
            best_score,
            margin,
        )

        best_id = (
            ranked[0]["id"]
            if best_score >= DINO_THRESHOLD
            else None
        )

        return {
            "best_id": best_id,
            "score": best_score,
            "second_score": second_score,
            "margin": margin,
            "confidence": confidence,
            "status": status,
            "candidates": ranked,
            "time_sec": time.perf_counter() - started,
        }


def _process_item(runner: DinoRunner, item: DinoWorkItem) -> tuple[DinoWorkItem, dict]:
    run_item = start_run(item.run_id)

    started = time.perf_counter()

    try:
        result = runner.recognize_one(run_item)

        save_success(
            run_item.run_id,
            best_id=result["best_id"],
            score=result["score"],
            second_score=result["second_score"],
            margin=result["margin"],
            confidence=result["confidence"],
            status=result["status"],
            dino_time_sec=result["time_sec"],
            candidates=result["candidates"],
        )

        return run_item, result

    except Exception as exc:
        save_failure(
            run_item.run_id,
            error_message=redact_absolute_paths(repr(exc)),
            dino_time_sec=time.perf_counter() - started,
        )
        raise


def run_batch(
    batch_id: int,
    workers: int | None = None,
    limit: int | None = None,
):
    workers = resolve_workers(workers)

    batch = get_batch(batch_id)

    if batch is None:
        raise ValueError(
            f"DINO batch {batch_id} not found"
        )

    if batch.status not in {"PENDING", "RUNNING"}:
        raise ValueError(
            f"DINO batch {batch_id} cannot run from "
            f"status {batch.status}"
        )

    items = get_batch_items(batch_id)

    if not items:
        raise ValueError(
            f"DINO batch {batch_id} has no PENDING items"
        )

    if limit is not None:
        limit = int(limit)
        if limit < 1:
            raise ValueError("limit must be >= 1")
        items = items[:limit]

    print()
    print("=" * 70)
    print(f"[DINO Runner] BATCH {batch.batch_id}")
    print(f"[DINO Runner] type={batch.run_type}")
    print(f"[DINO Runner] status={batch.status}")
    print(f"[DINO Runner] pending_selected={len(items)}")
    print(f"[DINO Runner] workers={max(1, int(workers))}")
    if limit is not None:
        print(f"[DINO Runner] limit={limit}")
    print("=" * 70)

    if batch.status == "PENDING":
        start_batch(batch_id)

    runner = DinoRunner(workers=workers)
    started = time.perf_counter()

    processed = 0
    failed = 0

    if runner.workers == 1:
        for item in items:
            try:
                run_item, result = _process_item(runner, item)

                processed += 1

                print(
                    f"[DINO Runner] DONE "
                    f"{processed}/{len(items)} "
                    f"{run_item.photo_id} "
                    f"score={result['score']:.4f} "
                    f"time={result['time_sec']:.2f}s"
                )

            except Exception as exc:
                failed += 1
                print(
                    f"[DINO Runner] FAILED "
                    f"{item.photo_id}: {exc}"
                )

    else:
        with ThreadPoolExecutor(
            max_workers=runner.workers
        ) as executor:
            futures = {
                executor.submit(
                    _process_item,
                    runner,
                    item,
                ): item
                for item in items
            }

            for future in as_completed(futures):
                item = futures[future]

                try:
                    run_item, result = future.result()

                    processed += 1

                    print(
                        f"[DINO Runner] DONE "
                        f"{processed}/{len(items)} "
                        f"{run_item.photo_id} "
                        f"score={result['score']:.4f} "
                        f"time={result['time_sec']:.2f}s"
                    )

                except Exception as exc:
                    failed += 1
                    print(
                        f"[DINO Runner] FAILED "
                        f"{item.photo_id}: {exc}"
                    )

    final_batch = finish_batch(batch_id)

    elapsed = time.perf_counter() - started

    print()
    print("=" * 70)
    print(f"[DINO Runner] FINISHED BATCH {batch_id}")
    print(f"[DINO Runner] status={final_batch.status}")
    print(f"[DINO Runner] processed={processed}")
    print(f"[DINO Runner] failed={failed}")
    print(f"[DINO Runner] elapsed={elapsed:.2f}s")
    print("=" * 70)

    return final_batch


def main():
    parser = argparse.ArgumentParser(
        description="Run an existing DINO batch."
    )

    parser.add_argument(
        "batch_id",
        type=int,
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="worker threads; default from SCENE_DINO_WORKERS (0 = half CPU)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    run_batch(
        batch_id=args.batch_id,
        workers=args.workers,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()

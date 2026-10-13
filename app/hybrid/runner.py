import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from app.core.errors import redact_absolute_paths
from app.core.parallel import bounded_submit, default_window
from app.hybrid.database import (
    HybridWorkItem,
    completed_photo_ids,
    get_run,
    get_run_items,
    save_failure,
    save_success,
    start_run,
    finish_run,
)


GLOBAL_WEIGHT = 10.0
NEIGHBOR_BONUS = 3.0
SWITCH_GAIN = 1.5


def default_workers() -> int:
    return max(1, (os.cpu_count() or 1) // 2)


def hybrid_one(
    items: list[HybridWorkItem],
    index: int,
) -> dict:
    item = items[index]
    started = time.perf_counter()

    old = item.dino_best_id

    scores: dict[str, float] = {}

    for candidate in item.candidates:
        fingerprint_id = candidate.get("id")
        score = candidate.get("score")

        if not fingerprint_id or score is None:
            continue

        fingerprint_id = str(fingerprint_id)
        scores[fingerprint_id] = (
            scores.get(fingerprint_id, 0.0)
            + float(score) * GLOBAL_WEIGHT
        )

    neighbors: dict[str, str] = {}

    left_fp = None
    right_fp = None

    if index > 0:
        left_fp = items[index - 1].dino_best_id
        if left_fp is not None:
            neighbors["left"] = left_fp

    if index < len(items) - 1:
        right_fp = items[index + 1].dino_best_id
        if right_fp is not None:
            neighbors["right"] = right_fp

    if (
        left_fp is not None
        and right_fp is not None
        and left_fp == right_fp
    ):
        scores[left_fp] = scores.get(left_fp, 0.0) + NEIGHBOR_BONUS

    best = old

    ranked = sorted(
        scores.items(),
        key=lambda pair: pair[1],
        reverse=True,
    )

    if ranked:
        candidate = ranked[0][0]
        candidate_score = scores[candidate]
        old_score = scores.get(old, 0.0)

        gain = candidate_score - old_score

        if candidate != old and gain > SWITCH_GAIN:
            best = candidate

    old_score = scores.get(old, 0.0) if old is not None else 0.0
    new_score = scores.get(best, 0.0) if best is not None else 0.0

    hybrid_changed = best != old

    elapsed = time.perf_counter() - started

    return {
        "photo_id": item.photo_id,
        "dino_run_id": item.dino_run_id,
        "hybrid_original_id": old,
        "hybrid_final_id": best,
        "hybrid_changed": hybrid_changed,
        "hybrid_old_score": old_score,
        "hybrid_score": new_score,
        "hybrid_margin": item.dino_margin,
        "hybrid_neighbors": json.dumps(
            neighbors,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "hybrid_time_sec": elapsed,
    }


def _process_item(
    hybrid_run_id: int,
    items: list[HybridWorkItem],
    index: int,
) -> tuple[str, bool]:
    item = items[index]
    started = time.perf_counter()

    try:
        result = hybrid_one(items, index)

        save_success(
            hybrid_run_id=hybrid_run_id,
            photo_id=result["photo_id"],
            dino_run_id=result["dino_run_id"],
            hybrid_original_id=result["hybrid_original_id"],
            hybrid_final_id=result["hybrid_final_id"],
            hybrid_changed=result["hybrid_changed"],
            hybrid_old_score=result["hybrid_old_score"],
            hybrid_score=result["hybrid_score"],
            hybrid_margin=result["hybrid_margin"],
            hybrid_neighbors=result["hybrid_neighbors"],
            hybrid_time_sec=result["hybrid_time_sec"],
        )

        return item.photo_id, True

    except Exception as exc:
        elapsed = time.perf_counter() - started

        try:
            save_failure(
                hybrid_run_id=hybrid_run_id,
                photo_id=item.photo_id,
                dino_run_id=item.dino_run_id,
                error_message=redact_absolute_paths(str(exc)),
                hybrid_time_sec=elapsed,
            )
        except Exception:
            raise

        return item.photo_id, False


def run(
    hybrid_run_id: int,
    workers: int | None = None,
) -> None:
    workers = default_workers() if workers is None else max(1, int(workers))

    run_info = get_run(hybrid_run_id)

    # Only a PENDING run may be claimed; a RUNNING one belongs to another
    # executor (or was left by a crashed one and must be recovered first).
    if run_info.status != "PENDING":
        raise ValueError(
            f"HYBRID run {hybrid_run_id} cannot be claimed from status "
            f"{run_info.status}"
        )

    items = get_run_items(hybrid_run_id)

    if len(items) != run_info.total_count:
        raise ValueError(
            f"HYBRID input mismatch: "
            f"{len(items)} items, expected {run_info.total_count}"
        )

    # Atomic PENDING -> RUNNING claim (UPDATE ... WHERE status='PENDING').
    start_run(hybrid_run_id)

    # On a recovered rerun, skip items that already produced a DONE result.
    already_done = completed_photo_ids(hybrid_run_id)
    pending_indexes = [
        index
        for index in range(len(items))
        if items[index].photo_id not in already_done
    ]

    print("=" * 80)
    print("HYBRID RUNNER")
    print("=" * 80)
    print(f"run_id={hybrid_run_id}")
    print(f"dino_batch_id={run_info.dino_batch_id}")
    print(f"items={len(items)}")
    print(f"already_done={len(already_done)}")
    print(f"to_process={len(pending_indexes)}")
    print(f"workers={workers}")
    print(f"GLOBAL_WEIGHT={GLOBAL_WEIGHT}")
    print(f"NEIGHBOR_BONUS={NEIGHBOR_BONUS}")
    print(f"SWITCH_GAIN={SWITCH_GAIN}")
    print("SUBFINGERPRINTS=DISABLED")
    print("IMAGE_READS=DISABLED")
    print()

    started = time.perf_counter()

    completed = 0
    failed = 0

    if workers == 1:
        for index in pending_indexes:
            photo_id, ok = _process_item(
                hybrid_run_id,
                items,
                index,
            )

            if ok:
                completed += 1
            else:
                failed += 1

            print(
                f"[HYBRID] {completed + failed}/{len(pending_indexes)} "
                f"photo={photo_id} "
                f"status={'DONE' if ok else 'FAILED'}"
            )

    else:
        worker = partial(_process_item, hybrid_run_id, items)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for _index, future in bounded_submit(
                executor,
                worker,
                pending_indexes,
                window=default_window(workers),
            ):
                photo_id, ok = future.result()

                if ok:
                    completed += 1
                else:
                    failed += 1

                print(
                    f"[HYBRID] {completed + failed}/{len(pending_indexes)} "
                    f"photo={photo_id} "
                    f"status={'DONE' if ok else 'FAILED'}"
                )

    final_run = finish_run(hybrid_run_id)

    elapsed = time.perf_counter() - started

    print()
    print("=" * 80)
    print("HYBRID FINISHED")
    print("=" * 80)
    print(f"run_id={final_run.hybrid_run_id}")
    print(f"status={final_run.status}")
    print(f"processed={completed + failed}")
    print(f"completed={final_run.completed_count}")
    print(f"failed={final_run.failed_count}")
    print(f"elapsed={elapsed:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Hybrid recognition from PostgreSQL DINO results."
    )
    parser.add_argument(
        "hybrid_run_id",
        type=int,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    run(
        hybrid_run_id=args.hybrid_run_id,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()

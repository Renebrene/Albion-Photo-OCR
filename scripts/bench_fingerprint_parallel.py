"""
Measure fingerprint-build throughput against parallelism.

Builds fingerprints from real address folders into a throwaway SCENE_DATA root.
Nothing touches the working repository: fingerprints land in a temp dir and the
registry (PostgreSQL) is never called - this goes straight to
FingerprintManager.create(), not through build_fingerprint().

    python scripts/bench_fingerprint_parallel.py --parallel 1,2,3,4,6 --builds 6
    python scripts/bench_fingerprint_parallel.py --parallel 1 --device cpu

For each parallelism N it runs `builds` builds over a pool of N processes, each
with cores//N torch threads and cores//N descriptor workers, and reports per
build: total wall time, model load, embedding phase and descriptor phase (the
phases come from the builder's own progress callback).
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# app.* imports stay inside the functions: the child processes set SCENE_DATA /
# SCENE_DEVICE / thread counts before app.core.config is imported.
APP_IMPORTED = False

# One embedder per process when --cache-embedder is on: production reloads
# DINOv2 for every FINGERPRINT_BUILD job, this shows what caching it buys.
_EMBEDDERS: dict[str, object] = {}


def _prepare(threads: int, device: str) -> None:
    global APP_IMPORTED

    os.environ["SCENE_DEVICE"] = device
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["MKL_NUM_THREADS"] = str(threads)

    import torch

    torch.set_num_threads(threads)
    APP_IMPORTED = True


def _build(task: dict) -> dict:
    folder = task["folder"]
    fp_id = task["id"]
    max_photos = task["max_photos"]
    threads = task["threads"]
    device = task["device"]

    _prepare(threads, device)

    from app.core.config import settings
    from app.core.embedder import SceneEmbedder
    from app.core.fingerprint import FingerprintManager

    start = time.perf_counter()

    embedder = _EMBEDDERS.get(device) if task.get("cache") else None

    if embedder is None:
        embedder = SceneEmbedder(settings)
        if task.get("cache"):
            _EMBEDDERS[device] = embedder

    model_loaded = time.perf_counter()

    stages: dict[str, list[float]] = {}

    def progress(done, total, stage):
        stages.setdefault(stage, [time.perf_counter(), time.perf_counter()])
        stages[stage][1] = time.perf_counter()

    manager = FingerprintManager(
        settings,
        embedder,
        descriptor_workers=threads,
    )

    manager.create(
        fp_id,
        Path(folder),
        embedder,
        max_photos=max_photos,
        replace=True,
        progress=progress,
    )

    end = time.perf_counter()

    phases = {name: round(span[1] - span[0], 2) for name, span in stages.items()}

    return {
        "id": fp_id,
        "pid": os.getpid(),
        "total": round(end - start, 2),
        "model_load": round(model_loaded - start, 2),
        "phases": phases,
    }


def _folders(root: Path, count: int) -> list[Path]:
    candidates = sorted(
        path for path in (root / "data" / "input").iterdir() if path.is_dir()
    )
    if len(candidates) < count:
        raise SystemExit(
            f"нужно {count} папок адресов, найдено {len(candidates)}"
        )
    return candidates[:count]


def run_config(
    parallel: int,
    builds: int,
    folders: list[Path],
    max_photos: int,
    device: str,
    cores: int,
    cache: bool = False,
) -> dict:
    threads = max(1, cores // parallel)

    tasks = [
        {
            "folder": str(folders[index % len(folders)]),
            "id": f"bench_p{parallel}_{index}_v33",
            "max_photos": max_photos,
            "threads": threads,
            "device": device,
            "cache": cache,
        }
        for index in range(builds)
    ]

    wall_start = time.perf_counter()

    context = mp.get_context("spawn")

    with context.Pool(processes=parallel) as pool:
        results = pool.map(_build, tasks)

    wall = time.perf_counter() - wall_start

    totals = [item["total"] for item in results]
    loads = [item["model_load"] for item in results]

    return {
        "parallel": parallel,
        "threads_each": threads,
        "device": device,
        "cached_embedder": cache,
        "builds": builds,
        "wall_sec": round(wall, 2),
        "per_build_median": round(statistics.median(totals), 2),
        "per_build_min": round(min(totals), 2),
        "per_build_max": round(max(totals), 2),
        "model_load_median": round(statistics.median(loads), 2),
        "sec_per_build_throughput": round(wall / builds, 2),
        "builds_per_hour": round(builds / wall * 3600, 1),
        "phases": {
            item["id"]: item["phases"] for item in results
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="fingerprint build parallelism bench")
    parser.add_argument(
        "--parallel",
        default="1,2,3,4,6",
        help="comma separated parallelism values to test",
    )
    parser.add_argument("--builds", type=int, default=6, help="builds per config")
    parser.add_argument("--photos", type=int, default=25, help="photos per build")
    parser.add_argument(
        "--device",
        default=os.getenv("SCENE_DEVICE", "cuda" if _cuda() else "cpu"),
        help="torch device for the embedder",
    )
    parser.add_argument(
        "--cache-embedder",
        action="store_true",
        help="load DINOv2 once per process instead of once per job",
    )
    parser.add_argument("--out", default=None, help="write the summary as JSON here")
    args = parser.parse_args()

    cores = os.cpu_count() or 1
    folders = _folders(ROOT, max(int(value) for value in args.parallel.split(",")))

    scratch = Path(tempfile.mkdtemp(prefix="scene_bench_", dir="/tmp"))
    os.environ["SCENE_DATA"] = str(scratch)

    print(
        f"cores={cores} builds={args.builds} photos={args.photos} "
        f"device={args.device} scratch={scratch}",
        flush=True,
    )

    summary = []

    try:
        for value in args.parallel.split(","):
            parallel = int(value.strip())
            print(f"\n=== parallel={parallel} ===", flush=True)
            result = run_config(
                parallel,
                args.builds,
                folders,
                args.photos,
                args.device,
                cores,
                cache=args.cache_embedder,
            )
            summary.append(result)
            print(json.dumps({k: v for k, v in result.items() if k != "phases"},
                             ensure_ascii=False), flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    print("\n==== SUMMARY ====", flush=True)

    for item in summary:
        print(
            f"parallel={item['parallel']:<2} threads={item['threads_each']:<3} "
            f"wall={item['wall_sec']:>7}s  per-build median={item['per_build_median']:>7}s  "
            f"{item['builds_per_hour']:>6} builds/h",
            flush=True,
        )

    if args.out:
        Path(args.out).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nwritten: {args.out}", flush=True)


def _cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    sys.exit(main())

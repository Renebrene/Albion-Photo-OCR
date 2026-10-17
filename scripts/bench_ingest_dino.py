"""Замер ресурсов INGEST и DINO/HYBRID.

Что измеряется:
  * INGEST: pipeline.run (hash + decode + EXIF) при разном числе процессов;
  * DINO: эмбеддинги DINOv2 на CPU при разном batch_size и числе torch-потоков;
  * дескрипторы DINO при разном числе потоков;
  * HYBRID: пересчёт вердиктов по уже сохранённым кандидатам (только чтение);
  * реальные длительности последних DINO/HYBRID-прогонов из БД.

Ничего не пишет в БД и не изменяет исходники. Результаты:
data/output/bench_pipeline/bench_YYYYmmdd_HHMMSS.{json,md}.

    .venv/bin/python scripts/bench_ingest_dino.py --photos 24
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import psutil

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data/output/bench_pipeline"
sys.path.insert(0, str(REPO))

IMAGE_SUFFIXES = {".jpg", ".jpeg"}


class ResourceMonitor(threading.Thread):
    """Sample RSS and CPU time of the process tree."""

    def __init__(self, interval: float = 0.1):
        super().__init__(daemon=True)
        self.interval = interval
        self.stop_event = threading.Event()
        self.peak_rss = 0
        self.cpu_by_pid: dict[int, list[float]] = {}
        self.root = psutil.Process(os.getpid())

    def _sample(self) -> None:
        try:
            procs = [self.root, *self.root.children(recursive=True)]
        except psutil.Error:
            procs = [self.root]

        rss = 0

        for proc in procs:
            try:
                rss += proc.memory_info().rss
                times = proc.cpu_times()
                cpu = float(times.user) + float(times.system)
            except psutil.Error:
                continue

            # First sample is the baseline; last sample is the total. This
            # works for both threads of one process and ProcessPool children
            # (os.times() only counts reaped children, so it misses workers
            # that live for the whole sweep).
            entry = self.cpu_by_pid.get(proc.pid)

            if entry is None:
                self.cpu_by_pid[proc.pid] = [cpu, cpu]
            else:
                entry[1] = cpu

        self.peak_rss = max(self.peak_rss, rss)

    def run(self) -> None:
        while not self.stop_event.is_set():
            self._sample()
            self.stop_event.wait(self.interval)

    def stop(self) -> tuple[int, float]:
        self.stop_event.set()
        self.join(timeout=2)

        # A final sample catches work done right before the call returned.
        # The root process is always sampled, even if stop() raced the loop.
        self._sample()

        cpu = sum(max(0.0, last - first) for first, last in self.cpu_by_pid.values())

        return self.peak_rss, cpu


def measure(callable_):
    """Run callable_, return (result, wall, cpu_seconds, peak_rss)."""

    monitor = ResourceMonitor()
    started = time.perf_counter()

    monitor.start()

    try:
        result = callable_()
    finally:
        wall = time.perf_counter() - started
        peak, cpu = monitor.stop()

    return result, round(wall, 3), round(cpu, 3), int(peak)


def pick_photos(limit: int) -> list[Path]:
    root = REPO / "data/input"

    if not root.is_dir():
        raise SystemExit("data/input is missing")

    best: list[Path] = []

    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        photos = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
        )

        if len(photos) > len(best):
            best = photos

    if not best:
        raise SystemExit("no photos found under data/input")

    return best[:limit]


def symlink_dir(photos: list[Path]) -> Path:
    target = Path(tempfile.mkdtemp(prefix="photobase-bench-"))

    for index, photo in enumerate(photos):
        (target / f"{index:03d}_{photo.name}").symlink_to(photo)

    return target


def bench_ingest(photos: list[Path], workers: list[int]) -> list[dict]:
    from app.ingest.pipeline import run as ingest_run

    folder = symlink_dir(photos)
    rows = []

    try:
        # Warm-up: page cache and imports are not part of the sweep.
        ingest_run(folder, 1, skip_known=None)

        for count in workers:
            _, wall, cpu, rss = measure(
                lambda count=count: ingest_run(folder, count, skip_known=None)
            )

            rows.append(
                {
                    "workers": count,
                    "photos": len(photos),
                    "seconds": wall,
                    "photos_per_second": round(len(photos) / wall, 2),
                    "cpu_seconds": cpu,
                    "cpu_of_one_core_percent": round(cpu / wall * 100, 1),
                    "machine_percent": round(
                        cpu / wall / (os.cpu_count() or 1) * 100, 1
                    ),
                    "peak_rss_mb": round(rss / 1024**2, 1),
                }
            )
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    return rows


def cpu_settings():
    from app.core.config import settings

    return replace(settings, device="cpu")


def bench_embedding(photos: list[Path], batches: list[int],
                    threads: list[int], base_threads: int) -> list[dict]:
    import torch
    from PIL import Image
    from app.core.embedder import SceneEmbedder

    settings = cpu_settings()
    started = time.perf_counter()
    embedder = SceneEmbedder(settings)
    load_seconds = round(time.perf_counter() - started, 2)

    images = []
    for photo in photos:
        with Image.open(photo) as image:
            if getattr(image, "n_frames", 1) > 1:
                image.seek(0)
            images.append(image.convert("RGB"))

    rows = []

    def run_one(batch_size: int, thread_count: int) -> dict:
        torch.set_num_threads(thread_count)

        def call():
            return embedder.embed_images(images, batch_size=batch_size)

        _, wall, cpu, rss = measure(call)

        return {
            "batch_size": batch_size,
            "torch_threads": thread_count,
            "photos": len(images),
            "seconds": wall,
            "photos_per_second": round(len(images) / wall, 2),
            "cpu_seconds": cpu,
            "cpu_of_one_core_percent": round(cpu / wall * 100, 1),
            "machine_percent": round(
                cpu / wall / (os.cpu_count() or 1) * 100, 1
            ),
            "peak_rss_mb": round(rss / 1024**2, 1),
        }

    for batch in batches:
        rows.append(run_one(batch, base_threads))

    for thread_count in threads:
        rows.append(run_one(max(batches), thread_count))

    torch.set_num_threads(os.cpu_count() or 1)

    return rows, load_seconds


def bench_recognition(photos: list[Path], batches: list[int],
                      thread_workers: list[int]) -> tuple[list[dict], float]:
    """
    The real DINO path: decode → DINOv2 → descriptors → rank vs 20 fingerprints.

    Production runs ``DinoRunner.run_batch``; with SCENE_DINO_BATCH>1 it uses
    ``recognize_many`` (one forward per chunk), otherwise ``recognize_one``
    from several threads.
    """

    import torch
    from app.dino.database import DinoWorkItem
    from app.dino.runner import DinoRunner

    cpu_count = os.cpu_count() or 1

    torch.set_num_threads(cpu_count)
    started = time.perf_counter()
    runner = DinoRunner(workers=1)
    load_seconds = round(time.perf_counter() - started, 2)

    items = [
        DinoWorkItem(
            run_id=index + 1,
            photo_id=f"PH_bench_{index:03d}",
            source_path=str(photo),
            run_type="NORMAL",
        )
        for index, photo in enumerate(photos)
    ]

    # Warm-up: model/fingerprints are already loaded; this only fills caches.
    runner.recognize_one(items[0])

    rows = []

    def record(mode: str, workers: int, batch_size: int, thread_count: int,
               call) -> None:
        _, wall, cpu, rss = measure(call)
        rows.append(
            {
                "mode": mode,
                "workers": workers,
                "batch_size": batch_size,
                "torch_threads": thread_count,
                "photos": len(items),
                "seconds": wall,
                "photos_per_second": round(len(items) / wall, 2),
                "cpu_seconds": cpu,
                "cpu_of_one_core_percent": round(cpu / wall * 100, 1),
                "machine_percent": round(cpu / wall / cpu_count * 100, 1),
                "peak_rss_mb": round(rss / 1024**2, 1),
            }
        )

    def batched(batch_size: int):
        def call():
            results = []
            for start in range(0, len(items), batch_size):
                results.extend(
                    runner.recognize_many(items[start:start + batch_size])
                )
            return results

        return call

    def threaded(workers: int, thread_count: int):
        torch.set_num_threads(thread_count)

        def call():
            with ThreadPoolExecutor(max_workers=workers) as pool:
                return list(pool.map(runner.recognize_one, items))

        return call

    # 1. One worker, one forward per chunk (the recommended shape).
    for batch in batches:
        torch.set_num_threads(cpu_count)
        record("batch", 1, batch, cpu_count, batched(batch))

    # 2. Several threads, each embedding one image; torch keeps all cores.
    for workers in thread_workers:
        torch.set_num_threads(cpu_count)
        record("threads", workers, 1, cpu_count, threaded(workers, cpu_count))

    # 3. Same threads, but torch is pinned so workers do not oversubscribe.
    for workers in thread_workers:
        thread_count = max(1, cpu_count // workers)
        record(
            "threads_pinned", workers, 1, thread_count,
            threaded(workers, thread_count),
        )

    torch.set_num_threads(cpu_count)

    return rows, load_seconds


def bench_descriptors(photos: list[Path], workers: list[int]) -> list[dict]:
    from app.core.scene_analyzer import CompactDescriptor

    rows = []

    for count in workers:
        def call(count=count):
            with ThreadPoolExecutor(max_workers=count) as pool:
                return list(pool.map(CompactDescriptor.all, photos))

        _, wall, cpu, rss = measure(call)

        rows.append(
            {
                "workers": count,
                "photos": len(photos),
                "seconds": wall,
                "photos_per_second": round(len(photos) / wall, 2),
                "cpu_seconds": cpu,
                "cpu_of_one_core_percent": round(cpu / wall * 100, 1),
                "machine_percent": round(
                    cpu / wall / (os.cpu_count() or 1) * 100, 1
                ),
                "peak_rss_mb": round(rss / 1024**2, 1),
            }
        )

    return rows


def bench_hybrid(workers: list[int]) -> list[dict]:
    from app.hybrid import database as hybrid_db
    from app.hybrid.runner import hybrid_one
    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT hybrid_run_id FROM public.hybrid_runs "
                "WHERE status='DONE' ORDER BY hybrid_run_id DESC LIMIT 1"
            )
            row = cur.fetchone()

    if row is None:
        return []

    run_id = int(row[0])
    items = hybrid_db.get_run_items(run_id)

    if not items:
        return []

    rows = []

    for count in workers:
        def call(count=count):
            with ThreadPoolExecutor(max_workers=count) as pool:
                futures = [
                    pool.submit(hybrid_one, items, index)
                    for index in range(len(items))
                ]
                return [future.result() for future in futures]

        _, wall, cpu, rss = measure(call)

        rows.append(
            {
                "workers": count,
                "hybrid_run_id": run_id,
                "photos": len(items),
                "seconds": wall,
                "photos_per_second": round(len(items) / wall, 2),
                "microseconds_per_photo": round(wall / len(items) * 1e6, 1),
                "cpu_of_one_core_percent": round(cpu / wall * 100, 1),
                "peak_rss_mb": round(rss / 1024**2, 1),
            }
        )

    return rows


def historical_runs() -> dict:
    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT batch_id, total_count, started_at, finished_at,
                       EXTRACT(EPOCH FROM (finished_at - started_at)) AS seconds
                FROM public.dino_batches
                WHERE status = 'DONE' AND started_at IS NOT NULL
                ORDER BY batch_id DESC LIMIT 5
                """
            )
            dino = [
                {
                    "batch_id": int(r[0]),
                    "photos": int(r[1]),
                    "seconds": round(float(r[4] or 0), 1),
                    "seconds_per_photo": round(float(r[4] or 0) / max(1, r[1]), 2),
                }
                for r in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT hybrid_run_id, total_count, started_at, finished_at,
                       EXTRACT(EPOCH FROM (finished_at - started_at)) AS seconds
                FROM public.hybrid_runs
                WHERE status = 'DONE' AND started_at IS NOT NULL
                ORDER BY hybrid_run_id DESC LIMIT 5
                """
            )
            hybrid = [
                {
                    "hybrid_run_id": int(r[0]),
                    "photos": int(r[1]),
                    "seconds": round(float(r[4] or 0), 1),
                    "seconds_per_photo": round(float(r[4] or 0) / max(1, r[1]), 2),
                }
                for r in cur.fetchall()
            ]

    return {"dino_batches": dino, "hybrid_runs": hybrid}


def markdown(result: dict) -> str:
    lines = [
        "# Ресурсы INGEST и DINO/HYBRID",
        "",
        f"Дата: {time.strftime('%Y-%m-%d %H:%M')} · CPU: {os.cpu_count()} логических",
        f"Фото в замере: {result['photos']}",
        "",
        "## INGEST (hash + decode + EXIF)",
        "",
        "| Воркеров | Секунд | Фото/с | CPU-секунд | 1 ядро, % | Машина, % | Пик RSS, МБ |",
        "|---|---|---|---|---|---|---|",
    ]

    for row in result["ingest"]:
        lines.append(
            f"| {row['workers']} | {row['seconds']} | {row['photos_per_second']} | "
            f"{row['cpu_seconds']} | {row['cpu_of_one_core_percent']} | "
            f"{row['machine_percent']} | {row['peak_rss_mb']} |"
        )

    lines += [
        "",
        f"## DINO-эмбеддинги (CPU, загрузка модели {result['embedding_load_seconds']} с)",
        "",
        "| batch | потоков | Секунд | Фото/с | 1 ядро, % | Машина, % | Пик RSS, МБ |",
        "|---|---|---|---|---|---|---|",
    ]

    for row in result["embedding"]:
        lines.append(
            f"| {row['batch_size']} | {row['torch_threads']} | {row['seconds']} | "
            f"{row['photos_per_second']} | {row['cpu_of_one_core_percent']} | "
            f"{row['machine_percent']} | {row['peak_rss_mb']} |"
        )

    lines += [
        "",
        "## Дескрипторы DINO (CompactDescriptor, потоки)",
        "",
        "| Потоков | Секунд | Фото/с | 1 ядро, % | Пик RSS, МБ |",
        "|---|---|---|---|---|",
    ]

    for row in result["descriptors"]:
        lines.append(
            f"| {row['workers']} | {row['seconds']} | {row['photos_per_second']} | "
            f"{row['cpu_of_one_core_percent']} | {row['peak_rss_mb']} |"
        )

    lines += [
        "",
        "## DINO: реальный путь фото (decode + embedding + дескрипторы + ranking)",
        "",
        f"Загрузка модели и 20 слепков: {result['recognition_load_seconds']} с",
        "",
        "| Режим | Потоков | batch | torch-потоков | Секунд | Фото/с | 1 ядро, % | Машина, % | Пик RSS, МБ |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for row in result["recognition"]:
        lines.append(
            f"| {row['mode']} | {row['workers']} | {row['batch_size']} | "
            f"{row['torch_threads']} | {row['seconds']} | "
            f"{row['photos_per_second']} | {row['cpu_of_one_core_percent']} | "
            f"{row['machine_percent']} | {row['peak_rss_mb']} |"
        )

    if result["hybrid"]:
        lines += [
            "",
            "## HYBRID (пересчёт по сохранённым кандидатам)",
            "",
            "| Потоков | Фото | Секунд | мкс/фото | 1 ядро, % |",
            "|---|---|---|---|---|",
        ]

        for row in result["hybrid"]:
            lines.append(
                f"| {row['workers']} | {row['photos']} | {row['seconds']} | "
                f"{row['microseconds_per_photo']} | {row['cpu_of_one_core_percent']} |"
            )

    lines += [
        "",
        "## Реальные длительности из БД",
        "",
        "| DINO batch | Фото | Секунд | С/фото |",
        "|---|---|---|---|",
    ]

    for row in result["historical"]["dino_batches"]:
        lines.append(
            f"| {row['batch_id']} | {row['photos']} | {row['seconds']} | "
            f"{row['seconds_per_photo']} |"
        )

    lines += ["", "| HYBRID run | Фото | Секунд | С/фото |", "|---|---|---|---|"]

    for row in result["historical"]["hybrid_runs"]:
        lines.append(
            f"| {row['hybrid_run_id']} | {row['photos']} | {row['seconds']} | "
            f"{row['seconds_per_photo']} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--photos", type=int, default=24)
    parser.add_argument("--base-threads", type=int, default=min(6, os.cpu_count() or 1))
    args = parser.parse_args()

    photos = pick_photos(max(4, args.photos))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"photos: {len(photos)} · CPU: {os.cpu_count()}", flush=True)

    print("INGEST...", flush=True)
    ingest = bench_ingest(photos, [1, 2, 4, 6, 8, 12])

    print("DINO embeddings...", flush=True)
    embedding, load_seconds = bench_embedding(
        photos, [1, 2, 4, 8], [1, 2, 4, 6, 12], args.base_threads
    )

    print("DINO descriptors...", flush=True)
    descriptors = bench_descriptors(photos, [1, 2, 4, 6, 12])

    print("DINO recognition (real path)...", flush=True)
    recognition, recognition_load = bench_recognition(
        photos, [1, 2, 4, 8], [2, 4, 6]
    )

    print("HYBRID...", flush=True)
    hybrid = bench_hybrid([1, 2, 4, 6, 12])

    result = {
        "photos": len(photos),
        "cpu_count": os.cpu_count(),
        "ingest": ingest,
        "embedding": embedding,
        "embedding_load_seconds": load_seconds,
        "descriptors": descriptors,
        "recognition": recognition,
        "recognition_load_seconds": recognition_load,
        "hybrid": hybrid,
        "historical": historical_runs(),
    }

    stamp = time.strftime("%Y%m%d_%H%M%S")
    (OUT_DIR / f"bench_{stamp}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1)
    )
    report = markdown(result)
    (OUT_DIR / f"bench_{stamp}.md").write_text(report)

    print("\n" + report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

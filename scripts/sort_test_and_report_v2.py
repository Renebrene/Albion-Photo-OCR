#!/usr/bin/env python3

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from collections import Counter

import psutil


PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"
OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"

FINGERPRINTS = [
    f"{i}_v33"
    for i in range(78, 96)
]

RECOGNITION_JSON = OUTPUT_DIR / "recognition.json"
REPORT_CSV = OUTPUT_DIR / "report.csv"
REPORT_JSON = OUTPUT_DIR / "report.json"
STATISTICS_JSON = OUTPUT_DIR / "statistics.json"


def gpu_stats():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )

        line = result.stdout.strip().splitlines()[0]
        parts = [x.strip() for x in line.split(",")]

        return {
            "gpu_name": parts[0],
            "gpu_utilization_percent": float(parts[1]),
            "gpu_memory_used_mb": float(parts[2]),
            "gpu_memory_total_mb": float(parts[3]),
        }

    except Exception:
        return {
            "gpu_name": None,
            "gpu_utilization_percent": None,
            "gpu_memory_used_mb": None,
            "gpu_memory_total_mb": None,
        }


def find_json(text):
    """
    Find the actual JSON array, ignoring messages such as:
        [SceneEmbedder]
        [Recognizer]
    """

    decoder = json.JSONDecoder()

    for i, ch in enumerate(text):
        if ch != "[":
            continue

        candidate = text[i:]

        try:
            obj, end = decoder.raw_decode(candidate)

            if isinstance(obj, list):
                return obj

        except json.JSONDecodeError:
            pass

    raise RuntimeError("Не удалось найти JSON-массив в выводе recognition")


def run_recognition():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fp_arg = ",".join(FINGERPRINTS)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(INPUT_DIR),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("RUNNING RECOGNITION")
    print("=" * 80)

    print("Input:", INPUT_DIR)
    print("Fingerprints:", ", ".join(FINGERPRINTS))
    print()

    start = time.perf_counter()

    process = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - start

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
        raise RuntimeError(
            f"recognize завершился с кодом {process.returncode}"
        )

    combined = process.stdout + "\n" + process.stderr

    data = find_json(combined)

    RECOGNITION_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return data, elapsed


def copy_images(data):
    print()
    print("=" * 80)
    print("SORTING")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    counters = Counter()

    for item in data:
        source = Path(item["file"])

        # Главный принцип:
        # ВСЕГДА используем best_id = первый кандидат.
        assigned_id = item.get("best_id")

        if not assigned_id:
            continue

        destination_dir = OUTPUT_DIR / assigned_id
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / source.name

        shutil.copy2(source, destination)

        counters[assigned_id] += 1

        candidates = item.get("candidates", [])

        row = {
            "file": str(source),
            "filename": source.name,
            "assigned_id": assigned_id,
            "score": item.get("score"),
            "second_score": item.get("second_score"),
            "margin": item.get("margin"),
            "confidence": item.get("confidence"),
            "status": item.get("status"),
            "best_image": item.get("best_image"),
            "best_image_score": item.get("best_image_score"),
            "global": None,
            "environment": None,
            "color": None,
            "spatial": None,
            "candidate_2": None,
            "candidate_2_score": None,
            "candidate_3": None,
            "candidate_3_score": None,
            "candidate_4": None,
            "candidate_4_score": None,
            "candidate_5": None,
            "candidate_5_score": None,
        }

        if candidates:
            c = candidates[0]

            row["global"] = c.get("global")
            row["environment"] = c.get("environment")
            row["color"] = c.get("color")
            row["spatial"] = c.get("spatial")

        for n in range(1, min(5, len(candidates))):
            c = candidates[n]

            row[f"candidate_{n+1}"] = c.get("id")
            row[f"candidate_{n+1}_score"] = c.get("score")

        rows.append(row)

    print()

    for k in sorted(counters, key=lambda x: int(x.split("_")[0])):
        print(f"{k:10s} {counters[k]:4d}")

    return rows, counters


def write_reports(rows, counters, recognition_time):
    fields = [
        "file",
        "filename",
        "assigned_id",
        "score",
        "second_score",
        "margin",
        "confidence",
        "status",
        "best_image",
        "best_image_score",
        "global",
        "environment",
        "color",
        "spatial",
        "candidate_2",
        "candidate_2_score",
        "candidate_3",
        "candidate_3_score",
        "candidate_4",
        "candidate_4_score",
        "candidate_5",
        "candidate_5_score",
    ]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    scores = [
        float(x["score"])
        for x in rows
        if x["score"] is not None
    ]

    margins = [
        float(x["margin"])
        for x in rows
        if x["margin"] is not None
    ]

    status_counter = Counter(
        x["status"]
        for x in rows
        if x["status"]
    )

    confidence_counter = Counter(
        x["confidence"]
        for x in rows
        if x["confidence"]
    )

    process = psutil.Process(os.getpid())

    stats = {
        "total_images": len(rows),

        "recognition_time_seconds": recognition_time,

        "images_per_second":
            len(rows) / recognition_time
            if recognition_time > 0 else None,

        "milliseconds_per_image":
            recognition_time * 1000 / len(rows)
            if rows else None,

        "score": {
            "min": min(scores) if scores else None,
            "mean": sum(scores) / len(scores) if scores else None,
            "max": max(scores) if scores else None,
        },

        "margin": {
            "min": min(margins) if margins else None,
            "mean": sum(margins) / len(margins) if margins else None,
            "max": max(margins) if margins else None,
        },

        "status": dict(status_counter),
        "confidence": dict(confidence_counter),

        "assigned": dict(counters),

        "cpu": {
            "logical_cpus": psutil.cpu_count(),
            "process_cpu_percent": process.cpu_percent(interval=0.5),
        },

        "ram": {
            "total_mb":
                psutil.virtual_memory().total / 1024 / 1024,

            "used_mb":
                psutil.virtual_memory().used / 1024 / 1024,

            "available_mb":
                psutil.virtual_memory().available / 1024 / 1024,

            "process_rss_mb":
                process.memory_info().rss / 1024 / 1024,
        },

        "gpu": gpu_stats(),
    }

    REPORT_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    STATISTICS_JSON.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return stats


def main():
    print()
    print("=" * 80)
    print("SCENE FINGERPRINT TEST SORTER V2")
    print("=" * 80)

    if not INPUT_DIR.exists():
        raise RuntimeError(f"Нет папки: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start_total = time.perf_counter()

    data, recognition_time = run_recognition()

    rows, counters = copy_images(data)

    stats = write_reports(
        rows,
        counters,
        recognition_time,
    )

    total_time = time.perf_counter() - start_total

    stats["total_wall_time_seconds"] = total_time

    STATISTICS_JSON.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)

    print(f"Images:             {stats['total_images']}")
    print(f"Recognition time:   {recognition_time:.2f} sec")
    print(f"Total time:         {total_time:.2f} sec")
    print(
        f"Speed:              "
        f"{stats['images_per_second']:.2f} images/sec"
    )
    print(
        f"Per image:          "
        f"{stats['milliseconds_per_image']:.1f} ms"
    )

    print()
    print("SCORE")
    print(f"  min:              {stats['score']['min']:.4f}")
    print(f"  mean:             {stats['score']['mean']:.4f}")
    print(f"  max:              {stats['score']['max']:.4f}")

    print()
    print("MARGIN")
    print(f"  min:              {stats['margin']['min']:.4f}")
    print(f"  mean:             {stats['margin']['mean']:.4f}")
    print(f"  max:              {stats['margin']['max']:.4f}")

    print()
    print("RAM")
    print(
        f"  process RSS:      "
        f"{stats['ram']['process_rss_mb']:.1f} MB"
    )

    print()
    print("GPU")
    print(f"  name:             {stats['gpu']['gpu_name']}")
    print(
        f"  utilization:      "
        f"{stats['gpu']['gpu_utilization_percent']}%"
    )
    print(
        f"  memory:           "
        f"{stats['gpu']['gpu_memory_used_mb']} / "
        f"{stats['gpu']['gpu_memory_total_mb']} MB"
    )

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print("Sorted:", OUTPUT_DIR)
    print("CSV:   ", REPORT_CSV)
    print("JSON:  ", REPORT_JSON)
    print("Stats: ", STATISTICS_JSON)


if __name__ == "__main__":
    main()

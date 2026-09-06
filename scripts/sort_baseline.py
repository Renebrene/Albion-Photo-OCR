#!/usr/bin/env python3

import csv
import json
import shutil
import time
from collections import Counter
from pathlib import Path

BASE = Path("data/output/baseline_v33")
SRC = BASE / "recognition.json"
OUT = BASE / "sorted"
REPORT_CSV = BASE / "report.csv"
REPORT_JSON = BASE / "report.json"

FINGERPRINTS = [
    "78_v33", "79_v33", "80_v33", "81_v33", "82_v33",
    "83_v33", "84_v33", "85_v33", "86_v33", "87_v33",
    "88_v33", "89_v33", "90_v33", "91_v33", "92_v33",
    "93_v33", "94_v33", "95_v33",
]

def main():
    t0 = time.perf_counter()

    data = json.loads(SRC.read_text(encoding="utf-8"))

    print("=" * 80)
    print("SORT BASELINE V33")
    print("=" * 80)
    print("INPUT:", len(data))

    # Создаём папки только для реально встречающихся кандидатов
    OUT.mkdir(parents=True, exist_ok=True)

    for fp in FINGERPRINTS:
        (OUT / fp.replace("_v33", "")).mkdir(exist_ok=True)

    rows = []
    counts = Counter()

    for item in data:
        src = Path(item["file"])

        # ГЛАВНОЕ:
        # всегда используем ПЕРВОГО кандидата
        best_id = item["best_id"]
        folder = best_id.replace("_v33", "")

        if folder not in FINGERPRINTS:
            # Защита от неожиданных ID
            folder = best_id

        dst_dir = OUT / folder
        dst_dir.mkdir(parents=True, exist_ok=True)

        dst = dst_dir / src.name

        # Не перезаписываем файл при совпадении имени
        if dst.exists():
            stem = src.stem
            suffix = src.suffix
            n = 2

            while True:
                candidate = dst_dir / f"{stem}__{n}{suffix}"
                if not candidate.exists():
                    dst = candidate
                    break
                n += 1

        shutil.copy2(src, dst)

        counts[best_id] += 1

        rows.append({
            "file": str(src),
            "filename": src.name,
            "assigned_id": best_id,
            "score": item.get("score"),
            "second_id": (
                item["candidates"][1]["id"]
                if len(item.get("candidates", [])) > 1
                else ""
            ),
            "second_score": item.get("second_score"),
            "margin": item.get("margin"),
            "status": item.get("status"),
            "confidence": item.get("confidence"),
            "best_image": item.get("best_image"),
            "best_image_score": item.get("best_image_score"),
            "global": (
                item["candidates"][0].get("global")
                if item.get("candidates")
                else ""
            ),
            "environment": (
                item["candidates"][0].get("environment")
                if item.get("candidates")
                else ""
            ),
            "color": (
                item["candidates"][0].get("color")
                if item.get("candidates")
                else ""
            ),
            "spatial": (
                item["candidates"][0].get("spatial")
                if item.get("candidates")
                else ""
            ),
        })

    # CSV
    fields = list(rows[0].keys())

    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    elapsed = time.perf_counter() - t0

    # JSON report
    report = {
        "total": len(data),
        "counts": dict(sorted(counts.items())),
        "elapsed_sort_seconds": elapsed,
        "source": str(SRC),
        "output": str(OUT),
        "rule": "ALWAYS_FIRST_CANDIDATE",
    }

    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for fp in FINGERPRINTS:
        print(f"{fp:10s} {counts[fp]:4d}")

    print("-" * 80)
    print(f"TOTAL      {sum(counts.values()):4d}")

    print()
    print("OUTPUT:")
    print("  sorted :", OUT)
    print("  CSV    :", REPORT_CSV)
    print("  JSON   :", REPORT_JSON)
    print()
    print(f"TIME: {elapsed:.3f} sec")


if __name__ == "__main__":
    main()

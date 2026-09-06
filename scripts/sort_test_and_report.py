#!/usr/bin/env python3

import csv
import json
import shutil
import time
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

INPUT_DIR = Path("data/input/test")
RECOGNITION_JSON = Path("/tmp/recognize_test.json")

OUTPUT_DIR = Path("data/output_test")
REPORT_DIR = Path("data/reports")

REPORT_CSV = REPORT_DIR / "test_recognition.csv"
REPORT_JSON = REPORT_DIR / "test_recognition.json"
SUMMARY_JSON = REPORT_DIR / "test_summary.json"


def load_recognition():
    text = RECOGNITION_JSON.read_text(encoding="utf-8")

    # В stdout попадают служебные сообщения:
    # [SceneEmbedder] ...
    # [Recognizer] ...
    #
    # Поэтому ищем именно начало JSON-массива:
    # [
    #   {
    #       "file": ...
    #
    lines = text.splitlines()

    start = None

    for i, line in enumerate(lines):
        if line.strip() == "[":
            # Проверяем, что дальше действительно начинается JSON
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip().startswith("{"):
                    start = i
                    break

        if start is not None:
            break

    if start is None:
        raise RuntimeError(
            "JSON array not found in recognition output"
        )

    json_text = "\n".join(lines[start:])

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print("JSON parsing error:")
        print(e)
        print()
        print("JSON starts with:")
        print(json_text[:1000])
        raise


def clean_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def main():

    started = time.perf_counter()

    data = load_recognition()

    clean_output()

    print("=" * 80)
    print("SORT TEST BY FIRST CANDIDATE")
    print("=" * 80)

    print(f"INPUT:       {INPUT_DIR}")
    print(f"FILES:       {len(data)}")
    print(f"OUTPUT:      {OUTPUT_DIR}")
    print()

    rows = []

    distribution = Counter()
    score_by_id = defaultdict(list)
    margin_by_id = defaultdict(list)

    status_counter = Counter()
    confidence_counter = Counter()

    copied = 0

    for i, item in enumerate(data, 1):

        src = Path(item["file"])

        # Первый кандидат — именно он определяет адрес
        best_id = item["best_id"]

        # Убираем суффикс _v33
        if best_id.endswith("_v33"):
            address = best_id[:-4]
        else:
            address = best_id

        dst_dir = OUTPUT_DIR / address
        dst_dir.mkdir(parents=True, exist_ok=True)

        dst = dst_dir / src.name

        # Если одинаковые имена вдруг встретились повторно
        if dst.exists():
            stem = src.stem
            suffix = src.suffix

            n = 2

            while True:
                dst = dst_dir / f"{stem}__{n}{suffix}"

                if not dst.exists():
                    break

                n += 1

        shutil.copy2(src, dst)
        copied += 1

        candidates = item.get("candidates", [])

        sub_info = None

        # На будущее сохраняем информацию о локальных кандидатах,
        # если recognize уже начал их отдавать.
        if item.get("subfingerprint"):
            sub_info = item["subfingerprint"]

        row = {
            "file": str(src),
            "filename": src.name,
            "assigned_id": address,
            "fingerprint": best_id,

            "score": float(item.get("score", 0)),
            "second_score": float(item.get("second_score", 0)),
            "margin": float(item.get("margin", 0)),

            "confidence": item.get("confidence", ""),
            "status": item.get("status", ""),

            "best_image": item.get("best_image", ""),
            "best_image_score": float(
                item.get("best_image_score", 0)
            ),

            "subfingerprint": sub_info,

            "output_file": str(dst),
        }

        rows.append(row)

        distribution[address] += 1
        score_by_id[address].append(row["score"])
        margin_by_id[address].append(row["margin"])

        status_counter[row["status"]] += 1
        confidence_counter[row["confidence"]] += 1

        if i % 25 == 0 or i == len(data):
            print(
                f"[{i:3d}/{len(data)}] "
                f"{src.name} -> {address} "
                f"score={row['score']:.4f}"
            )

    elapsed = time.perf_counter() - started

    # ------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------

    fields = [
        "file",
        "filename",
        "assigned_id",
        "fingerprint",
        "score",
        "second_score",
        "margin",
        "confidence",
        "status",
        "best_image",
        "best_image_score",
        "subfingerprint",
        "output_file",
    ]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    summary_distribution = {}

    for address in sorted(distribution, key=lambda x: int(x)):
        scores = score_by_id[address]
        margins = margin_by_id[address]

        summary_distribution[address] = {
            "count": len(scores),
            "percentage": round(
                len(scores) / len(rows) * 100, 2
            ),
            "score_min": round(min(scores), 6),
            "score_mean": round(
                sum(scores) / len(scores), 6
            ),
            "score_max": round(max(scores), 6),
            "margin_min": round(min(margins), 6),
            "margin_mean": round(
                sum(margins) / len(margins), 6
            ),
            "margin_max": round(max(margins), 6),
        }

    scores = [x["score"] for x in rows]
    margins = [x["margin"] for x in rows]

    summary = {
        "generated_at": datetime.now().isoformat(),

        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),

        "total_files": len(rows),
        "copied_files": copied,

        "elapsed_seconds": round(elapsed, 4),
        "seconds_per_image": round(
            elapsed / len(rows), 4
        ) if rows else 0,

        "score": {
            "min": min(scores) if scores else 0,
            "mean": (
                sum(scores) / len(scores)
                if scores else 0
            ),
            "max": max(scores) if scores else 0,
        },

        "margin": {
            "min": min(margins) if margins else 0,
            "mean": (
                sum(margins) / len(margins)
                if margins else 0
            ),
            "max": max(margins) if margins else 0,
        },

        "status": dict(status_counter),
        "confidence": dict(confidence_counter),

        "distribution": summary_distribution,

        "reports": {
            "csv": str(REPORT_CSV),
            "json": str(REPORT_JSON),
        }
    }

    # JSON с каждой фотографией
    report_json = {
        "summary": summary,
        "images": rows,
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            report_json,
            f,
            ensure_ascii=False,
            indent=2
        )

    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ------------------------------------------------------------
    # CONSOLE SUMMARY
    # ------------------------------------------------------------

    print()
    print("=" * 80)
    print("SORT COMPLETE")
    print("=" * 80)

    print(f"TOTAL:       {len(rows)}")
    print(f"COPIED:      {copied}")
    print(f"TIME:        {elapsed:.2f} sec")
    print(
        f"PER IMAGE:   "
        f"{elapsed / len(rows):.4f} sec"
        if rows else ""
    )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for address in sorted(
        distribution,
        key=lambda x: int(x)
    ):
        count = distribution[address]

        print(
            f"{address:>3}: "
            f"{count:3d} "
            f"({count / len(rows) * 100:6.2f}%)"
        )

    print()
    print("SCORE")
    print("-" * 80)

    print(f"min : {min(scores):.4f}")
    print(f"mean: {sum(scores) / len(scores):.4f}")
    print(f"max : {max(scores):.4f}")

    print()
    print("MARGIN")
    print("-" * 80)

    print(f"min : {min(margins):.4f}")
    print(f"mean: {sum(margins) / len(margins):.4f}")
    print(f"max : {max(margins):.4f}")

    print()
    print("STATUS")
    print("-" * 80)

    for k, v in status_counter.most_common():
        print(f"{k:18s} {v:4d}")

    print()
    print("REPORTS")
    print("-" * 80)

    print(REPORT_CSV)
    print(REPORT_JSON)
    print(SUMMARY_JSON)

    print()
    print("SORTED PHOTOS")
    print("-" * 80)

    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()

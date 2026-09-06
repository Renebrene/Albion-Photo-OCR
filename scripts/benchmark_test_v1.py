#!/usr/bin/env python3

import json
import re
import subprocess
import time
from pathlib import Path
from collections import Counter, defaultdict

import psutil


PROJECT = Path(__file__).resolve().parent.parent
TEST_DIR = PROJECT / "data/input/test"
OUT_DIR = PROJECT / "data/output/benchmark_v1"

FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]


def extract_real_address(filename):
    """
    Используется ТОЛЬКО для benchmark.

    Примеры:
      Вавилова 52 А (10).JPG -> 83
      1 Конной Армии 32 А (10).JPG -> ...
    """

    # Пока не угадываем адрес по тексту.
    # Используем соответствие имени через fingerprint image database
    # ниже.
    return None


def load_fingerprint_names():
    """
    Строим:
        filename -> fingerprint

    Это позволяет определить REAL для файлов,
    которые являются копиями/вариантами исходных фотографий.
    """

    result = {}

    for fp in FINGERPRINTS:
        p = PROJECT / "data/fingerprints" / fp / "metadata.json"

        if not p.exists():
            continue

        with open(p, encoding="utf-8") as f:
            meta = json.load(f)

        for name in meta.get("image_names", []):
            result[name.lower()] = fp

    return result


def find_real_from_filename(filename, fingerprint_names):
    """
    Сначала пробуем точное имя.

    Если имя тестового файла отличается от имени fingerprint,
    пытаемся использовать известные группы адресов из имени.

    Это benchmark-логика и НИКОГДА не передается recognition.
    """

    key = filename.lower()

    if key in fingerprint_names:
        return fingerprint_names[key]

    # Важный случай:
    # тестовые файлы обычно переименованы адресом.
    #
    # Для полноценного benchmark нам нужно заранее составить
    # mapping адрес -> fingerprint.
    #
    # Поэтому пока возвращаем UNKNOWN.
    return None


def run_recognition():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(TEST_DIR),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        ",".join(FINGERPRINTS),
        "--json",
    ]

    print("=" * 80)
    print("BENCHMARK RECOGNITION")
    print("=" * 80)
    print("Images:", len(list(TEST_DIR.glob("*"))))
    print("Fingerprints:", len(FINGERPRINTS))
    print()

    t0 = time.perf_counter()

    proc = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - t0

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise RuntimeError(
            f"recognize failed: {proc.returncode}"
        )

    # Ищем JSON-массив среди служебного вывода.
    decoder = json.JSONDecoder()

    data = None

    text = proc.stdout + "\n" + proc.stderr

    for i, ch in enumerate(text):
        if ch != "[":
            continue

        try:
            obj, end = decoder.raw_decode(text[i:])
            if isinstance(obj, list):
                data = obj
                break
        except json.JSONDecodeError:
            continue

    if data is None:
        raise RuntimeError("JSON recognition result not found")

    return data, elapsed


def main():

    if not TEST_DIR.exists():
        raise RuntimeError(f"Нет папки {TEST_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fingerprint_names = load_fingerprint_names()

    data, elapsed = run_recognition()

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    print("TOTAL:", len(data))
    print("TIME:", f"{elapsed:.2f} sec")
    print(
        "SPEED:",
        f"{len(data)/elapsed:.2f} images/sec"
    )

    # Пока REAL может быть неизвестен.
    # Но сохраняем всю информацию TOP-5.

    rows = []

    for x in data:

        candidates = x.get("candidates", [])

        top = [
            c.get("id")
            for c in candidates[:5]
        ]

        scores = [
            c.get("score")
            for c in candidates[:5]
        ]

        rows.append({
            "file": x.get("file"),
            "real": find_real_from_filename(
                Path(x.get("file", "")).name,
                fingerprint_names
            ),
            "top1": top[0] if len(top) > 0 else None,
            "top1_score": scores[0] if len(scores) > 0 else None,
            "top2": top[1] if len(top) > 1 else None,
            "top2_score": scores[1] if len(scores) > 1 else None,
            "top3": top[2] if len(top) > 2 else None,
            "top3_score": scores[2] if len(scores) > 2 else None,
            "top4": top[3] if len(top) > 3 else None,
            "top4_score": scores[3] if len(scores) > 3 else None,
            "top5": top[4] if len(top) > 4 else None,
            "top5_score": scores[4] if len(scores) > 4 else None,
            "score": x.get("score"),
            "margin": x.get("margin"),
            "confidence": x.get("confidence"),
            "status": x.get("status"),
            "best_image": x.get("best_image"),
        })

    # Сохраняем полный benchmark.
    (OUT_DIR / "benchmark.json").write_text(
        json.dumps(
            {
                "total": len(rows),
                "recognition_time_sec": elapsed,
                "images_per_second": len(rows) / elapsed,
                "fingerprints": FINGERPRINTS,
                "results": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Простая статистика TOP кандидатов.
    top1 = Counter(x["top1"] for x in rows)
    top2 = Counter(x["top2"] for x in rows)

    print()
    print("TOP-1 DISTRIBUTION")
    for fp, n in sorted(top1.items()):
        print(
            f"{fp:10s} {n:4d} "
            f"{100*n/len(rows):6.2f}%"
        )

    print()
    print("TOP-2 DISTRIBUTION")
    for fp, n in sorted(top2.items()):
        print(
            f"{fp:10s} {n:4d} "
            f"{100*n/len(rows):6.2f}%"
        )

    print()
    print("OUTPUT:")
    print(OUT_DIR / "benchmark.json")

    print()
    print("=" * 80)
    print("NOTE")
    print("=" * 80)
    print(
        "REAL пока не вычисляется автоматически для "
        "переименованных тестовых файлов."
    )
    print(
        "Следующим шагом построим mapping "
        "адрес -> fingerprint и получим настоящий TOP-1/2/3/5 accuracy."
    )


if __name__ == "__main__":
    main()

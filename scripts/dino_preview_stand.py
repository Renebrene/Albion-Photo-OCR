#!/usr/bin/env python
"""
Замерный стенд: может ли DINO работать по готовому MIDDLE-превью.

Зачем. Сейчас DINO читает исходник целиком и сам уменьшает его до 518 px
(глобальный эмбеддинг) и 128 px (компактные дескрипторы). MIDDLE-превью уже
огранено до 1280 px, то есть модель всё равно уменьшит его, но декодировать
и читать с диска/сети придётся в разы меньше. Нужен честный замер: не
меняются ли вердикты.

Стенд ничего не пишет в базу и не трогает исходники. Для N фото с готовым
MIDDLE-превью он считает эмбеддинги и дескрипторы двумя способами —
оригинал и превью — и сравнивает:

* косинус между векторами (глобальный, environment, color, spatial);
* какой слепок выбран лучшим и совпадает ли он;
* сходство и отрыв (margin) в обоих вариантах;
* время на фото;
* переходы адреса, если слепки привязаны к справочнику.

Запуск:
    .venv/bin/python scripts/dino_preview_stand.py --limit 30

Отчёт: docs/dino_preview_experiment.md и
docs/dino_preview_experiment_result.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dino.runner import DinoRunner  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.preview import formats as preview_formats  # noqa: E402
from app.preview.generator import build_preview_paths  # noqa: E402


def preview_root() -> Path:
    import os

    return Path(os.getenv("SCENE_PREVIEW_ROOT", str(ROOT / "data" / "preview")))


def middle_preview(photo_id: str) -> Path | None:
    paths = build_preview_paths(
        preview_root=preview_root(),
        photo_id=photo_id,
    )

    for candidate in preview_formats.candidate_paths(paths.middle):
        if candidate.is_file():
            return candidate

    return None


def address_map() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT af.fingerprint_id, af.address_id
                FROM public.address_fingerprints AS af
                JOIN public.fingerprints AS f
                  ON f.fingerprint_id = af.fingerprint_id AND f.active
                WHERE af.active
                """
            )
            return {str(row[0]): int(row[1]) for row in cur.fetchall()}


def address_names() -> dict[int, str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT address_id, simple_address, legal_address "
                "FROM public.address_directory"
            )
            return {
                int(row[0]): (row[1] or row[2] or str(row[0]))
                for row in cur.fetchall()
            }


def sample_photos(limit: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.photo_id, p.source_path, p.filename, r.dino_best_id
                FROM public.dino_runs AS r
                JOIN public.photos AS p ON p.photo_id = r.photo_id
                WHERE r.status = 'DONE'
                  AND r.dino_best_id IS NOT NULL
                ORDER BY md5(r.photo_id)
                """
            )
            rows = cur.fetchall()

    photos: list[dict] = []

    for photo_id, source_path, filename, best_id in rows:
        if not Path(source_path).is_file():
            continue

        preview = middle_preview(photo_id)

        if preview is None:
            continue

        photos.append(
            {
                "photo_id": photo_id,
                "filename": filename,
                "source_path": source_path,
                "preview_path": str(preview),
                "stored_best_id": best_id,
            }
        )

        if len(photos) >= limit:
            break

    return photos


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float32).reshape(-1)
    right = np.asarray(right, dtype=np.float32).reshape(-1)
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))

    if denominator == 0.0:
        return 0.0

    return float(np.dot(left, right) / denominator)


def describe(runner: DinoRunner, path: Path, photo_id: str) -> dict:
    """Эмбеддинг + дескрипторы + ранжирование, как в recognize_one."""

    started = time.perf_counter()
    query_global = runner.embedder.embed_paths([path])[0]
    environment, color, spatial = runner._query_descriptors(path)  # noqa: SLF001
    result = runner._rank(  # noqa: SLF001
        query_global,
        environment,
        color,
        spatial,
        photo_id,
    )
    elapsed = time.perf_counter() - started

    return {
        "global": query_global,
        "environment": environment,
        "color": color,
        "spatial": spatial,
        "result": result,
        "time_sec": elapsed,
    }


def run_one(runner: DinoRunner, photo: dict) -> dict:
    original = describe(runner, Path(photo["source_path"]), photo["photo_id"])
    preview = describe(runner, Path(photo["preview_path"]), photo["photo_id"])

    original_result = original["result"]
    preview_result = preview["result"]

    top_original = [candidate["id"] for candidate in original_result["candidates"]]
    top_preview = [candidate["id"] for candidate in preview_result["candidates"]]

    return {
        "photo_id": photo["photo_id"],
        "filename": photo["filename"],
        "preview": photo["preview_path"],
        "original": {
            "best_id": original_result["best_id"],
            "score": round(float(original_result["score"]), 6),
            "margin": round(float(original_result["margin"]), 6),
            "status": original_result["status"],
            "time_sec": round(original["time_sec"], 3),
            "top": [round(float(candidate["score"]), 6) for candidate in original_result["candidates"]],
        },
        "preview_result": {
            "best_id": preview_result["best_id"],
            "score": round(float(preview_result["score"]), 6),
            "margin": round(float(preview_result["margin"]), 6),
            "status": preview_result["status"],
            "time_sec": round(preview["time_sec"], 3),
            "top": [round(float(candidate["score"]), 6) for candidate in preview_result["candidates"]],
        },
        "same_best": original_result["best_id"] == preview_result["best_id"],
        "top5_overlap": len(set(top_original) & set(top_preview)),
        "cosine": {
            "global": round(cosine(original["global"], preview["global"]), 6),
            "environment": round(cosine(original["environment"], preview["environment"]), 6),
            "color": round(cosine(original["color"], preview["color"]), 6),
            "spatial": round(cosine(original["spatial"], preview["spatial"]), 6),
        },
    }


def summarise(rows: list[dict], fps: dict[str, int]) -> dict:
    score_deltas = [
        abs(item["original"]["score"] - item["preview_result"]["score"])
        for item in rows
    ]
    margin_deltas = [
        abs(item["original"]["margin"] - item["preview_result"]["margin"])
        for item in rows
    ]

    address_flips = []

    for item in rows:
        original_address = fps.get(str(item["original"]["best_id"] or ""))
        preview_address = fps.get(str(item["preview_result"]["best_id"] or ""))

        if original_address != preview_address:
            address_flips.append(
                {
                    "photo_id": item["photo_id"],
                    "filename": item["filename"],
                    "original_fingerprint": item["original"]["best_id"],
                    "preview_fingerprint": item["preview_result"]["best_id"],
                    "original_address": original_address,
                    "preview_address": preview_address,
                }
            )

    def statistic(values: list[float]) -> dict:
        if not values:
            return {"mean": None, "median": None, "max": None}

        return {
            "mean": round(float(np.mean(values)), 6),
            "median": round(float(np.median(values)), 6),
            "max": round(float(max(values)), 6),
        }

    return {
        "photos": len(rows),
        "same_best": sum(1 for item in rows if item["same_best"]),
        "same_best_rate": round(
            sum(1 for item in rows if item["same_best"]) / len(rows), 4
        )
        if rows
        else None,
        "top5_overlap_avg": round(
            float(np.mean([item["top5_overlap"] for item in rows])), 3
        )
        if rows
        else None,
        "score_delta": statistic(score_deltas),
        "margin_delta": statistic(margin_deltas),
        "cosine_global": statistic([item["cosine"]["global"] for item in rows]),
        "cosine_environment": statistic(
            [item["cosine"]["environment"] for item in rows]
        ),
        "cosine_color": statistic([item["cosine"]["color"] for item in rows]),
        "cosine_spatial": statistic([item["cosine"]["spatial"] for item in rows]),
        "time_original_avg": round(
            float(np.mean([item["original"]["time_sec"] for item in rows])), 3
        )
        if rows
        else None,
        "time_preview_avg": round(
            float(np.mean([item["preview_result"]["time_sec"] for item in rows])), 3
        )
        if rows
        else None,
        "address_flips": len(address_flips),
        "address_flip_samples": address_flips[:10],
    }


def write_report(report: dict, path_md: Path, path_json: Path) -> None:
    path_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    summary = report["summary"]

    lines = [
        "# Стенд: DINO по оригиналу и по MIDDLE-превью",
        "",
        f"Фото: {summary['photos']} · модель: `{report['model']}` · "
        f"слепков: {report['fingerprints']}",
        "",
        "| Показатель | Значение |",
        "|---|---:|",
        f"| Совпал лучший слепок | {summary['same_best']} / {summary['photos']} "
        f"({summary['same_best_rate']}) |",
        f"| Среднее пересечение top-5 | {summary['top5_overlap_avg']} |",
        f"| Δ score (|разница|), среднее | {summary['score_delta']['mean']} |",
        f"| Δ score, максимум | {summary['score_delta']['max']} |",
        f"| Δ margin, среднее | {summary['margin_delta']['mean']} |",
        f"| Косинус global, среднее | {summary['cosine_global']['mean']} |",
        f"| Косинус global, минимум | {summary['cosine_global']['median']} (медиана) |",
        f"| Косинус environment, среднее | {summary['cosine_environment']['mean']} |",
        f"| Косинус color, среднее | {summary['cosine_color']['mean']} |",
        f"| Косинус spatial, среднее | {summary['cosine_spatial']['mean']} |",
        f"| Время на фото: оригинал | {summary['time_original_avg']} с |",
        f"| Время на фото: превью | {summary['time_preview_avg']} с |",
        f"| Смена адреса | {summary['address_flips']} |",
        "",
        "## Фото с расхождением лучшего слепка",
        "",
    ]

    flips = [item for item in report["details"] if not item["same_best"]]

    if not flips:
        lines.append("Нет: на всей выборке выбран тот же слепок.")
    else:
        for item in flips:
            lines.append(
                f"- `{item['photo_id']}` {item['filename']}: "
                f"оригинал {item['original']['best_id']} "
                f"(score {item['original']['score']}), "
                f"превью {item['preview_result']['best_id']} "
                f"(score {item['preview_result']['score']})"
            )

    path_md.write_text("\n".join(lines) + "\n", "utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument(
        "--md",
        default=str(ROOT / "docs" / "dino_preview_experiment.md"),
    )
    parser.add_argument(
        "--json",
        default=str(ROOT / "docs" / "dino_preview_experiment_result.json"),
    )
    args = parser.parse_args(argv)

    photos = sample_photos(args.limit)

    if not photos:
        raise SystemExit("нет фото с DONE-вердиктом и MIDDLE-превью")

    runner = DinoRunner(workers=1)
    fps = address_map()
    names = address_names()

    rows = []

    # Прогрев декодеров (WebP и JPEG): первый вызов иначе попадёт в замер.
    describe(runner, Path(photos[0]["source_path"]), photos[0]["photo_id"])
    describe(runner, Path(photos[0]["preview_path"]), photos[0]["photo_id"])

    for index, photo in enumerate(photos, start=1):
        print(f"[{index}/{len(photos)}] {photo['photo_id']}", flush=True)
        rows.append(run_one(runner, photo))

    summary = summarise(rows, fps)

    for sample in summary["address_flip_samples"]:
        sample["original_name"] = names.get(sample["original_address"])
        sample["preview_name"] = names.get(sample["preview_address"])

    result = {
        "model": runner.cpu_settings.model_name,
        "fingerprints": len(runner.fingerprints),
        "summary": summary,
        "details": rows,
    }

    write_report(result, Path(args.md), Path(args.json))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nОтчёт: {args.md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

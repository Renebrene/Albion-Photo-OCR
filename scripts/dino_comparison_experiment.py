#!/usr/bin/env python3
"""Read-only comparison of DINO matching strategies on the existing corpus.

Point 9 of the DINO review: cosine-to-centroid, best reference, top-k means,
multiple centroids, blends, and descriptor combinations.  The test set is a
stratified sample of photos whose address is written in the filename.

Nothing is written to PostgreSQL or to production fingerprints.  Query
embeddings are recomputed from the original files; candidate fingerprints are
read from data/fingerprints.

    .venv/bin/python scripts/dino_comparison_experiment.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.embedder import SceneEmbedder  # noqa: E402
from app.core.fingerprint import FingerprintManager  # noqa: E402
from app.core.scene_analyzer import CompactDescriptor  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    expected_address,
    fingerprint_addresses,
    load_addresses,
)

OUT = Path("data/experiments/dino_comparison")
REPORT = Path(f"data/reports/dino_comparison_experiment_{date.today():%Y%m%d}.md")
SAMPLE_TARGET = 600
PER_ADDRESS = 5
CANONICAL_ADDRESS = {1509: 148, 2301: 205, 2412: 212}
random.seed(7)


def normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32)
    return vector / max(float(np.linalg.norm(vector)), 1e-9)


def descriptor_similarity(query: np.ndarray, references: np.ndarray) -> float:
    scores = references @ query
    k = max(3, int(len(scores) * 0.10))
    k = min(k, len(scores))
    if k <= 0:
        return 0.0
    return float(np.sort(scores)[-k:].mean())


def load_candidates() -> dict[str, list[dict]]:
    """Stored DINO candidates for the photos in the current batch."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.photo_id, c.fingerprint_id, c.score,
                       c.global_score, c.environment_score, c.color_score,
                       c.spatial_score, c.best_image_score
                FROM public.dino_runs AS r
                JOIN public.dino_candidates AS c ON c.run_id = r.run_id
                WHERE r.batch_id = 17
                  AND r.status = 'DONE'
                ORDER BY r.photo_id, c.rank
                """
            )
            result: dict[str, list[dict]] = defaultdict(list)
            for row in cur.fetchall():
                result[str(row[0])].append(
                    {
                        "fingerprint_id": str(row[1]),
                        "stored_score": float(row[2]),
                        "global": float(row[3]),
                        "environment": float(row[4]),
                        "color": float(row[5]),
                        "spatial": float(row[6]),
                        "best_image_score": float(row[7]),
                    }
                )
            return result


def load_photo_rows(photo_ids: list[str]) -> dict[str, tuple[str, str]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id, filename, source_path FROM public.photos "
                "WHERE photo_id = ANY(%s)",
                (photo_ids,),
            )
            return {
                str(row[0]): (str(row[1]), str(row[2] or ""))
                for row in cur.fetchall()
            }


def build_sample() -> list[str]:
    """Stratified sample: at most a few photos per expected address."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id, filename FROM public.photos "
                "WHERE filename IS NOT NULL"
            )
            rows = cur.fetchall()

    addresses = load_addresses()
    by_address: dict[int, list[str]] = defaultdict(list)

    for photo_id, filename in rows:
        expected = expected_address(str(filename), addresses)
        if expected is None:
            continue
        expected = CANONICAL_ADDRESS.get(expected, expected)
        by_address[expected].append(str(photo_id))

    sample: list[str] = []
    for expected, values in sorted(by_address.items()):
        random.shuffle(values)
        sample.extend(values[:PER_ADDRESS])

    random.shuffle(sample)
    return sample[:SAMPLE_TARGET]


class FingerprintCache:
    def __init__(self, manager: FingerprintManager):
        self.manager = manager
        self.data: dict[str, dict] = {}

    def get(self, fingerprint_id: str) -> dict | None:
        if fingerprint_id in self.data:
            return self.data[fingerprint_id]

        try:
            data = self.manager.load(fingerprint_id)
        except (FileNotFoundError, ValueError, OSError):
            self.data[fingerprint_id] = None
            return None

        embeddings = np.asarray(data["embeddings"], dtype=np.float32)
        embeddings = embeddings / np.maximum(
            np.linalg.norm(embeddings, axis=1, keepdims=True),
            1e-9,
        )
        data["embeddings"] = embeddings
        data["centroid"] = normalize(data["centroid"])
        data["clusters"] = self._clusters(embeddings)
        self.data[fingerprint_id] = data
        return data

    @staticmethod
    def _clusters(embeddings: np.ndarray, count: int = 4) -> np.ndarray:
        if len(embeddings) < count * 2:
            return np.asarray([normalize(embeddings.mean(axis=0))])
        try:
            model = KMeans(n_clusters=count, random_state=7, n_init=10)
            model.fit(embeddings)
            centers = model.cluster_centers_
            return centers / np.maximum(
                np.linalg.norm(centers, axis=1, keepdims=True),
                1e-9,
            )
        except Exception:  # noqa: BLE001 - one fingerprint, not the experiment
            return np.asarray([normalize(embeddings.mean(axis=0))])


def score_methods(
    query: np.ndarray,
    env: np.ndarray,
    color: np.ndarray,
    spatial: np.ndarray,
    fingerprint: dict,
) -> dict[str, float]:
    embeddings = fingerprint["embeddings"]
    centroid = float(query @ fingerprint["centroid"])
    ref_scores = embeddings @ query
    sorted_scores = np.sort(ref_scores)[::-1]

    def top_k(k: int) -> float:
        if not len(sorted_scores):
            return 0.0
        return float(sorted_scores[:min(k, len(sorted_scores))].mean())

    best = float(sorted_scores[0]) if len(sorted_scores) else 0.0
    top3 = top_k(3)
    top5 = top_k(5)
    top10 = top_k(10)
    cluster = float(np.max(fingerprint["clusters"] @ query))
    env_score = descriptor_similarity(env, fingerprint["environment_embeddings"])
    color_score = descriptor_similarity(color, fingerprint["color_embeddings"])
    spatial_score = descriptor_similarity(spatial, fingerprint["spatial_embeddings"])

    def combined(global_score: float) -> float:
        return (
            0.70 * global_score
            + 0.20 * env_score
            + 0.07 * color_score
            + 0.03 * spatial_score
        )

    return {
        "centroid": centroid,
        "best": best,
        "top3": top3,
        "top5": top5,
        "top10": top10,
        "cluster4": cluster,
        "centroid_best": 0.5 * centroid + 0.5 * best,
        "centroid_top3": 0.7 * centroid + 0.3 * top3,
        "max_centroid_top3": max(centroid, top3),
        "combined_centroid": combined(centroid),
        "combined_best": combined(best),
        "combined_top3": combined(top3),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cpu = replace(settings, device="cpu")
    embedder = SceneEmbedder(cpu)
    manager = FingerprintManager(cpu, embedder)
    cache = FingerprintCache(manager)

    sample = build_sample()
    print(f"[compare] sample={len(sample)}", flush=True)
    photo_rows = load_photo_rows(sample)
    candidates = load_candidates()
    fp_to_address = fingerprint_addresses()
    addresses = load_addresses()

    # Precompute expected labels from the filenames.
    expected: dict[str, int | None] = {}
    for photo_id, (filename, _source) in photo_rows.items():
        value = expected_address(filename, addresses)
        expected[photo_id] = (
            CANONICAL_ADDRESS.get(value, value)
            if value is not None
            else None
        )

    method_scores: dict[str, list[float]] = defaultdict(list)
    method_addresses: dict[str, dict[str, float]] = defaultdict(dict)
    rows = []

    for index, photo_id in enumerate(sample, 1):
        row = photo_rows.get(photo_id)
        if row is None:
            continue
        filename, source_path = row
        path = Path(source_path)
        if not path.exists():
            preview = Path("data/preview/middle") / f"{photo_id}.webp"
            if preview.exists():
                path = preview
            else:
                continue

        candidate_rows = candidates.get(photo_id)
        if not candidate_rows:
            continue

        try:
            query = normalize(embedder.embed_paths([path])[0])
            image = CompactDescriptor._load(path)
            env, color, spatial = CompactDescriptor.all_from_image(image)
        except Exception as exc:  # noqa: BLE001
            print(f"[compare] skip {photo_id}: {exc}", flush=True)
            continue

        by_address: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        for candidate in candidate_rows:
            fingerprint_id = candidate["fingerprint_id"]
            fingerprint = cache.get(fingerprint_id)
            if fingerprint is None:
                continue
            address = fp_to_address.get(fingerprint_id)
            if address is None:
                continue

            scores = score_methods(query, env, color, spatial, fingerprint)
            for method, score in scores.items():
                by_address[address][method] = max(
                    by_address[address][method],
                    score,
                )
            # Stored production score, for reference.
            by_address[address]["stored"] = max(
                by_address[address]["stored"],
                candidate["stored_score"],
            )

        if not by_address:
            continue

        expected_address_id = expected.get(photo_id)
        label = ADDRESS_NAMES.get(expected_address_id, "") if expected_address_id else ""
        predictions = {}
        for method in method_scores.keys() | {
            name for item in by_address.values() for name in item
        }:
            best_address = max(
                by_address,
                key=lambda address_id: by_address[address_id].get(method, -1.0),
            )
            predictions[method] = {
                "address": best_address,
                "name": ADDRESS_NAMES.get(best_address, ""),
                "score": by_address[best_address].get(method, None),
            }
            if expected_address_id is not None:
                method_scores[method].append(
                    float(best_address == expected_address_id)
                )

        rows.append(
            {
                "photo_id": photo_id,
                "filename": filename,
                "expected": expected_address_id,
                "expected_name": label,
                "predictions": predictions,
            }
        )

        if index % 50 == 0:
            print(f"[compare] {index}/{len(sample)}", flush=True)

    summary = []
    for method, values in sorted(method_scores.items(), key=lambda pair: -np.mean(pair[1])):
        if not values:
            continue
        summary.append(
            {
                "method": method,
                "correct": int(sum(values)),
                "total": len(values),
                "accuracy": float(np.mean(values)),
            }
        )

    report = {
        "sample": len(rows),
        "methods": summary,
        "tested_fingerprints": len(cache.data),
    }
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# DINO: сравнение способов сопоставления",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и слепки не изменялись.",
        "",
        f"Стратифицированная выборка: **{len(rows)}** подписанных фото, "
        f"до {PER_ADDRESS} фото на адрес. Загружено слепков: {len(cache.data)}.",
        "",
        "| Метод | Верно | Всего | Точность |",
        "|---|---:|---:|---:|",
    ]
    for item in summary:
        lines.append(
            f"| `{item['method']}` | {item['correct']} | {item['total']} | "
            f"{item['accuracy']*100:.2f}% |"
        )

    lines += [
        "",
        "## Что означает",
        "",
        "- `centroid` — текущее сравнение с центроидом слепка.",
        "- `best` — максимум по отдельным эталонным кадрам (`best_image_score`).",
        "- `top3/5/10` — среднее лучших K эталонных кадров.",
        "- `cluster4` — лучшее из 4 кластеров внутри слепка.",
        "- `*_combined` — global-метод плюс environment/color/spatial.",
        "- `stored` — production-score из DINO-кандидатов.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[compare] report: {REPORT}", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2)[:3000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

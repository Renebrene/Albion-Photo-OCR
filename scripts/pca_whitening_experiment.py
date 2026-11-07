#!/usr/bin/env python3
"""Read-only PCA / whitening pilot for DINO global embeddings.

Fits PCA (with and without whitening) on the reference embeddings of the
active fingerprints, transforms both references and queries, and compares
top-1 retrieval on labelled photos.  Nothing is written to PostgreSQL or to
production fingerprints.

    .venv/bin/python scripts/pca_whitening_experiment.py

Outputs:
    data/experiments/pca_whitening/report.json
    data/reports/pca_whitening_experiment_YYYYMMDD.md
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.embedder import SceneEmbedder  # noqa: E402
from app.core.fingerprint import FingerprintManager  # noqa: E402
from app.core.scene_analyzer import CompactDescriptor  # noqa: E402
from scripts import dino_comparison_experiment as dce  # noqa: E402
from scripts.evaluate_sorting import ADDRESS_NAMES  # noqa: E402

OUT = Path("data/experiments/pca_whitening")
REPORT = Path(f"data/reports/pca_whitening_experiment_{date.today():%Y%m%d}.md")

METHODS = ("centroid", "best", "top3", "top5")

# (name, components or None, whiten)
VARIANTS = [
    ("raw", None, False),
    ("pca128", 128, False),
    ("pca256", 256, False),
    ("pca512", 512, False),
    ("white128", 128, True),
    ("white256", 256, True),
    ("white512", 512, True),
]


def l2_normalize(rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    if rows.ndim == 1:
        return rows / max(float(np.linalg.norm(rows)), 1e-9)
    return rows / np.maximum(
        np.linalg.norm(rows, axis=1, keepdims=True),
        1e-9,
    )


def fit_variant(matrix: np.ndarray, components: int | None, whiten: bool):
    if components is None:
        return None
    model = PCA(
        n_components=min(components, matrix.shape[1]),
        whiten=whiten,
        svd_solver="randomized",
        random_state=7,
    )
    model.fit(matrix)
    return model


def transform(model, rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    if model is None:
        return l2_normalize(rows)
    transformed = model.transform(rows)
    return l2_normalize(transformed)


def top_k(scores: np.ndarray, k: int) -> float:
    if not len(scores):
        return 0.0
    values = np.sort(scores)[::-1]
    return float(values[: min(k, len(values))].mean())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    sample = dce.build_sample()
    photo_rows = dce.load_photo_rows(sample)
    candidates = dce.load_candidates()

    embedder = SceneEmbedder(settings)
    manager = FingerprintManager(settings, embedder)
    cache = dce.FingerprintCache(manager)

    fingerprint_ids = sorted(
        {
            candidate["fingerprint_id"]
            for rows in candidates.values()
            for candidate in rows
        }
    )

    fingerprints = {}
    for fingerprint_id in fingerprint_ids:
        fingerprint = cache.get(fingerprint_id)
        if fingerprint is not None:
            fingerprints[fingerprint_id] = fingerprint

    reference_matrix = np.vstack(
        [fingerprint["embeddings"] for fingerprint in fingerprints.values()]
    ).astype(np.float32)
    print(
        f"[pca] fingerprints={len(fingerprints)} "
        f"reference_vectors={len(reference_matrix)}",
        flush=True,
    )

    models = []
    transformed = {}
    for name, components, whiten in VARIANTS:
        model = fit_variant(reference_matrix, components, whiten)
        models.append((name, model))

        per_fingerprint = {}
        for fingerprint_id, fingerprint in fingerprints.items():
            embeddings = transform(model, fingerprint["embeddings"])
            centroid = l2_normalize(embeddings.mean(axis=0))
            per_fingerprint[fingerprint_id] = {
                "embeddings": embeddings,
                "centroid": centroid,
            }
        transformed[name] = per_fingerprint
        print(f"[pca] fitted {name}", flush=True)

    addresses = dce.fingerprint_addresses()
    address_rows = dce.load_addresses()
    expected = {}
    for photo_id in sample:
        row = photo_rows.get(photo_id)
        if row is None:
            continue
        value = dce.expected_address(row[0], address_rows)
        expected[photo_id] = (
            dce.CANONICAL_ADDRESS.get(value, value)
            if value is not None
            else None
        )

    records: dict[str, list[dict]] = {
        f"{variant}|{method}": []
        for variant, _components, _whiten in VARIANTS
        for method in METHODS
    }
    errors: dict[str, Counter] = defaultdict(Counter)
    tested = 0
    skipped = 0

    for index, photo_id in enumerate(sample, 1):
        row = photo_rows.get(photo_id)
        if row is None:
            skipped += 1
            continue

        _filename, source_path = row
        path = Path(source_path)
        if not path.exists():
            preview = Path("data/preview/middle") / f"{photo_id}.webp"
            if preview.exists():
                path = preview
            else:
                skipped += 1
                continue

        candidate_rows = candidates.get(photo_id)
        if not candidate_rows:
            skipped += 1
            continue

        try:
            query = dce.normalize(embedder.embed_paths([path])[0])
        except Exception as exc:  # noqa: BLE001 - one bad photo
            print(f"[pca] skip {photo_id}: {exc}", flush=True)
            skipped += 1
            continue

        expected_id = expected.get(photo_id)
        if expected_id is None:
            skipped += 1
            continue

        tested += 1

        for variant, model in models:
            query_t = transform(model, query.reshape(1, -1))[0]
            by_address: dict[int, dict[str, float]] = defaultdict(dict)

            for candidate in candidate_rows:
                fingerprint_id = candidate["fingerprint_id"]
                data = transformed[variant].get(fingerprint_id)
                if data is None:
                    continue
                address_id = addresses.get(fingerprint_id)
                if address_id is None:
                    continue

                embeddings = data["embeddings"]
                scores = embeddings @ query_t
                components = {
                    "centroid": float(query_t @ data["centroid"]),
                    "best": float(scores.max()) if len(scores) else 0.0,
                    "top3": top_k(scores, 3),
                    "top5": top_k(scores, 5),
                }
                target = by_address[address_id]
                for method, value in components.items():
                    target[method] = max(target.get(method, -1.0), value)

            if not by_address:
                continue

            for method in METHODS:
                ranked = sorted(
                    (
                        (address_id, values[method])
                        for address_id, values in by_address.items()
                        if method in values
                    ),
                    key=lambda pair: pair[1],
                    reverse=True,
                )
                if not ranked:
                    continue
                predicted_id, best_score = ranked[0]
                second_score = ranked[1][1] if len(ranked) > 1 else None
                combo = f"{variant}|{method}"
                correct = predicted_id == expected_id
                records[combo].append(
                    {
                        "photo_id": photo_id,
                        "expected": expected_id,
                        "predicted": predicted_id,
                        "score": float(best_score),
                        "margin": (
                            float(best_score - second_score)
                            if second_score is not None
                            else None
                        ),
                        "correct": correct,
                    }
                )
                if not correct:
                    errors[combo][(expected_id, predicted_id)] += 1

        if index % 25 == 0:
            print(f"[pca] {index}/{len(sample)}", flush=True)

    results = []
    for combo, combo_records in records.items():
        if not combo_records:
            continue
        variant, method = combo.split("|")
        correct = sum(1 for record in combo_records if record["correct"])
        results.append(
            {
                "name": combo,
                "variant": variant,
                "method": method,
                "correct": correct,
                "total": len(combo_records),
                "accuracy": correct / len(combo_records),
                "wrong_pairs": [
                    {
                        "expected": expected_id,
                        "expected_name": ADDRESS_NAMES.get(expected_id, ""),
                        "predicted": predicted_id,
                        "predicted_name": ADDRESS_NAMES.get(predicted_id, ""),
                        "count": count,
                    }
                    for (expected_id, predicted_id), count in errors[combo].most_common(5)
                ],
            }
        )

    results.sort(key=lambda item: (-item["correct"], item["name"]))
    best = results[0] if results else None

    report = {
        "sample": len(sample),
        "tested": tested,
        "skipped": skipped,
        "fingerprints": len(fingerprints),
        "reference_vectors": len(reference_matrix),
        "results": results,
        "best": best,
    }
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# PCA / whitening для DINO-эмбеддингов",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и production-слепки "
        "не изменялись.",
        "",
        f"Выборка: **{tested}** подписанных фото; слепков: {len(fingerprints)}; "
        f"эталонных векторов: {len(reference_matrix)}.",
        "",
        "PCA обучалась на эталонных эмбеддингах всех активных слепков. "
        "После преобразования векторы L2-нормализуются.",
        "",
        "| Вариант | centroid | best | top3 | top5 |",
        "|---|---:|---:|---:|---:|",
    ]

    by_variant: dict[str, dict[str, dict]] = defaultdict(dict)
    for item in results:
        by_variant[item["variant"]][item["method"]] = item

    for variant, _components, _whiten in VARIANTS:
        row = by_variant.get(variant, {})
        cells = []
        for method in METHODS:
            item = row.get(method)
            cells.append(
                f"{item['correct']}/{item['total']} "
                f"({item['accuracy']*100:.2f}%)"
                if item
                else "—"
            )
        lines.append(f"| `{variant}` | " + " | ".join(cells) + " |")

    if best is not None:
        lines += [
            "",
            f"Лучший вариант: **`{best['name']}`** — "
            f"{best['correct']}/{best['total']} ({best['accuracy']*100:.2f}%).",
            "",
            "| Ожидалось → предсказано | Кол-во |",
            "|---|---:|",
        ]
        for pair in best["wrong_pairs"]:
            lines.append(
                f"| {pair['expected_name']} → {pair['predicted_name']} | "
                f"{pair['count']} |"
            )

    lines += [
        "",
        "## Ограничения",
        "",
        "- Выборка — те же 328 фото и 71 адрес, что и в предыдущем эксперименте: "
        "небольшая и стратифицированная.",
        "- PCA обучалась на эталонных кадрах, но оценивалась на тех же адресах; "
        "для production нужен отдельный temporal holdout.",
        "- Оценивался только global-компонент; environment/color/spatial не "
        "менялись.",
        "- Преобразование меняет формат эмбеддинга: старые и новые слепки "
        "несовместимы без версии и пересборки FAISS.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[pca] report: {REPORT}", flush=True)
    print(json.dumps(report["best"], ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

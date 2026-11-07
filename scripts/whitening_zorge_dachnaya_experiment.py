#!/usr/bin/env python3
"""Read-only whitening experiment for Zorge / Dachnaya.

Builds experimental fingerprints from the two labelled reference folders:

    /media/alexice/TEST/дачная
    /media/alexice/TEST/зорге

Three transforms are compared:

* raw      - ordinary CLS embeddings, current behaviour;
* local    - PCA whitening fitted on the 68 reference images of the two
             addresses themselves;
* global   - PCA whitening fitted on all other active fingerprints (the
             transform is not fitted on the evaluated addresses).

Queries are all corpus photos whose filename contains both "Вавилова" and
"Дачная" or both "Стачки" and "Зорге".  Exact duplicate files from the
reference folders are excluded.

Nothing is written to PostgreSQL or to production fingerprints.

    .venv/bin/python scripts/whitening_zorge_dachnaya_experiment.py

Outputs:
    data/experiments/whitening_zorge_dachnaya/report.json
    data/reports/whitening_zorge_dachnaya_YYYYMMDD.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.embedder import SceneEmbedder  # noqa: E402
from app.core.fingerprint import FingerprintManager  # noqa: E402
from app.core.scene_analyzer import CompactDescriptor  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from scripts.dino_v35_experiment import query_path  # noqa: E402

OUT = Path("data/experiments/whitening_zorge_dachnaya")
REPORT = Path(f"data/reports/whitening_zorge_dachnaya_{date.today():%Y%m%d}.md")

REFERENCE = {
    "dachnaya": Path("/media/alexice/TEST/дачная"),
    "zorge": Path("/media/alexice/TEST/зорге"),
}
PRODUCTION = {"dachnaya": "51_v35", "zorge": "92_v35"}
ADDRESS_IDS = (144, 211)

# Variant name -> ("raw" | "local" | "global", components)
VARIANTS = {
    "raw": ("raw", None),
    "local_white16": ("local", 16),
    "local_white32": ("local", 32),
    "local_white48": ("local", 48),
    "global_white256": ("global", 256),
    "global_white512": ("global", 512),
}

METHODS = ("centroid", "best", "top3", "top5")
COMBINED = {
    "comb_centroid_base": ("centroid", (0.70, 0.20, 0.07, 0.03)),
    "comb_centroid_env": ("centroid", (0.60, 0.30, 0.07, 0.03)),
    "comb_best_env": ("best", (0.60, 0.30, 0.07, 0.03)),
}
BASE_WEIGHTS = (0.70, 0.20, 0.07, 0.03)


def l2_normalize(rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    if rows.ndim == 1:
        return rows / max(float(np.linalg.norm(rows)), 1e-9)
    return rows / np.maximum(
        np.linalg.norm(rows, axis=1, keepdims=True),
        1e-9,
    )


def descriptor_similarity(query: np.ndarray, references: np.ndarray) -> float:
    scores = np.asarray(references) @ np.asarray(query)
    k = max(3, int(len(scores) * 0.10))
    k = min(k, len(scores))
    if k <= 0:
        return 0.0
    return float(np.sort(scores)[-k:].mean())


def file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reference_hashes() -> set[str]:
    result = set()
    for folder in REFERENCE.values():
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}:
                digest = file_hash(path)
                if digest:
                    result.add(digest)
    return result


def top_k(scores: np.ndarray, k: int) -> float:
    if not len(scores):
        return 0.0
    values = np.sort(scores)[::-1]
    return float(values[: min(k, len(values))].mean())


def load_references(
    embedder: SceneEmbedder,
) -> dict[str, dict]:
    result = {}
    for label, folder in REFERENCE.items():
        paths = sorted(
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
        )
        embeddings = l2_normalize(embedder.embed_paths(paths))
        environment, color, spatial = [], [], []
        for path in paths:
            env, col, spa = CompactDescriptor.all(path)
            environment.append(env)
            color.append(col)
            spatial.append(spa)

        result[label] = {
            "paths": paths,
            "embeddings": embeddings,
            "environment": np.stack(environment),
            "color": np.stack(color),
            "spatial": np.stack(spatial),
        }
        print(
            f"[white] reference {label}: {len(paths)} images",
            flush=True,
        )
    return result


def load_global_matrix(exclude_ids: set[str], embedder: SceneEmbedder):
    """Reference embeddings of all active fingerprints except the two."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT f.fingerprint_id
                FROM public.fingerprints AS f
                JOIN public.address_fingerprints AS af
                  ON af.fingerprint_id = f.fingerprint_id AND af.active
                WHERE f.active
                  AND af.address_id <> ALL(%s)
                """,
                (list(ADDRESS_IDS),),
            )
            ids = [str(row[0]) for row in cur.fetchall()]

    manager = FingerprintManager(settings, embedder)
    rows = []
    for fingerprint_id in sorted(set(ids) - exclude_ids):
        try:
            data = manager.load(fingerprint_id)
        except (FileNotFoundError, ValueError, OSError):
            continue
        rows.append(l2_normalize(np.asarray(data["embeddings"])))

    if not rows:
        return np.empty((0, 768), dtype=np.float32)
    return np.vstack(rows)


def fit_transforms(
    references: dict[str, dict],
    global_matrix: np.ndarray,
) -> dict[str, PCA | None]:
    local_matrix = np.vstack(
        [data["embeddings"] for data in references.values()]
    )
    transforms: dict[str, PCA | None] = {"raw": None}

    for name, (kind, components) in VARIANTS.items():
        if kind == "raw":
            continue
        matrix = local_matrix if kind == "local" else global_matrix
        if len(matrix) < 2:
            transforms[name] = None
            continue
        count = min(components, matrix.shape[1], len(matrix) - 1)
        model = PCA(
            n_components=count,
            whiten=True,
            svd_solver="randomized",
            random_state=7,
        )
        model.fit(matrix)
        transforms[name] = model
        print(
            f"[white] fitted {name}: {count} components "
            f"on {len(matrix)} vectors",
            flush=True,
        )
    return transforms


def apply_transform(model: PCA | None, rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    if model is None:
        return l2_normalize(rows)
    return l2_normalize(model.transform(rows))


def fingerprint_data(
    references: dict[str, dict],
    transforms: dict[str, PCA | None],
) -> dict[str, dict[str, dict]]:
    """For every variant and label: embeddings, centroid, descriptors."""

    result = {}
    for variant, model in transforms.items():
        per_label = {}
        for label, data in references.items():
            embeddings = apply_transform(model, data["embeddings"])
            per_label[label] = {
                "embeddings": embeddings,
                "centroid": l2_normalize(embeddings.mean(axis=0)),
                "environment": data["environment"],
                "color": data["color"],
                "spatial": data["spatial"],
            }
        result[variant] = per_label
    return result


def save_artifacts(
    references: dict[str, dict],
    transforms: dict[str, PCA | None],
    fingerprints: dict[str, dict[str, dict]],
) -> None:
    """Persist experimental fingerprints and PCA transforms."""

    for variant, per_label in fingerprints.items():
        for label, data in per_label.items():
            out = OUT / "fingerprints" / variant / label
            out.mkdir(parents=True, exist_ok=True)

            np.save(out / "embeddings.npy", data["embeddings"])
            np.save(out / "centroid.npy", data["centroid"])
            np.save(
                out / "environment_embeddings.npy", data["environment"]
            )
            np.save(out / "color_embeddings.npy", data["color"])
            np.save(out / "spatial_embeddings.npy", data["spatial"])

            similarities = data["embeddings"] @ data["centroid"]
            indices = np.argsort(similarities)[-16:][::-1].astype(np.int32)
            np.save(out / "representative_indices.npy", indices)
            np.save(
                out / "representatives.npy", data["embeddings"][indices]
            )

            metadata = {
                "id": f"{label}_{variant}",
                "variant": variant,
                "label": label,
                "source_folder": str(REFERENCE[label]),
                "image_names": [
                    path.name for path in references[label]["paths"]
                ],
                "images": len(references[label]["paths"]),
                "model": settings.model_name,
                "dimension": int(data["embeddings"].shape[1]),
                "representation": (
                    "raw" if variant == "raw" else "pca_whitening"
                ),
                "experimental": True,
            }
            (out / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    for variant, model in transforms.items():
        if model is None:
            continue
        out = OUT / "transforms" / variant
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "mean.npy", model.mean_)
        np.save(out / "components.npy", model.components_)
        np.save(
            out / "explained_variance.npy", model.explained_variance_
        )
        (out / "metadata.json").write_text(
            json.dumps(
                {
                    "variant": variant,
                    "components": int(model.components_.shape[0]),
                    "whiten": True,
                    "random_state": 7,
                    "experimental": True,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def load_production(embedder: SceneEmbedder):
    manager = FingerprintManager(settings, embedder)
    result = {}
    for label, fingerprint_id in PRODUCTION.items():
        data = manager.load(fingerprint_id)
        embeddings = l2_normalize(np.asarray(data["embeddings"]))
        result[label] = {
            "embeddings": embeddings,
            "centroid": l2_normalize(np.asarray(data["centroid"])),
            "environment": np.asarray(data["environment_embeddings"]),
            "color": np.asarray(data["color_embeddings"]),
            "spatial": np.asarray(data["spatial_embeddings"]),
        }
    return result


def load_queries() -> list[tuple[str, str, str, str]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, filename, source_path, 'dachnaya'
                FROM public.photos
                WHERE filename ILIKE %s AND filename ILIKE %s
                UNION ALL
                SELECT photo_id, filename, source_path, 'zorge'
                FROM public.photos
                WHERE filename ILIKE %s AND filename ILIKE %s
                """,
                ("%Вавилова%", "%Дачная%", "%Стачки%", "%Зорге%"),
            )
            return [
                (str(row[0]), str(row[1]), str(row[2] or ""), str(row[3]))
                for row in cur.fetchall()
            ]


def score_fingerprint(
    query: np.ndarray,
    query_environment: np.ndarray,
    query_color: np.ndarray,
    query_spatial: np.ndarray,
    fingerprint: dict,
) -> dict[str, float]:
    scores = fingerprint["embeddings"] @ query
    result = {
        "centroid": float(query @ fingerprint["centroid"]),
        "best": float(scores.max()) if len(scores) else 0.0,
        "top3": top_k(scores, 3),
        "top5": top_k(scores, 5),
    }
    environment = descriptor_similarity(
        query_environment, fingerprint["environment"]
    )
    color = descriptor_similarity(query_color, fingerprint["color"])
    spatial = descriptor_similarity(query_spatial, fingerprint["spatial"])
    for name, (method, weights) in COMBINED.items():
        wg, we, wc, ws = weights
        result[name] = (
            wg * result[method]
            + we * environment
            + wc * color
            + ws * spatial
        )
    return result


def predict(
    query_scores: dict[str, dict[str, float]],
    method: str,
) -> tuple[str, float, float | None]:
    ranked = sorted(
        (
            (label, scores[method])
            for label, scores in query_scores.items()
            if method in scores
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )
    label, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else None
    return label, score, second


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="smoke test: only the first N queries (0 = all)",
    )
    args = parser.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    embedder = SceneEmbedder(settings)
    references = load_references(embedder)
    ref_hashes = reference_hashes()

    excluded = set(PRODUCTION.values())
    global_matrix = load_global_matrix(excluded, embedder)
    print(
        f"[white] global matrix: {len(global_matrix)} vectors "
        f"(excluding {sorted(excluded)})",
        flush=True,
    )

    transforms = fit_transforms(references, global_matrix)
    fingerprints = fingerprint_data(references, transforms)
    save_artifacts(references, transforms, fingerprints)
    production = load_production(embedder)

    queries = load_queries()
    if args.limit:
        queries = queries[: args.limit]
    print(f"[white] queries in DB: {len(queries)}", flush=True)

    methods = list(METHODS) + list(COMBINED)
    records: dict[str, list[dict]] = {
        f"{variant}|{method}": []
        for variant in list(fingerprints) + ["production"]
        for method in methods
    }
    errors: dict[str, Counter] = defaultdict(Counter)
    monthly: dict[str, Counter] = defaultdict(Counter)

    tested = 0
    skipped_duplicate = 0
    skipped_missing = 0

    for index, (photo_id, filename, source_path, label) in enumerate(queries, 1):
        source = Path(source_path)
        if source.exists():
            digest = file_hash(source)
            if digest in ref_hashes:
                skipped_duplicate += 1
                continue

        path = query_path(photo_id, source_path)
        if not path.exists():
            skipped_missing += 1
            continue

        try:
            query = l2_normalize(embedder.embed_paths([path])[0])
            image = CompactDescriptor._load(path)
            environment, color, spatial = CompactDescriptor.all_from_image(
                image
            )
        except Exception as exc:  # noqa: BLE001 - one bad photo
            print(f"[white] skip {photo_id}: {exc}", flush=True)
            skipped_missing += 1
            continue

        tested += 1
        month = None
        if source.exists():
            try:
                from PIL import Image

                with Image.open(source) as handle:
                    value = handle.getexif().get(306)
                if value:
                    month = str(value)[:7]
            except Exception:  # noqa: BLE001
                month = None
        month = month or "unknown"

        for variant, per_label in list(fingerprints.items()) + [
            ("production", production)
        ]:
            model = transforms.get(variant)
            query_variant = (
                apply_transform(model, query.reshape(1, -1))[0]
                if variant != "production"
                else query
            )
            scores = {
                fp_label: score_fingerprint(
                    query_variant,
                    environment,
                    color,
                    spatial,
                    fingerprint,
                )
                for fp_label, fingerprint in per_label.items()
            }

            for method in methods:
                predicted, best_score, second_score = predict(scores, method)
                correct = predicted == label
                combo = f"{variant}|{method}"
                records[combo].append(
                    {
                        "photo_id": photo_id,
                        "expected": label,
                        "predicted": predicted,
                        "score": best_score,
                        "margin": (
                            best_score - second_score
                            if second_score is not None
                            else None
                        ),
                        "correct": correct,
                    }
                )
                if not correct:
                    errors[combo][(label, predicted)] += 1
                if method in ("centroid", "best", "comb_centroid_env"):
                    key = f"{variant}|{method}"
                    monthly[key]["total"] += 1
                    monthly[key]["correct"] += int(correct)

        if index % 100 == 0:
            print(f"[white] {index}/{len(queries)}", flush=True)

    results = []
    for combo, combo_records in records.items():
        if not combo_records:
            continue
        variant, method = combo.split("|")
        correct = sum(1 for record in combo_records if record["correct"])
        by_class = Counter(
            record["expected"] for record in combo_records
        )
        correct_by_class = Counter(
            record["expected"] for record in combo_records if record["correct"]
        )
        results.append(
            {
                "name": combo,
                "variant": variant,
                "method": method,
                "correct": correct,
                "total": len(combo_records),
                "accuracy": correct / len(combo_records),
                "class_accuracy": {
                    label: correct_by_class[label] / count
                    for label, count in by_class.items()
                },
                "wrong_pairs": [
                    {
                        "expected": expected,
                        "predicted": predicted,
                        "count": count,
                    }
                    for (expected, predicted), count in errors[combo].most_common(5)
                ],
            }
        )

    results.sort(key=lambda item: (-item["correct"], item["name"]))
    best = results[0] if results else None

    monthly_rows = []
    for key, counter in monthly.items():
        if counter["total"] >= 50:
            monthly_rows.append(
                {
                    "name": key,
                    "total": counter["total"],
                    "correct": counter["correct"],
                    "accuracy": counter["correct"] / counter["total"],
                }
            )

    report = {
        "queries": len(queries),
        "tested": tested,
        "skipped_duplicate": skipped_duplicate,
        "skipped_missing": skipped_missing,
        "reference_images": {
            label: len(data["paths"]) for label, data in references.items()
        },
        "global_vectors": len(global_matrix),
        "results": results,
        "best": best,
        "best_records": records.get(best["name"], []) if best else [],
        "monthly": monthly_rows,
    }
    (OUT / "README.md").write_text(
        "# Experimental whitening fingerprints: Zorge / Dachnaya\n\n"
        "Read-only experiment, not connected to production.\n\n"
        "- `fingerprints/<variant>/<label>/` — embeddings, centroid, "
        "descriptors, 16 representatives and metadata for each variant.\n"
        "- `transforms/<variant>/` — PCA mean, components and explained "
        "variance needed to transform a query embedding.\n"
        "- `report.json` — all combinations and per-photo records of the "
        "best combination.\n\n"
        "A query must be transformed with the same `transforms/<variant>` "
        "before comparing with `fingerprints/<variant>/<label>`.\n",
        encoding="utf-8",
    )
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Whitening для слепков Зорге / Дачная",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и production-слепки "
        "не изменялись.",
        "",
        f"Запросов в базе: **{len(queries)}**; проверено: **{tested}**; "
        f"исключено точных дублей эталонов: **{skipped_duplicate}**; "
        f"пропущено без файла: {skipped_missing}.",
        "",
        f"Эталоны: Дачная — {len(references['dachnaya']['paths'])} фото, "
        f"Зорге — {len(references['zorge']['paths'])} фото. "
        f"Глобальный whitening обучен на {len(global_matrix)} векторах "
        f"остальных активных слепков (без 51_v35/92_v35).",
        "",
        "## Результаты",
        "",
        "| Вариант | Метод | Верно | Всего | Точность | Дачная | Зорге |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        dachnaya = item["class_accuracy"].get("dachnaya")
        zorge = item["class_accuracy"].get("zorge")
        lines.append(
            f"| `{item['variant']}` | `{item['method']}` | {item['correct']} | "
            f"{item['total']} | {item['accuracy']*100:.2f}% | "
            f"{(dachnaya*100 if dachnaya is not None else 0):.1f}% | "
            f"{(zorge*100 if zorge is not None else 0):.1f}% |"
        )

    if best is not None:
        lines += [
            "",
            f"Лучший вариант: **`{best['name']}`** — "
            f"{best['correct']}/{best['total']} ({best['accuracy']*100:.2f}%).",
            "",
            "## Ошибки лучшего варианта",
            "",
            "| Ожидалось → предсказано | Кол-во |",
            "|---|---:|",
        ]
        for pair in best["wrong_pairs"]:
            lines.append(
                f"| {pair['expected']} → {pair['predicted']} | {pair['count']} |"
            )

    lines += [
        "",
        "## Ограничения",
        "",
        "- Локальный whitening обучен на 68 эталонных кадрах двух адресов; "
        "это мало, поэтому добавлены варианты с глобальным whitening.",
        "- Глобальный whitening обучен без 51_v35/92_v35, но на остальных "
        "слепках корпуса; это не полностью независимый holdout.",
        "- Точные дубли файлов исключены, но похожие кадры одной серии могли "
        "остаться.",
        "- Оценка бинарная: только Дачная против Зорге/Стачки; остальные "
        "адреса в этом прогоне не участвуют.",
        "- Для production нужен новый формат слепка: transform, версия и "
        "пересборка FAISS.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[white] report: {REPORT}", flush=True)
    print(json.dumps(best, ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

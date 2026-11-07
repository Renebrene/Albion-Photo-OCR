#!/usr/bin/env python3
"""Read-only multi-class whitening check on all labelled photos.

Builds whitened versions of all active fingerprints (PCA whitening fitted on
the reference embeddings) and evaluates them against every corpus photo whose
filename identifies an address.  Raw embeddings are the control.

The query embeddings are cached in
`data/experiments/whitening_all/query_embeddings.npy`, so a rerun does not
repeat DINO inference.

Nothing is written to PostgreSQL or to production fingerprints.

    .venv/bin/python scripts/whitening_all_labeled_experiment.py

Outputs:
    data/experiments/whitening_all/report.json
    data/reports/whitening_all_labeled_YYYYMMDD.md
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
from app.ingest.database import get_connection  # noqa: E402
from scripts import hybrid_weight_experiment as hwe  # noqa: E402
from scripts.dino_v35_experiment import query_path  # noqa: E402
from scripts.evaluate_sorting import fingerprint_addresses  # noqa: E402

OUT = Path("data/experiments/whitening_all")
REPORT = Path(f"data/reports/whitening_all_labeled_{date.today():%Y%m%d}.md")

VARIANTS = {"raw": None, "white256": 256, "white512": 512}
METHODS = ("centroid", "best", "top3", "top5", "blend50")
EMBED_CHUNK = 256
EVAL_BATCH = 512


def l2_normalize(rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    if rows.ndim == 1:
        return rows / max(float(np.linalg.norm(rows)), 1e-9)
    return rows / np.maximum(
        np.linalg.norm(rows, axis=1, keepdims=True),
        1e-9,
    )


def file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def active_fingerprints() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.fingerprint_id, af.address_id
                FROM public.fingerprints AS f
                JOIN public.address_fingerprints AS af
                  ON af.fingerprint_id = f.fingerprint_id AND af.active
                WHERE f.active
                ORDER BY f.fingerprint_id
                """
            )
            return {
                str(row[0]): int(row[1]) for row in cur.fetchall()
            }


def load_references(embedder: SceneEmbedder):
    manager = FingerprintManager(settings, embedder)
    mapping = active_fingerprints()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fingerprint_id, source_folder FROM public.fingerprints"
            )
            db_folders = {
                str(row[0]): str(row[1]) if row[1] else None
                for row in cur.fetchall()
            }

    embeddings = []
    reference_addresses = []
    names_by_address: dict[int, set[str]] = defaultdict(set)
    paths_by_address: dict[int, list[Path]] = defaultdict(list)
    loaded = 0

    for fingerprint_id, address_id in mapping.items():
        address_id = hwe.CANONICAL_ADDRESS.get(address_id, address_id)
        try:
            data = manager.load(fingerprint_id)
        except (FileNotFoundError, ValueError, OSError) as exc:
            print(f"[all] skip {fingerprint_id}: {exc}", flush=True)
            continue

        matrix = l2_normalize(np.asarray(data["embeddings"], dtype=np.float32))
        embeddings.append(matrix)
        reference_addresses.extend([address_id] * len(matrix))
        loaded += 1

        metadata = data.get("metadata") or {}
        folder = metadata.get("source_folder") or db_folders.get(fingerprint_id)
        names = metadata.get("image_names") or []
        if folder and names:
            for name in names:
                names_by_address[address_id].add(str(name))
                paths_by_address[address_id].append(Path(str(folder)) / name)

    if not embeddings:
        raise RuntimeError("no active fingerprints loaded")

    matrix = np.vstack(embeddings)
    addresses = np.asarray(reference_addresses, dtype=np.int64)
    order = np.argsort(addresses, kind="stable")
    matrix = matrix[order]
    addresses = addresses[order]

    slices: dict[int, slice] = {}
    start = 0
    for index in range(1, len(addresses) + 1):
        if index == len(addresses) or addresses[index] != addresses[start]:
            slices[int(addresses[start])] = slice(start, index)
            start = index

    print(
        f"[all] fingerprints={loaded} vectors={len(matrix)} "
        f"addresses={len(slices)}",
        flush=True,
    )
    return {
        "matrix": matrix,
        "addresses": addresses,
        "slices": slices,
        "fingerprints": loaded,
        "names_by_address": names_by_address,
        "paths_by_address": paths_by_address,
    }


def fit_transforms(matrix: np.ndarray) -> dict[str, PCA | None]:
    transforms: dict[str, PCA | None] = {"raw": None}
    for name, components in VARIANTS.items():
        if components is None:
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
        print(f"[all] fitted {name}: {count} components", flush=True)
    return transforms


def save_artifacts(transforms: dict[str, PCA | None], data: dict[str, dict]):
    for name, model in transforms.items():
        if model is None:
            continue
        out = OUT / "transforms" / name
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "mean.npy", model.mean_)
        np.save(out / "components.npy", model.components_)
        np.save(out / "explained_variance.npy", model.explained_variance_)
        (out / "metadata.json").write_text(
            json.dumps(
                {
                    "variant": name,
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

    for name, per_variant in data.items():
        out = OUT / "centroids" / name
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "centroids.npy", per_variant["centroids"])
        (out / "address_order.json").write_text(
            json.dumps(per_variant["address_order"]),
            encoding="utf-8",
        )


def transform_rows(model: PCA | None, rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    if model is None:
        return l2_normalize(rows)
    return l2_normalize(model.transform(rows))


def variant_data(references: dict, model: PCA | None):
    matrix = transform_rows(model, references["matrix"])
    centroids = []
    address_order = list(references["slices"])
    for address_id in address_order:
        block = matrix[references["slices"][address_id]]
        centroids.append(l2_normalize(block.mean(axis=0)))
    return {
        "matrix": matrix,
        "centroids": np.stack(centroids),
        "address_order": address_order,
        "address_to_index": {
            address_id: index
            for index, address_id in enumerate(address_order)
        },
    }


def reference_hashes_by_size(
    references: dict,
    query_sizes: set[int],
    max_hashes: int = 20000,
) -> dict[int, set[str]]:
    """Hashes of reference files whose size occurs among the queries.

    Exact duplicate protection without reading every reference file: files
    whose size is not present in the query set cannot be duplicates.
    """

    result: dict[int, set[str]] = defaultdict(set)
    hashed = 0
    for paths in references["paths_by_address"].values():
        for path in paths:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size not in query_sizes:
                continue
            if hashed >= max_hashes:
                break
            digest = file_hash(path)
            if digest:
                result[size].add(digest)
                hashed += 1

    print(
        f"[all] reference hashes for duplicate check: {hashed}",
        flush=True,
    )
    return result


def load_queries(references: dict, expected: dict[str, int | None]):
    ids = [photo_id for photo_id, value in expected.items() if value is not None]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, filename, source_path
                FROM public.photos
                WHERE photo_id = ANY(%s)
                """,
                (ids,),
            )
            rows = cur.fetchall()

    query_sizes = set()
    for _photo_id, _filename, source_path in rows:
        try:
            query_sizes.add(Path(str(source_path or "")).stat().st_size)
        except OSError:
            continue

    reference_hashes = reference_hashes_by_size(references, query_sizes)

    queries = []
    duplicates = 0
    missing = 0

    for photo_id, filename, source_path in rows:
        expected_id = expected.get(str(photo_id))
        if expected_id is None:
            continue

        source = Path(str(source_path or ""))
        try:
            size = source.stat().st_size
        except OSError:
            size = None

        if size is not None and size in reference_hashes:
            digest = file_hash(source)
            if digest in reference_hashes[size]:
                duplicates += 1
                continue

        path = query_path(str(photo_id), str(source_path or ""))
        if not path.exists():
            missing += 1
            continue

        queries.append(
            (
                str(photo_id),
                str(filename),
                str(path),
                expected_id,
            )
        )

    print(
        f"[all] queries={len(queries)} duplicates={duplicates} "
        f"missing={missing}",
        flush=True,
    )
    return queries, duplicates, missing


def production_baseline(queries: list[tuple], expected: dict[str, int | None]):
    """Current production HYBRID result on exactly the same query set."""

    ids = [row[0] for row in queries]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, hybrid_final_id
                FROM public.hybrid_results
                WHERE hybrid_run_id = 11
                  AND status = 'DONE'
                  AND photo_id = ANY(%s)
                """,
                (ids,),
            )
            finals = {
                str(row[0]): str(row[1]) if row[1] else None
                for row in cur.fetchall()
            }

    fp_to_address = fingerprint_addresses()
    correct = total = unknown = 0
    for photo_id in ids:
        expected_id = expected.get(photo_id)
        if expected_id is None:
            continue
        total += 1
        fingerprint_id = finals.get(photo_id)
        address_id = (
            fp_to_address.get(fingerprint_id) if fingerprint_id else None
        )
        if address_id is None:
            unknown += 1
        elif address_id == expected_id:
            correct += 1

    return {
        "correct": correct,
        "total": total,
        "unknown": unknown,
        "accuracy": correct / total if total else 0.0,
    }


def embed_queries(embedder: SceneEmbedder, queries: list[tuple]):
    ids = [row[0] for row in queries]
    cache_ids = OUT / "query_ids.json"
    cache_embeddings = OUT / "query_embeddings.npy"

    if cache_ids.exists() and cache_embeddings.exists():
        cached = json.loads(cache_ids.read_text(encoding="utf-8"))
        if cached == ids:
            matrix = np.load(cache_embeddings)
            print(
                f"[all] cached query embeddings: {matrix.shape}",
                flush=True,
            )
            return matrix

    vectors = []
    total = len(queries)
    for start in range(0, total, EMBED_CHUNK):
        chunk = queries[start:start + EMBED_CHUNK]
        paths = [row[2] for row in chunk]
        try:
            batch = embedder.embed_paths(paths)
        except Exception:  # noqa: BLE001 - one broken image, not the chunk
            parts = []
            for path in paths:
                try:
                    parts.append(embedder.embed_paths([path])[0])
                except Exception as exc:  # noqa: BLE001
                    print(f"[all] skip {path}: {exc}", flush=True)
                    parts.append(np.zeros(768, dtype=np.float32))
            batch = np.stack(parts)
        vectors.append(np.asarray(batch, dtype=np.float32))
        done = min(start + EMBED_CHUNK, total)
        print(f"[all] embedded {done}/{total}", flush=True)

    matrix = l2_normalize(np.vstack(vectors))
    np.save(cache_embeddings, matrix)
    cache_ids.write_text(json.dumps(ids), encoding="utf-8")
    return matrix


def evaluate(
    queries: list[tuple],
    query_embeddings: np.ndarray,
    transforms: dict[str, PCA | None],
    data: dict[str, dict],
    reference_slices: dict[int, slice],
):
    predictions: dict[str, dict[str, np.ndarray]] = {}
    address_orders: dict[str, list[int]] = {}

    for variant, model in transforms.items():
        per_variant = data[variant]
        query_matrix = transform_rows(model, query_embeddings)
        address_order = per_variant["address_order"]
        matrix = per_variant["matrix"]
        centroids = per_variant["centroids"]

        predictions[variant] = {
            method: np.empty(len(queries), dtype=np.int32)
            for method in METHODS
        }

        for start in range(0, len(queries), EVAL_BATCH):
            stop = min(start + EVAL_BATCH, len(queries))
            block = query_matrix[start:stop]
            similarities = block @ matrix.T
            scores: dict[str, np.ndarray] = {
                "centroid": block @ centroids.T,
                "best": np.empty(
                    (len(block), len(address_order)), dtype=np.float32
                ),
                "top3": np.empty(
                    (len(block), len(address_order)), dtype=np.float32
                ),
                "top5": np.empty(
                    (len(block), len(address_order)), dtype=np.float32
                ),
            }

            for index, address_id in enumerate(address_order):
                cell = similarities[:, reference_slices[address_id]]
                scores["best"][:, index] = cell.max(axis=1)
                for k, method in ((3, "top3"), (5, "top5")):
                    count = min(k, cell.shape[1])
                    part = np.partition(
                        cell, cell.shape[1] - count, axis=1
                    )[:, -count:]
                    scores[method][:, index] = part.mean(axis=1)

            scores["blend50"] = (
                0.5 * scores["centroid"] + 0.5 * scores["best"]
            )

            for method in METHODS:
                predictions[variant][method][start:stop] = scores[
                    method
                ].argmax(axis=1)

        address_orders[variant] = address_order

    return predictions, address_orders


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
    expected = hwe.labeled_context()
    labelled_total = sum(1 for value in expected.values() if value is not None)

    transforms = fit_transforms(references["matrix"])
    data = {
        name: variant_data(references, model)
        for name, model in transforms.items()
    }
    save_artifacts(transforms, data)

    queries, duplicates, missing = load_queries(references, expected)
    if args.limit:
        queries = queries[: args.limit]
    production = production_baseline(queries, expected)
    query_embeddings = embed_queries(embedder, queries)

    predictions, address_orders = evaluate(
        queries,
        query_embeddings,
        transforms,
        data,
        references["slices"],
    )

    expected = np.asarray([row[3] for row in queries], dtype=np.int64)
    results = []
    per_photo = {}
    for variant in transforms:
        address_order = address_orders[variant]
        address_to_index = {
            address_id: index
            for index, address_id in enumerate(address_order)
        }
        expected_index = np.asarray(
            [
                address_to_index.get(int(address_id), -1)
                for address_id in expected
            ],
            dtype=np.int32,
        )
        covered = expected_index >= 0
        for method in METHODS:
            predicted_index = predictions[variant][method]
            correct = predicted_index == expected_index
            results.append(
                {
                    "name": f"{variant}|{method}",
                    "variant": variant,
                    "method": method,
                    "correct": int(correct[covered].sum()),
                    "total": int(covered.sum()),
                    "accuracy": (
                        float(correct[covered].mean())
                        if covered.any()
                        else 0.0
                    ),
                    "uncovered": int((~covered).sum()),
                }
            )
            per_photo[f"{variant}|{method}"] = predicted_index.copy()

    results.sort(key=lambda item: (-item["correct"], item["name"]))
    best = results[0] if results else None

    # Per-address recall of the best combination.
    address_recall = []
    if best is not None:
        address_order = address_orders[best["variant"]]
        predicted = per_photo[best["name"]]
        address_to_index = {
            address_id: index
            for index, address_id in enumerate(address_order)
        }
        stats = defaultdict(Counter)
        for expected_id, predicted_index in zip(expected, predicted):
            expected_id = int(expected_id)
            stats[expected_id]["total"] += 1
            if address_to_index.get(expected_id) == predicted_index:
                stats[expected_id]["correct"] += 1
        for address_id, counter in stats.items():
            if counter["total"] >= 20:
                address_recall.append(
                    {
                        "address_id": address_id,
                        "name": hwe.ADDRESS_NAMES.get(address_id, ""),
                        "correct": counter["correct"],
                        "total": counter["total"],
                        "accuracy": counter["correct"] / counter["total"],
                    }
                )
        address_recall.sort(key=lambda item: item["accuracy"])

    # Paired raw vs best white.
    paired = None
    if best is not None and best["variant"] != "raw":
        raw_key = f"raw|{best['method']}"
        white_key = best["name"]
        if raw_key in per_photo:
            raw_pred = per_photo[raw_key]
            white_pred = per_photo[white_key]
            address_order = address_orders["raw"]
            address_to_index = {
                address_id: index
                for index, address_id in enumerate(address_order)
            }
            better = worse = 0
            for expected_id, raw_index, white_index in zip(
                expected, raw_pred, white_pred
            ):
                expected_index = address_to_index.get(int(expected_id), -1)
                raw_ok = raw_index == expected_index
                white_ok = white_index == expected_index
                if white_ok and not raw_ok:
                    better += 1
                elif raw_ok and not white_ok:
                    worse += 1
            paired = {"better": better, "worse": worse, "net": better - worse}

    best_predictions = []
    if best is not None:
        best_order = address_orders[best["variant"]]
        for index, (
            (photo_id, filename, _path, _expected),
            predicted_index,
        ) in enumerate(zip(queries, per_photo[best["name"]])):
            best_predictions.append(
                {
                    "photo_id": photo_id,
                    "filename": filename,
                    "expected": int(expected[index]),
                    "predicted": int(best_order[int(predicted_index)]),
                }
            )

    covered_total = results[0]["total"] if results else 0
    report = {
        "labelled": labelled_total,
        "queries": len(queries),
        "covered": covered_total,
        "duplicates": duplicates,
        "missing": missing,
        "reference_vectors": int(len(references["matrix"])),
        "fingerprints": int(references["fingerprints"]),
        "addresses": len(references["slices"]),
        "results": results,
        "best": best,
        "production": production,
        "address_recall": address_recall[:15],
        "paired": paired,
        "best_predictions": best_predictions,
    }
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Многоклассовый whitening по всем подписанным фото",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и production-слепки "
        "не изменялись.",
        "",
        f"Подписанных фото: **{labelled_total}**; точных дублей эталонов "
        f"исключено: **{duplicates}**; запросов: **{len(queries)}** "
        f"(без файла: {missing}); покрыто слепками: **{covered_total}**; "
        f"без слепка: {len(queries) - covered_total}.",
        f"Слепков: **{references['fingerprints']}**, адресов: "
        f"**{len(references['slices'])}**, эталонных векторов: "
        f"{len(references['matrix'])}.",
        "",
        f"Текущий production (global + дескрипторы + HYBRID) на этом же наборе: "
        f"**{production['correct']}/{production['total']} "
        f"({production['accuracy']*100:.2f}%)**.",
        "",
        "PCA whitening обучен на эталонных эмбеддингах всех активных слепков. "
        "Запросы преобразуются тем же transform.",
        "",
        "| Комбинация | Верно | Всего | Точность |",
        "|---|---:|---:|---:|",
    ]
    for item in results:
        lines.append(
            f"| `{item['name']}` | {item['correct']} | {item['total']} | "
            f"{item['accuracy']*100:.2f}% |"
        )

    if best is not None:
        lines += [
            "",
            f"Лучшая комбинация: **`{best['name']}`** — "
            f"{best['correct']}/{best['total']} ({best['accuracy']*100:.2f}%).",
        ]
    if paired is not None:
        lines += [
            "",
            f"Парно к raw с тем же методом: лучше **{paired['better']}**, "
            f"хуже **{paired['worse']}**, чистое изменение "
            f"**{paired['net']:+d}**.",
        ]

    if address_recall:
        lines += [
            "",
            "## Худшие адреса у лучшей комбинации",
            "",
            "| Адрес | Верно | Всего | Точность |",
            "|---|---:|---:|---:|",
        ]
        for item in address_recall[:10]:
            lines.append(
                f"| {item['name']} | {item['correct']} | {item['total']} | "
                f"{item['accuracy']*100:.2f}% |"
            )

    lines += [
        "",
        "## Ограничения",
        "",
        "- PCA обучена на эталонных слепках, а запросы — те же адреса; это "
        "независимые кадры, но не независимые адреса.",
        "- Точные дубли файлов исключены; близкие кадры одной серии могли "
        "остаться.",
        "- Оценивается только global-компонент; environment/color/spatial "
        "не участвуют.",
        "- Для production нужен новый формат слепка и пересборка FAISS.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[all] report: {REPORT}", flush=True)
    print(json.dumps(best, ensure_ascii=False, indent=2)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

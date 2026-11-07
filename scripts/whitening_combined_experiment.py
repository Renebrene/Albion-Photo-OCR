#!/usr/bin/env python3
"""Read-only combined experiment: whitened global + descriptors + HYBRID.

Uses the cached query embeddings and the white512 transform saved by
`whitening_all_labeled_experiment.py`.  Computes:

* raw centroid + descriptors (control);
* white512 centroid + descriptors;
* both with the current HYBRID rules (series, neighbours, best-image margin,
  switch gain) over the full run-11 photo order.

Nothing is written to PostgreSQL or to production fingerprints.

    .venv/bin/python scripts/whitening_combined_experiment.py

Outputs:
    data/experiments/whitening_combined/report.json
    data/reports/whitening_combined_YYYYMMDD.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.embedder import SceneEmbedder  # noqa: E402
from app.core.fingerprint import FingerprintManager  # noqa: E402
from app.core.scene_analyzer import CompactDescriptor  # noqa: E402
from app.hybrid.database import get_run_items  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from scripts import hybrid_weight_experiment as hwe  # noqa: E402
from scripts.comparison_combinations_experiment import (  # noqa: E402
    deterministic_order,
)
from scripts.dino_v35_experiment import query_path  # noqa: E402
from scripts.evaluate_sorting import fingerprint_addresses  # noqa: E402
from scripts.whitening_all_labeled_experiment import (  # noqa: E402
    active_fingerprints,
    l2_normalize,
)

OUT = Path("data/experiments/whitening_all")
COMBINED_OUT = Path("data/experiments/whitening_combined")
REPORT = Path(f"data/reports/whitening_combined_{date.today():%Y%m%d}.md")

WEIGHTS = {
    "base": (0.70, 0.20, 0.07, 0.03),
    "env": (0.60, 0.30, 0.07, 0.03),
}
EVAL_BATCH = 256
EMBED_CHUNK = 256


def load_transform():
    base = OUT / "transforms" / "white512"
    mean = np.load(base / "mean.npy")
    components = np.load(base / "components.npy")
    variance = np.load(base / "explained_variance.npy")
    return mean, components, np.sqrt(np.maximum(variance, 1e-12))


def apply_white(query: np.ndarray, transform) -> np.ndarray:
    mean, components, scale = transform
    rows = np.asarray(query, dtype=np.float32)
    return l2_normalize(((rows - mean) @ components.T) / scale)


def load_reference_data(embedder: SceneEmbedder):
    manager = FingerprintManager(settings, embedder)
    mapping = active_fingerprints()

    rows = []
    address_ids = []
    env_rows = []
    color_rows = []
    spatial_rows = []
    canonical_fingerprint: dict[int, str] = {}

    for fingerprint_id, address_id in sorted(mapping.items()):
        address_id = hwe.CANONICAL_ADDRESS.get(address_id, address_id)
        try:
            data = manager.load(fingerprint_id)
        except (FileNotFoundError, ValueError, OSError) as exc:
            print(f"[comb] skip {fingerprint_id}: {exc}", flush=True)
            continue

        embeddings = l2_normalize(np.asarray(data["embeddings"]))
        rows.append(embeddings)
        address_ids.extend([address_id] * len(embeddings))
        env_rows.append(np.asarray(data["environment_embeddings"]))
        color_rows.append(np.asarray(data["color_embeddings"]))
        spatial_rows.append(np.asarray(data["spatial_embeddings"]))
        canonical_fingerprint.setdefault(address_id, fingerprint_id)

    matrix = np.vstack(rows)
    address_array = np.asarray(address_ids, dtype=np.int64)
    order = np.argsort(address_array, kind="stable")
    matrix = matrix[order]
    address_array = address_array[order]
    environment = np.vstack(env_rows)[order]
    color = np.vstack(color_rows)[order]
    spatial = np.vstack(spatial_rows)[order]

    slices: dict[int, slice] = {}
    start = 0
    for index in range(1, len(address_array) + 1):
        if index == len(address_array) or address_array[index] != address_array[start]:
            slices[int(address_array[start])] = slice(start, index)
            start = index

    address_order = list(slices)
    centroids = np.stack(
        [l2_normalize(matrix[slices[address_id]].mean(axis=0)) for address_id in address_order]
    )

    print(
        f"[comb] references={len(matrix)} addresses={len(address_order)} "
        f"fingerprints={len(canonical_fingerprint)}",
        flush=True,
    )
    return {
        "matrix": matrix,
        "environment": environment,
        "color": color,
        "spatial": spatial,
        "slices": slices,
        "address_order": address_order,
        "address_to_index": {
            address_id: index
            for index, address_id in enumerate(address_order)
        },
        "centroids": centroids,
        "canonical_fingerprint": canonical_fingerprint,
    }


def load_queries():
    ids = json.loads((OUT / "query_ids.json").read_text(encoding="utf-8"))
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
            rows = {
                str(row[0]): (str(row[1]), str(row[2] or ""))
                for row in cur.fetchall()
            }

    queries = []
    for photo_id in ids:
        filename, source_path = rows.get(photo_id, ("", ""))
        queries.append(
            (
                photo_id,
                filename,
                query_path(photo_id, source_path),
            )
        )
    return queries


def load_query_descriptors(queries: list[tuple]):
    cache = COMBINED_OUT / "query_descriptors.npz"
    ids = [row[0] for row in queries]
    if cache.exists():
        data = np.load(cache, allow_pickle=False)
        if [str(value) for value in data["ids"]] == ids:
            print("[comb] cached query descriptors", flush=True)
            return data["environment"], data["color"], data["spatial"]

    environment = []
    color = []
    spatial = []
    for index, (photo_id, _filename, path) in enumerate(queries, 1):
        try:
            image = CompactDescriptor._load(path)
            env, col, spa = CompactDescriptor.all_from_image(image)
        except Exception as exc:  # noqa: BLE001 - one bad image
            print(f"[comb] descriptor skip {photo_id}: {exc}", flush=True)
            env = np.zeros(640, dtype=np.float32)
            col = np.zeros(48, dtype=np.float32)
            spa = np.zeros(32, dtype=np.float32)
        environment.append(env)
        color.append(col)
        spatial.append(spa)
        if index % 2000 == 0:
            print(f"[comb] descriptors {index}/{len(queries)}", flush=True)

    environment = np.stack(environment).astype(np.float32)
    color = np.stack(color).astype(np.float32)
    spatial = np.stack(spatial).astype(np.float32)
    np.savez_compressed(
        cache,
        ids=np.asarray(ids),
        environment=environment,
        color=color,
        spatial=spatial,
    )
    return environment, color, spatial


def top_k_mean(values: np.ndarray, k: int) -> np.ndarray:
    count = min(k, values.shape[1])
    part = np.partition(values, values.shape[1] - count, axis=1)[:, -count:]
    return part.mean(axis=1)


def descriptor_scores(
    query: np.ndarray,
    reference: np.ndarray,
    address_order: list[int],
    slices: dict[int, slice],
):
    similarities = query @ reference.T
    result = np.empty((len(query), len(address_order)), dtype=np.float32)
    for index, address_id in enumerate(address_order):
        cell = similarities[:, slices[address_id]]
        k = max(3, int(cell.shape[1] * 0.10))
        result[:, index] = top_k_mean(cell, k)
    return result


def score_queries(
    query_embeddings: np.ndarray,
    environment: np.ndarray,
    color: np.ndarray,
    spatial: np.ndarray,
    references: dict,
    transform,
):
    address_order = references["address_order"]
    slices = references["slices"]
    white_queries = apply_white(query_embeddings, transform)

    methods: dict[str, np.ndarray] = {}
    for batch_start in range(0, len(query_embeddings), EVAL_BATCH):
        stop = min(batch_start + EVAL_BATCH, len(query_embeddings))
        white_block = white_queries[batch_start:stop]
        raw_block = query_embeddings[batch_start:stop]

        white_centroid = white_block @ references["centroids_white"].T
        raw_centroid = raw_block @ references["centroids_raw"].T
        white_best = np.empty((len(white_block), len(address_order)), dtype=np.float32)
        white_similarity = white_block @ references["matrix_white"].T
        for index, address_id in enumerate(address_order):
            white_best[:, index] = white_similarity[:, slices[address_id]].max(axis=1)

        env = descriptor_scores(
            environment[batch_start:stop],
            references["environment"],
            address_order,
            slices,
        )
        col = descriptor_scores(
            color[batch_start:stop],
            references["color"],
            address_order,
            slices,
        )
        spa = descriptor_scores(
            spatial[batch_start:stop],
            references["spatial"],
            address_order,
            slices,
        )

        block_methods = {
            "raw_centroid": raw_centroid,
            "white_centroid": white_centroid,
            "white_best": white_best,
            "environment": env,
            "color": col,
            "spatial": spa,
        }
        for name, (wg, we, wc, ws) in WEIGHTS.items():
            block_methods[f"raw_{name}"] = (
                wg * raw_centroid + we * env + wc * col + ws * spa
            )
            block_methods[f"white_{name}"] = (
                wg * white_centroid + we * env + wc * col + ws * spa
            )

        for name, values in block_methods.items():
            methods.setdefault(
                name, np.empty((len(query_embeddings), len(address_order)), dtype=np.float32)
            )[batch_start:stop] = values

        print(f"[comb] scored {stop}/{len(query_embeddings)}", flush=True)

    return methods


def build_hybrid_items(
    base_items,
    methods: dict[str, np.ndarray],
    method_name: str,
    references: dict,
    query_ids: list[str],
):
    items = list(base_items)
    address_order = references["address_order"]
    canonical = references["canonical_fingerprint"]
    fp_to_address = fingerprint_addresses()

    # Canonicalise series ids to the same fingerprint ids used in candidates.
    for index, item in enumerate(items):
        item = replace(
            item,
            series_fp=(
                canonical.get(fp_to_address.get(str(item.series_fp)), None)
                if item.series_fp
                else None
            ),
        )
        items[index] = item

    original_best_ids = [item.dino_best_id for item in items]
    scores = methods[method_name]
    index_by_photo = {
        item.photo_id: index for index, item in enumerate(items)
    }

    for row_index, photo_id in enumerate(query_ids):
        item_index = index_by_photo.get(photo_id)
        if item_index is None:
            continue
        row = scores[row_index]
        ranked = np.argsort(row)[-15:][::-1]
        candidates = []
        for address_index in ranked:
            address_id = address_order[int(address_index)]
            fingerprint_id = canonical.get(address_id)
            if fingerprint_id is None:
                continue
            candidates.append(
                {
                    "id": fingerprint_id,
                    "score": float(row[address_index]),
                    "best_image_score": float(row[address_index]),
                }
            )
        if not candidates:
            continue
        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        items[item_index] = replace(
            items[item_index],
            candidates=candidates,
            dino_best_id=best["id"],
            dino_score=best["score"],
            dino_second_score=second["score"] if second else None,
            dino_margin=(
                best["score"] - second["score"] if second else None
            ),
        )
        original_best_ids[item_index] = best["id"]

    return items, original_best_ids


def evaluate_finals(
    items,
    finals,
    expected: dict[str, int | None],
    fp_to_address: dict[str, int],
    photo_ids: set[str] | None = None,
):
    stats = Counter()
    wrong = Counter()
    for item, final_id in zip(items, finals):
        if photo_ids is not None and item.photo_id not in photo_ids:
            continue
        expected_id = expected.get(item.photo_id)
        if expected_id is None:
            continue
        predicted_id = (
            fp_to_address.get(str(final_id)) if final_id else None
        )
        if predicted_id is not None:
            predicted_id = hwe.CANONICAL_ADDRESS.get(
                predicted_id, predicted_id
            )
        stats["total"] += 1
        if predicted_id is None:
            stats["unknown"] += 1
        elif predicted_id == expected_id:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            wrong[(expected_id, predicted_id)] += 1
    return stats, wrong


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-hybrid", action="store_true")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="smoke test: only the first N queries (0 = all)",
    )
    args = parser.parse_args(argv)

    COMBINED_OUT.mkdir(parents=True, exist_ok=True)
    embedder = SceneEmbedder(settings)

    query_embeddings = np.load(OUT / "query_embeddings.npy")
    queries = load_queries()
    query_ids = [row[0] for row in queries]
    if args.limit:
        query_embeddings = query_embeddings[: args.limit]
        queries = queries[: args.limit]
        query_ids = query_ids[: args.limit]
    print(f"[comb] queries={len(queries)}", flush=True)

    references = load_reference_data(embedder)
    transform = load_transform()
    references["matrix_white"] = apply_white(
        references["matrix"], transform
    )
    references["centroids_raw"] = references["centroids"]
    references["centroids_white"] = np.stack(
        [
            l2_normalize(
                references["matrix_white"][
                    references["slices"][address_id]
                ].mean(axis=0)
            )
            for address_id in references["address_order"]
        ]
    )

    environment, color, spatial = load_query_descriptors(queries)
    methods = score_queries(
        query_embeddings,
        environment,
        color,
        spatial,
        references,
        transform,
    )

    expected = hwe.labeled_context()
    fp_to_address = fingerprint_addresses()
    address_order = references["address_order"]
    address_to_index = references["address_to_index"]
    expected_array = np.asarray(
        [expected.get(photo_id, -1) for photo_id in query_ids],
        dtype=np.int64,
    )
    covered = expected_array >= 0

    results = []
    predictions = {}
    for name, scores in methods.items():
        predicted_index = scores.argmax(axis=1)
        predictions[name] = predicted_index
        expected_index = np.asarray(
            [
                address_to_index.get(int(address_id), -1)
                for address_id in expected_array
            ],
            dtype=np.int32,
        )
        correct = predicted_index == expected_index
        results.append(
            {
                "name": name,
                "correct": int(correct[covered].sum()),
                "total": int(covered.sum()),
                "accuracy": float(correct[covered].mean()),
            }
        )
    results.sort(key=lambda item: (-item["correct"], item["name"]))

    hybrid = {}
    if not args.skip_hybrid:
        base_items = deterministic_order(hwe.get_run_items(11))
        for method_name in ("raw_env", "white_env", "white_base", "raw_base"):
            print(f"[comb] HYBRID on {method_name}", flush=True)
            items, original_best = build_hybrid_items(
                base_items,
                methods,
                method_name,
                references,
                query_ids,
            )
            finals = hwe.simulate(items, original_best)
            stats, wrong = evaluate_finals(
                items, finals, expected, fp_to_address, set(query_ids)
            )
            hybrid[method_name] = {
                "correct": stats["correct"],
                "wrong": stats["wrong"],
                "unknown": stats["unknown"],
                "total": stats["total"],
                "accuracy": (
                    stats["correct"] / stats["total"]
                    if stats["total"]
                    else 0.0
                ),
                "wrong_pairs": [
                    {
                        "expected": expected_id,
                        "expected_name": hwe.ADDRESS_NAMES.get(expected_id, ""),
                        "predicted": predicted_id,
                        "predicted_name": hwe.ADDRESS_NAMES.get(predicted_id, ""),
                        "count": count,
                    }
                    for (expected_id, predicted_id), count in wrong.most_common(8)
                ],
            }

    production = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, hybrid_final_id
                FROM public.hybrid_results
                WHERE hybrid_run_id = 11 AND status = 'DONE' AND photo_id = ANY(%s)
                """,
                (query_ids,),
            )
            finals = {
                str(row[0]): str(row[1]) if row[1] else None
                for row in cur.fetchall()
            }
    production_stats = Counter()
    for photo_id in query_ids:
        expected_id = expected.get(photo_id)
        if expected_id is None:
            continue
        production_stats["total"] += 1
        address_id = fp_to_address.get(finals.get(photo_id))
        if address_id is not None:
            address_id = hwe.CANONICAL_ADDRESS.get(address_id, address_id)
        if address_id is None:
            production_stats["unknown"] += 1
        elif address_id == expected_id:
            production_stats["correct"] += 1
        else:
            production_stats["wrong"] += 1
    production = {
        "correct": production_stats["correct"],
        "wrong": production_stats["wrong"],
        "unknown": production_stats["unknown"],
        "total": production_stats["total"],
        "accuracy": production_stats["correct"] / production_stats["total"],
    }

    report = {
        "queries": len(queries),
        "covered": int(covered.sum()),
        "results": results,
        "hybrid": hybrid,
        "production": production,
    }
    (COMBINED_OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Комбинированный whitening: centroid + дескрипторы + HYBRID",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и production-слепки "
        "не изменялись.",
        "",
        f"Запросов: **{len(queries)}**, покрыто слепками: **{int(covered.sum())}**. "
        f"Текущий production на этом наборе: **{production['correct']}/"
        f"{production['total']} ({production['accuracy']*100:.2f}%)**.",
        "",
        "## Top-1 без правил HYBRID",
        "",
        "| Комбинация | Верно | Всего | Точность |",
        "|---|---:|---:|---:|",
    ]
    for item in results:
        lines.append(
            f"| `{item['name']}` | {item['correct']} | {item['total']} | "
            f"{item['accuracy']*100:.2f}% |"
        )

    if hybrid:
        lines += [
            "",
            "## С правилами HYBRID",
            "",
            "| Комбинация | Верно | Неверно | Unknown | Точность |",
            "|---|---:|---:|---:|---:|",
        ]
        for name, item in sorted(
            hybrid.items(), key=lambda pair: -pair[1]["correct"]
        ):
            lines.append(
                f"| `{name}` | {item['correct']} | {item['wrong']} | "
                f"{item['unknown']} | {item['accuracy']*100:.2f}% |"
            )

        best_name, best_item = max(
            hybrid.items(), key=lambda pair: pair[1]["correct"]
        )
        counterpart = best_name.replace("white_", "raw_", 1)
        net = None
        if counterpart in hybrid:
            net = (
                best_item["correct"] - hybrid[counterpart]["correct"]
            )
        lines += [
            "",
            "## Вывод",
            "",
            f"Лучшая HYBRID-комбинация: **`{best_name}`** — "
            f"{best_item['correct']}/{best_item['total']} "
            f"({best_item['accuracy']*100:.2f}%).",
        ]
        if net is not None:
            lines.append(
                f"Чистый эффект whitening в той же симуляции "
                f"(`{best_name}` против `{counterpart}`): **{net:+d}** фото. "
                "Сравнение с production включает отличия методики симуляции "
                "(детерминированный порядок, один fingerprint на адрес, "
                "best_image заменён combined-score)."
            )

        for name, item in sorted(
            hybrid.items(), key=lambda pair: -pair[1]["correct"]
        )[:2]:
            lines += [
                "",
                f"### Ошибки `{name}`",
                "",
                "| Ожидалось → предсказано | Кол-во |",
                "|---|---:|",
            ]
            for pair in item["wrong_pairs"]:
                lines.append(
                    f"| {pair['expected_name']} → {pair['predicted_name']} | "
                    f"{pair['count']} |"
                )

    lines += [
        "",
        "## Ограничения",
        "",
        "- HYBRID-симуляция использует полный порядок run 11, но для "
        "неподписанных фото оставлены production-кандидаты: это контекст, "
        "а не часть оцениваемой выборки.",
        "- Кандидаты для подписанных фото — top-15 адресов по combined-score; "
        "best_image_score заменён на combined-score (в whitened-пространстве "
        "отдельный best не сохранялся).",
        "- Точные дубли эталонов исключены; близкие кадры серий могли остаться.",
        "- PCA обучена на эталонных эмбеддингах всех активных слепков; "
        "это не независимый holdout по адресам.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[comb] report: {REPORT}", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

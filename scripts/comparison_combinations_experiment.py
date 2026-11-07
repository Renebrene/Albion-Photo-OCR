#!/usr/bin/env python3
"""Point 9: combinations of DINO comparison methods on the existing corpus.

Read-only experiment.  It never writes to PostgreSQL or to production
fingerprints.  Two phases:

1. Full HYBRID run 11 (57 541 photos) using the already stored DINO
   candidates: global basis (centroid / best image / blend / max) x descriptor
   weights x decision rule (plain TOP-1 / current HYBRID rules), plus a small
   sweep of the HYBRID switch gain and best-image margin.

2. Stratified sample of labelled photos with query embeddings recomputed from
   the originals: centroid, best image, top-k means, multiple centroids,
   descriptor weights and per-address threshold calibration.

Outputs:
    data/experiments/comparison_combinations/report.json
    data/reports/comparison_combinations_YYYYMMDD.md

    .venv/bin/python scripts/comparison_combinations_experiment.py --phase all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date, datetime
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
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    fingerprint_addresses,
)

RUN_ID = 11
OUT = Path("data/experiments/comparison_combinations")
REPORT = Path(f"data/reports/comparison_combinations_{date.today():%Y%m%d}.md")

# Global similarity basis inside one fingerprint.
BASES = {
    "centroid": lambda global_score, best_image: global_score,
    "best_image": lambda global_score, best_image: best_image,
    "blend50": lambda global_score, best_image: 0.5 * global_score + 0.5 * best_image,
    "max": lambda global_score, best_image: max(global_score, best_image),
}

# Descriptor weights (global, environment, color, spatial).
WEIGHT_SETS = {
    "base": (0.70, 0.20, 0.07, 0.03),
    "no_color": (0.754, 0.216, 0.00, 0.03),
    "global_only": (1.00, 0.00, 0.00, 0.00),
    "env_heavy": (0.60, 0.30, 0.07, 0.03),
}

# Deep-sample global methods.
DEEP_METHODS = ("centroid", "best", "top3", "top5", "top10", "cluster4")

SWITCH_GAINS = (1.0, 1.5, 2.0, 3.0)
BEST_IMAGE_MARGINS = (0.005, 0.01, 0.02)


def deterministic_order(items):
    """Stable filename order with photo_id as the tie-breaker.

    Filenames are not unique (up to 36 photos share one name), so the bare
    ``ORDER BY filename`` in ``get_run_items()`` leaves ties to PostgreSQL.
    Both the production query and the experiment now pin them by photo_id.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT photo_id, filename FROM public.photos")
            filenames = {
                str(photo_id): str(filename or "")
                for photo_id, filename in cur.fetchall()
            }

    return sorted(
        items,
        key=lambda item: (
            filenames.get(item.photo_id, ""),
            item.photo_id,
        ),
    )


def candidate_basis_score(candidate: dict, basis: str) -> float:
    return float(
        BASES[basis](
            float(candidate["global_score"]),
            float(candidate["best_image_score"]),
        )
    )


def candidate_combined_score(
    candidate: dict,
    basis: str,
    weights: tuple[float, float, float, float],
) -> float:
    wg, we, wc, ws = weights
    return (
        wg * candidate_basis_score(candidate, basis)
        + we * float(candidate["environment_score"])
        + wc * float(candidate["color_score"])
        + ws * float(candidate["spatial_score"])
    )


def rescore_items(
    items,
    basis: str,
    weights: tuple[float, float, float, float],
):
    """Recompute candidate scores, TOP-1 and margin for one combination."""

    result = []

    for item in items:
        candidates = [
            {
                **candidate,
                "score": candidate_combined_score(candidate, basis, weights),
            }
            for candidate in item.candidates
        ]
        candidates.sort(key=lambda candidate: candidate["score"], reverse=True)

        best = candidates[0]["id"] if candidates else None
        best_score = candidates[0]["score"] if candidates else None
        second_score = candidates[1]["score"] if len(candidates) > 1 else None
        margin = (
            best_score - second_score
            if best_score is not None and second_score is not None
            else None
        )

        result.append(
            replace(
                item,
                candidates=candidates,
                dino_best_id=best,
                dino_score=best_score,
                dino_second_score=second_score,
                dino_margin=margin,
            )
        )

    return result


def score_for(item, fingerprint_id: str | None) -> float | None:
    if fingerprint_id is None:
        return None
    for candidate in item.candidates:
        if str(candidate["id"]) == str(fingerprint_id):
            return float(candidate["score"])
    return None


def address_scores(item) -> dict[str, float]:
    scores: dict[str, float] = {}
    for candidate in item.candidates:
        fingerprint_id = str(candidate.get("id"))
        if not fingerprint_id:
            continue
        scores[fingerprint_id] = max(
            scores.get(fingerprint_id, 0.0),
            float(candidate["score"]),
        )
    return scores


def evaluate_finals(scored, finals, expected, fp_to_address):
    """Compare final fingerprint ids with the address written in filenames."""

    stats = Counter()
    wrong_pairs: Counter = Counter()
    records = []

    for item, final_id in zip(scored, finals):
        expected_id = expected.get(item.photo_id)
        if expected_id is None:
            continue

        predicted_id = (
            fp_to_address.get(str(final_id)) if final_id is not None else None
        )

        stats["labelled"] += 1
        if predicted_id is None:
            stats["review"] += 1
        elif predicted_id == expected_id:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            wrong_pairs[(expected_id, predicted_id)] += 1

        by_address = address_scores(item)
        ranked = sorted(by_address.values(), reverse=True)
        address_margin = (
            ranked[0] - ranked[1] if len(ranked) > 1 else None
        )

        records.append(
            {
                "photo_id": item.photo_id,
                "expected": expected_id,
                "predicted": predicted_id,
                "score": score_for(item, final_id),
                "margin": item.dino_margin,
                "address_margin": address_margin,
                "correct": predicted_id == expected_id,
            }
        )

    stats["accuracy"] = (
        stats["correct"] / stats["labelled"] if stats["labelled"] else 0.0
    )
    return stats, wrong_pairs, records


def wrong_pair_rows(wrong_pairs: Counter, limit: int = 10) -> list[dict]:
    return [
        {
            "expected": expected_id,
            "expected_name": ADDRESS_NAMES.get(expected_id, ""),
            "predicted": predicted_id,
            "predicted_name": ADDRESS_NAMES.get(predicted_id, ""),
            "count": count,
        }
        for (expected_id, predicted_id), count in wrong_pairs.most_common(limit)
    ]


def full_corpus_phase(items, original_best_ids, expected, fp_to_address):
    production_final = hwe.simulate(items, original_best_ids)
    production_stats, _, _ = evaluate_finals(
        items, production_final, expected, fp_to_address
    )

    results = []
    best = None

    for basis in BASES:
        for weight_name, weights in WEIGHT_SETS.items():
            scored = rescore_items(items, basis, weights)

            for rule in ("top1", "hybrid", "hybrid_no_match"):
                if rule == "top1":
                    finals = [item.dino_best_id for item in scored]
                elif rule == "hybrid_no_match":
                    finals = hwe.simulate(
                        scored, original_best_ids, no_match=True
                    )
                else:
                    finals = hwe.simulate(scored, original_best_ids)

                stats, wrong_pairs, _ = evaluate_finals(
                    scored, finals, expected, fp_to_address
                )
                item = {
                    "name": f"{basis}|{weight_name}|{rule}",
                    "basis": basis,
                    "weights_name": weight_name,
                    "weights": {
                        "global": weights[0],
                        "environment": weights[1],
                        "color": weights[2],
                        "spatial": weights[3],
                    },
                    "rule": rule,
                    "labelled": stats["labelled"],
                    "correct": stats["correct"],
                    "wrong": stats["wrong"],
                    "review": stats["review"],
                    "accuracy": stats["accuracy"],
                    "delta_vs_production": (
                        stats["correct"] - production_stats["correct"]
                    ),
                    "wrong_pairs": wrong_pair_rows(wrong_pairs, 5),
                }
                results.append(item)

                if best is None or (
                    item["correct"], -item["wrong"]
                ) > (best["correct"], -best["wrong"]):
                    best = item

    # Rebuild the records of the best combination for threshold calibration.
    best_scored = rescore_items(items, best["basis"], tuple(best["weights"].values()))
    best_finals = (
        [item.dino_best_id for item in best_scored]
        if best["rule"] == "top1"
        else hwe.simulate(best_scored, original_best_ids)
    )
    _, _, best_records = evaluate_finals(
        best_scored, best_finals, expected, fp_to_address
    )

    # Paired comparison against production and stability by capture month.
    paired = Counter()
    monthly: dict[str, Counter] = defaultdict(Counter)
    for item, production_id, best_id in zip(
        items, production_final, best_finals
    ):
        expected_id = expected.get(item.photo_id)
        if expected_id is None:
            continue

        production_address = (
            fp_to_address.get(str(production_id))
            if production_id is not None
            else None
        )
        best_address = (
            fp_to_address.get(str(best_id)) if best_id is not None else None
        )
        production_ok = production_address == expected_id
        best_ok = best_address == expected_id

        if best_ok and not production_ok:
            paired["better"] += 1
        elif production_ok and not best_ok:
            paired["worse"] += 1

        month = (
            item.taken_at.strftime("%Y-%m") if item.taken_at else "unknown"
        )
        monthly[month]["total"] += 1
        monthly[month]["production_correct"] += int(production_ok)
        monthly[month]["best_correct"] += int(best_ok)

    paired["net"] = paired["better"] - paired["worse"]
    monthly_rows = [
        {
            "month": month,
            "total": counter["total"],
            "production_correct": counter["production_correct"],
            "best_correct": counter["best_correct"],
            "delta": counter["best_correct"] - counter["production_correct"],
        }
        for month, counter in sorted(monthly.items())
        if counter["total"] >= 50
    ]

    # HYBRID sensitivity around the best combination.
    sensitivity = []
    old_gain, old_margin = hwe.SWITCH_GAIN, hwe.BEST_IMAGE_MARGIN
    try:
        for gain in SWITCH_GAINS:
            for margin in BEST_IMAGE_MARGINS:
                hwe.SWITCH_GAIN = gain
                hwe.BEST_IMAGE_MARGIN = margin
                finals = hwe.simulate(best_scored, original_best_ids)
                stats, _, _ = evaluate_finals(
                    best_scored, finals, expected, fp_to_address
                )
                sensitivity.append(
                    {
                        "switch_gain": gain,
                        "best_image_margin": margin,
                        "correct": stats["correct"],
                        "wrong": stats["wrong"],
                        "review": stats["review"],
                        "accuracy": stats["accuracy"],
                    }
                )
    finally:
        hwe.SWITCH_GAIN = old_gain
        hwe.BEST_IMAGE_MARGIN = old_margin

    return {
        "items": len(items),
        "production": {
            "correct": production_stats["correct"],
            "wrong": production_stats["wrong"],
            "review": production_stats["review"],
            "accuracy": production_stats["accuracy"],
        },
        "combinations": results,
        "best": best,
        "best_records": best_records,
        "paired": dict(paired),
        "monthly": monthly_rows,
        "hybrid_sensitivity": sensitivity,
    }


def _fold(photo_id: str) -> int:
    return int(hashlib.md5(photo_id.encode("utf-8")).hexdigest(), 16) % 2


def _quantile(values: list[float], q: float, fallback: float) -> float:
    return float(np.percentile(values, q)) if values else fallback


def calibrate_thresholds(records, *, quantile: float = 10.0, min_samples: int = 5):
    """Global vs per-address review thresholds with a two-fold split."""

    usable = [record for record in records if record["expected"] is not None]
    for record in usable:
        record["fold"] = _fold(record["photo_id"])

    totals: dict[str, Counter] = {
        "global": Counter(),
        "per_address": Counter(),
        "fixed_065": Counter(),
        "margin_gate": Counter(),
    }

    for test_fold in (0, 1):
        train = [r for r in usable if r["fold"] != test_fold]
        test = [r for r in usable if r["fold"] == test_fold]

        correct_scores = [
            float(r["score"])
            for r in train
            if r["correct"] and r["score"] is not None
        ]
        global_threshold = _quantile(correct_scores, quantile, 0.65)

        per_address: dict[int, float] = {}
        by_address: dict[int, list[float]] = defaultdict(list)
        for record in train:
            if record["correct"] and record["score"] is not None:
                by_address[record["predicted"]].append(float(record["score"]))
        for address_id, values in by_address.items():
            per_address[address_id] = (
                _quantile(values, quantile, global_threshold)
                if len(values) >= min_samples
                else global_threshold
            )

        for record in test:
            score = record["score"]
            predicted = record["predicted"]
            correct = record["correct"]
            margin = record["margin"] or 0.0

            for scheme in ("global", "per_address", "fixed_065"):
                totals[scheme]["total"] += 1
                if scheme == "global":
                    threshold = global_threshold
                elif scheme == "per_address":
                    threshold = per_address.get(predicted, global_threshold)
                else:
                    threshold = 0.65

                trusted = score is not None and score >= threshold
                if trusted:
                    totals[scheme]["trusted"] += 1
                    if correct:
                        totals[scheme]["trusted_correct"] += 1
                    else:
                        totals[scheme]["wrong_trusted"] += 1
                else:
                    totals[scheme]["review"] += 1
                    if not correct:
                        totals[scheme]["wrong_review"] += 1

            # Production-like gate: score + margin.
            totals["margin_gate"]["total"] += 1
            trusted = (
                score is not None
                and score >= global_threshold
                and margin >= 0.005
            )
            if trusted:
                totals["margin_gate"]["trusted"] += 1
                if correct:
                    totals["margin_gate"]["trusted_correct"] += 1
                else:
                    totals["margin_gate"]["wrong_trusted"] += 1
            else:
                totals["margin_gate"]["review"] += 1
                if not correct:
                    totals["margin_gate"]["wrong_review"] += 1

    report = {}
    for scheme, counter in totals.items():
        trusted = counter["trusted"]
        report[scheme] = {
            "total": counter["total"],
            "trusted": trusted,
            "trusted_correct": counter["trusted_correct"],
            "trusted_accuracy": (
                counter["trusted_correct"] / trusted if trusted else None
            ),
            "review": counter["review"],
            "wrong_trusted": counter["wrong_trusted"],
            "wrong_review": counter["wrong_review"],
        }
    return report


def deep_phase(sample_target: int, expected, fp_to_address):
    import scripts.dino_comparison_experiment as dce

    old_target = dce.SAMPLE_TARGET
    dce.SAMPLE_TARGET = sample_target
    try:
        sample = dce.build_sample()
    finally:
        dce.SAMPLE_TARGET = old_target

    photo_rows = dce.load_photo_rows(sample)
    candidates = dce.load_candidates()

    embedder = SceneEmbedder(settings)
    manager = FingerprintManager(settings, embedder)
    cache = dce.FingerprintCache(manager)

    records_by_combo: dict[str, list[dict]] = {
        f"{method}|{weight_name}": []
        for method in DEEP_METHODS
        for weight_name in WEIGHT_SETS
    }
    errors_by_combo: dict[str, Counter] = defaultdict(Counter)

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
            image = CompactDescriptor._load(path)
            env, color, spatial = CompactDescriptor.all_from_image(image)
        except Exception as exc:  # noqa: BLE001 - one bad photo, not the run
            print(f"[deep] skip {photo_id}: {exc}", flush=True)
            skipped += 1
            continue

        expected_id = expected.get(photo_id)

        # Components per (address, method).  Multiple fingerprints can map to
        # the same address; the best fingerprint wins for each component.
        by_address: dict[int, dict[str, float]] = defaultdict(dict)

        for candidate in candidate_rows:
            fingerprint_id = candidate["fingerprint_id"]
            fingerprint = cache.get(fingerprint_id)
            if fingerprint is None:
                continue
            address_id = fp_to_address.get(fingerprint_id)
            if address_id is None:
                continue

            embeddings = fingerprint["embeddings"]
            centroid = fingerprint["centroid"]
            ref_scores = np.sort(embeddings @ query)[::-1]

            def top_k(k: int) -> float:
                if not len(ref_scores):
                    return 0.0
                return float(ref_scores[: min(k, len(ref_scores))].mean())

            components = {
                "centroid": float(query @ centroid),
                "best": float(ref_scores[0]) if len(ref_scores) else 0.0,
                "top3": top_k(3),
                "top5": top_k(5),
                "top10": top_k(10),
                "cluster4": float(np.max(fingerprint["clusters"] @ query)),
                "environment": dce.descriptor_similarity(
                    env, fingerprint["environment_embeddings"]
                ),
                "color": dce.descriptor_similarity(
                    color, fingerprint["color_embeddings"]
                ),
                "spatial": dce.descriptor_similarity(
                    spatial, fingerprint["spatial_embeddings"]
                ),
            }

            target = by_address[address_id]
            for key, value in components.items():
                target[key] = max(target.get(key, -1.0), value)

        if not by_address or expected_id is None:
            skipped += 1
            continue

        tested += 1

        for method in DEEP_METHODS:
            for weight_name, weights in WEIGHT_SETS.items():
                wg, we, wc, ws = weights
                scores = {
                    address_id: (
                        wg * components[method]
                        + we * components["environment"]
                        + wc * components["color"]
                        + ws * components["spatial"]
                    )
                    for address_id, components in by_address.items()
                }
                ranked = sorted(
                    scores.items(), key=lambda pair: pair[1], reverse=True
                )
                predicted_id, best_score = ranked[0]
                second_score = ranked[1][1] if len(ranked) > 1 else None

                combo = f"{method}|{weight_name}"
                correct = predicted_id == expected_id
                records_by_combo[combo].append(
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
                    errors_by_combo[combo][(expected_id, predicted_id)] += 1

        if index % 25 == 0:
            print(f"[deep] {index}/{len(sample)}", flush=True)

    results = []
    for combo, records in records_by_combo.items():
        if not records:
            continue
        correct = sum(1 for record in records if record["correct"])
        method, weight_name = combo.split("|")
        results.append(
            {
                "name": combo,
                "method": method,
                "weights_name": weight_name,
                "weights": dict(
                    zip(
                        ("global", "environment", "color", "spatial"),
                        WEIGHT_SETS[weight_name],
                    )
                ),
                "correct": correct,
                "total": len(records),
                "accuracy": correct / len(records),
                "wrong_pairs": [
                    {
                        "expected": expected_id,
                        "expected_name": ADDRESS_NAMES.get(expected_id, ""),
                        "predicted": predicted_id,
                        "predicted_name": ADDRESS_NAMES.get(predicted_id, ""),
                        "count": count,
                    }
                    for (expected_id, predicted_id), count in errors_by_combo[
                        combo
                    ].most_common(5)
                ],
            }
        )

    results.sort(key=lambda item: (-item["correct"], item["name"]))
    best = results[0] if results else None
    calibration = (
        calibrate_thresholds(records_by_combo[best["name"]]) if best else {}
    )

    return {
        "sample": len(sample),
        "tested": tested,
        "skipped": skipped,
        "fingerprints": len(cache.data),
        "combinations": results,
        "best": best,
        "calibration": calibration,
    }


def write_report(
    full: dict | None,
    deep: dict | None,
    run_id: int = 11,
) -> None:
    lines = [
        "# П. 9: комбинации способов сравнения DINO",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и production-слепки "
        "не изменялись.",
        "",
    ]

    if full is not None:
        production = full["production"]
        lines += [
            f"## 1. Полный корпус, run {run_id}",
            "",
            f"Фото: **{full['items']}**; production: "
            f"{production['correct']} верно, {production['wrong']} неверно, "
            f"{production['review']} Review, точность "
            f"{production['accuracy']*100:.2f}%.",
            "",
            "| Комбинация | Верно | Неверно | Review | Точность | Δ к production |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for item in sorted(
            full["combinations"],
            key=lambda row: (-row["correct"], row["wrong"], row["name"]),
        ):
            lines.append(
                f"| `{item['name']}` | {item['correct']} | {item['wrong']} | "
                f"{item['review']} | {item['accuracy']*100:.2f}% | "
                f"{item['delta_vs_production']:+d} |"
            )

        best = full["best"]
        lines += [
            "",
            "### Лучшая комбинация полного корпуса",
            "",
            f"**`{best['name']}`** — {best['correct']} верно, "
            f"{best['wrong']} неверно, точность {best['accuracy']*100:.2f}% "
            f"({best['delta_vs_production']:+d} к production).",
            "",
            "| Ожидалось → предсказано | Кол-во |",
            "|---|---:|",
        ]
        for pair in best["wrong_pairs"]:
            lines.append(
                f"| {pair['expected_name']} → {pair['predicted_name']} | "
                f"{pair['count']} |"
            )

        paired = full.get("paired") or {}
        lines += [
            "",
            f"Парное сравнение с production: лучше **{paired.get('better', 0)}**, "
            f"хуже **{paired.get('worse', 0)}**, чистое изменение "
            f"**{paired.get('net', 0):+d}** фото.",
            "",
            "### Стабильность по месяцам съёмки",
            "",
            "| Месяц | Фото | Production верно | Лучшая комбинация | Δ |",
            "|---|---:|---:|---:|---:|",
        ]
        for row in full.get("monthly") or []:
            lines.append(
                f"| {row['month']} | {row['total']} | "
                f"{row['production_correct']} | {row['best_correct']} | "
                f"{row['delta']:+d} |"
            )

        lines += [
            "",
            "### Чувствительность правил HYBRID (для лучшей комбинации)",
            "",
            "| switch gain | best_image margin | Верно | Неверно | Review | Точность |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
        for item in sorted(
            full["hybrid_sensitivity"],
            key=lambda row: (-row["correct"], row["switch_gain"]),
        ):
            lines.append(
                f"| {item['switch_gain']:.1f} | {item['best_image_margin']:.3f} | "
                f"{item['correct']} | {item['wrong']} | {item['review']} | "
                f"{item['accuracy']*100:.2f}% |"
            )

        calibration = calibrate_thresholds(full["best_records"])
        lines += [
            "",
            "### Калибровка порогов Review",
            "",
            "Двухфолдовая схема: порог по правильным ответам одной половины, "
            "проверка на другой. `per_address` — 10-й процентиль по адресу "
            "(не меньше 5 примеров, иначе глобальный порог).",
            "",
            "| Схема | Всего | Trusted | Верно в Trusted | Точность Trusted | "
            "Review | Ошибок в Trusted | Ошибок в Review |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for scheme, label in (
            ("fixed_065", "фиксированный 0.65"),
            ("global", "глобальный квантиль"),
            ("per_address", "по адресу"),
            ("margin_gate", "глобальный + margin ≥ 0.005"),
        ):
            item = calibration[scheme]
            accuracy = item["trusted_accuracy"]
            lines.append(
                f"| {label} | {item['total']} | {item['trusted']} | "
                f"{item['trusted_correct']} | "
                f"{(accuracy*100 if accuracy is not None else 0):.2f}% | "
                f"{item['review']} | {item['wrong_trusted']} | "
                f"{item['wrong_review']} |"
            )

    if deep is not None:
        lines += [
            "",
            "## 2. Глубокая выборка с пересчётом эмбеддингов",
            "",
            f"Цель выборки: {deep['sample']}; проверено: **{deep['tested']}**; "
            f"пропущено: {deep['skipped']}; слепков: {deep['fingerprints']}.",
            "",
            "| Комбинация | Верно | Всего | Точность |",
            "|---|---:|---:|---:|",
        ]
        for item in deep["combinations"]:
            lines.append(
                f"| `{item['name']}` | {item['correct']} | {item['total']} | "
                f"{item['accuracy']*100:.2f}% |"
            )

        best = deep["best"]
        lines += [
            "",
            f"Лучшая комбинация выборки: **`{best['name']}`** — "
            f"{best['correct']}/{best['total']} "
            f"({best['accuracy']*100:.2f}%).",
            "",
            "| Ожидалось → предсказано | Кол-во |",
            "|---|---:|",
        ]
        for pair in best["wrong_pairs"]:
            lines.append(
                f"| {pair['expected_name']} → {pair['predicted_name']} | "
                f"{pair['count']} |"
            )

        calibration = deep.get("calibration") or {}
        if calibration:
            lines += [
                "",
                "### Калибровка порогов на выборке",
                "",
                "| Схема | Всего | Trusted | Верно в Trusted | Точность Trusted | "
                "Review | Ошибок в Trusted | Ошибок в Review |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for scheme, label in (
                ("fixed_065", "фиксированный 0.65"),
                ("global", "глобальный квантиль"),
                ("per_address", "по адресу"),
                ("margin_gate", "глобальный + margin ≥ 0.005"),
            ):
                item = calibration[scheme]
                accuracy = item["trusted_accuracy"]
                lines.append(
                    f"| {label} | {item['total']} | {item['trusted']} | "
                    f"{item['trusted_correct']} | "
                    f"{(accuracy*100 if accuracy is not None else 0):.2f}% | "
                    f"{item['review']} | {item['wrong_trusted']} | "
                    f"{item['wrong_review']} |"
                )

    lines += [
        "",
        "## Ограничения",
        "",
        "- Полный корпус использует сохранённые кандидаты: top-k и кластеры "
        "внутри слепка там недоступны, они проверяются только на выборке.",
        "- Метки берутся из имён файлов; спорные имена исключаются.",
        "- Калибровка порогов оптимистична: порог строится по правильным "
        "ответам, хотя split двухфолдовый.",
        "- DINO-эмбеддинги выборки пересчитаны заново и могут незначительно "
        "отличаться от сохранённых из-за floating point.",
        "- Порядок фото для правила соседей — `taken_at -> source_path -> "
        "photo_id`, как в `get_run_items()`. Это соответствует структуре "
        "нового корпуса месяц/дата и убирает нестабильность одинаковых "
        "имён файлов.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        type=int,
        default=11,
        help="HYBRID run to re-score (default 11)",
    )
    parser.add_argument(
        "--phase",
        choices=("stored", "deep", "all"),
        default="all",
        help="stored = full HYBRID run; deep = recomputed sample; all = both",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=600,
        help="deep sample target (default 600)",
    )
    args = parser.parse_args(argv)
    run_id = args.run_id

    global REPORT
    REPORT = Path(
        f"data/reports/comparison_combinations_"
        f"{date.today():%Y%m%d}_run{run_id}.md"
    )

    OUT.mkdir(parents=True, exist_ok=True)

    expected = hwe.labeled_context()
    fp_to_address = fingerprint_addresses()
    labelled = sum(1 for value in expected.values() if value is not None)
    print(f"[combo] labelled photos: {labelled}", flush=True)

    full = None
    deep = None

    if args.phase in ("stored", "all"):
        print(f"[combo] loading HYBRID run {run_id}", flush=True)
        items = deterministic_order(get_run_items(run_id))
        original_best_ids = [item.dino_best_id for item in items]
        print(f"[combo] items={len(items)}", flush=True)
        full = full_corpus_phase(
            items, original_best_ids, expected, fp_to_address
        )
        print(f"[combo] best full: {full['best']['name']}", flush=True)
        del items

    if args.phase in ("deep", "all"):
        print(f"[combo] deep sample target={args.sample}", flush=True)
        deep = deep_phase(args.sample, expected, fp_to_address)
        if deep["best"] is not None:
            print(f"[combo] best deep: {deep['best']['name']}", flush=True)

    report = {
        "run_id": run_id,
        "labelled": labelled,
        "full": (
            {key: value for key, value in full.items() if key != "best_records"}
            if full is not None
            else None
        ),
        "deep": deep,
    }
    (OUT / f"report_run{run_id}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(full, deep, run_id)
    print(f"[combo] report: {REPORT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

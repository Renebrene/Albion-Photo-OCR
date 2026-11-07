#!/usr/bin/env python3
"""Read-only HYBRID weight sweep on the existing corpus.

The script re-scores stored DINO candidates under several weight combinations,
re-applies the current HYBRID rules (series, two neighbours, low-margin
best_image, switch gain) and compares the resulting address with the address
written in the filename.  Nothing is written to PostgreSQL or to production
fingerprints.

    .venv/bin/python scripts/hybrid_weight_experiment.py

Outputs:
    data/experiments/hybrid_weights/report.json
    data/reports/hybrid_weight_experiment_YYYYMMDD.md
"""

from __future__ import annotations

import base64
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.hybrid.database import get_run_items  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    expected_address,
    fingerprint_addresses,
    load_addresses,
)

RUN_ID = 11
OUT_DIR = Path("data/experiments/hybrid_weights")
REPORT = Path(f"data/reports/hybrid_weight_experiment_{date.today():%Y%m%d}.md")

GLOBAL_WEIGHT = 10.0
NEIGHBOR_BONUS = 3.0
SWITCH_GAIN = 1.5
BEST_IMAGE_MARGIN = 0.01

# Duplicate directory rows whose photos should be compared with the canonical
# address that actually has an active fingerprint.
CANONICAL_ADDRESS = {1509: 148, 2301: 205, 2412: 212}

# Confusion pairs worth watching separately: a global accuracy can hide a
# systematic swap between two nearby addresses.
TRACKED_PAIRS = {
    "Космонавтов 15 → 15-17": (176, 177),
    "Ленина 52 → 115": (189, 187),
    "Зорге 46 → Таганрогская 147 Б": (158, 219),
    "Дачная → Зорге": (144, 211),
    "Зорге → Дачная": (211, 144),
}


def normalized_weights(global_w: float, environment_w: float, color_w: float, spatial_w: float):
    total = global_w + environment_w + color_w + spatial_w
    return (
        global_w / total,
        environment_w / total,
        color_w / total,
        spatial_w / total,
    )


def weight_sets() -> list[tuple[str, tuple[float, float, float, float]]]:
    """A compact grid around the current production weights."""

    sets: list[tuple[str, tuple[float, float, float, float]]] = [
        ("base", normalized_weights(0.70, 0.20, 0.07, 0.03)),
    ]

    for color in (0.0, 0.03, 0.05, 0.10, 0.15):
        # Keep the global/environment ratio at the production 0.70:0.20.
        rest = 1.0 - 0.03 - color
        sets.append(
            (
                f"color_{color:.2f}",
                normalized_weights(rest * 0.7777778, rest * 0.2222222, color, 0.03),
            )
        )

    for environment in (0.10, 0.15, 0.25, 0.30):
        sets.append(
            (
                f"env_{environment:.2f}",
                normalized_weights(1.0 - 0.03 - 0.07 - environment, environment, 0.07, 0.03),
            )
        )

    return sets


def candidate_score(candidate: dict, weights: tuple[float, float, float, float]) -> float:
    wg, we, wc, ws = weights
    return (
        wg * float(candidate["global_score"])
        + we * float(candidate["environment_score"])
        + wc * float(candidate["color_score"])
        + ws * float(candidate["spatial_score"])
    )


def rescore_items(items, weights):
    """Return items with candidate scores and best candidate recomputed."""

    result = []

    for item in items:
        candidates = [
            {
                **candidate,
                "score": candidate_score(candidate, weights),
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


def simulate(
    items,
    original_best_ids: list[str | None],
    *,
    no_match: bool = False,
) -> list[str | None]:
    """
    One HYBRID pass over re-scored candidates.

    `original_best_ids` is needed for the zero-threshold fallback: photos whose
    original DINO best was NULL still prefer series/neighbour consensus over
    the new TOP-1, exactly like the current runner.
    """

    result: list[str | None] = []
    candidate_ids = [
        {str(candidate["id"]) for candidate in item.candidates}
        for item in items
    ]

    for index, item in enumerate(items):
        scores: dict[str, float] = {}

        for candidate in item.candidates:
            fingerprint_id = str(candidate["id"])
            scores[fingerprint_id] = (
                scores.get(fingerprint_id, 0.0)
                + float(candidate["score"]) * GLOBAL_WEIGHT
            )

        left_fp = items[index - 1].dino_best_id if index > 0 else None
        right_fp = (
            items[index + 1].dino_best_id
            if index < len(items) - 1
            else None
        )

        if left_fp is not None and left_fp == right_fp:
            scores[left_fp] = scores.get(left_fp, 0.0) + NEIGHBOR_BONUS

        consensus = (
            left_fp
            if left_fp is not None and left_fp == right_fp
            else None
        )
        best = item.dino_best_id
        used_custom_rule = False

        if original_best_ids[index] is None:
            if item.series_fp is not None and item.series_fp in candidate_ids[index]:
                best = item.series_fp
            elif consensus is not None and consensus in candidate_ids[index]:
                best = consensus
            elif no_match:
                # No DINO match and no series/neighbour confirmation: leave the
                # photo without an address instead of forcing TOP-1.
                best = None
            else:
                ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
                if ranked:
                    best = ranked[0][0]
            used_custom_rule = True

        elif item.dino_margin is not None and item.dino_margin < BEST_IMAGE_MARGIN:
            if item.series_fp is not None and item.series_fp in candidate_ids[index]:
                best = item.series_fp
                used_custom_rule = True
            elif consensus is not None and consensus in candidate_ids[index]:
                best = consensus
                used_custom_rule = True
            else:
                with_best_image = [
                    candidate
                    for candidate in item.candidates
                    if candidate.get("id") is not None
                    and candidate.get("best_image_score") is not None
                ]
                if with_best_image:
                    chosen = max(
                        with_best_image,
                        key=lambda candidate: float(candidate["best_image_score"]),
                    )
                    best = str(chosen["id"])
                    used_custom_rule = True

        if best is not None and not used_custom_rule:
            ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
            if ranked:
                candidate = ranked[0][0]
                if (
                    candidate != best
                    and scores[candidate] - scores.get(best, 0.0) > SWITCH_GAIN
                ):
                    best = candidate

        result.append(best)

    return result


def labeled_context():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, filename
                FROM public.photos
                WHERE filename IS NOT NULL
                """
            )
            filenames = {str(row[0]): str(row[1]) for row in cur.fetchall()}

    addresses = load_addresses()
    expected: dict[str, int | None] = {}

    for photo_id, filename in filenames.items():
        address = expected_address(filename, addresses)
        expected[photo_id] = (
            CANONICAL_ADDRESS.get(address, address)
            if address is not None
            else None
        )

    return expected


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[weights] loading HYBRID run {RUN_ID}", flush=True)
    items = get_run_items(RUN_ID)
    original_best_ids = [item.dino_best_id for item in items]
    print(f"[weights] items={len(items)}", flush=True)

    expected = labeled_context()
    fp_to_address = fingerprint_addresses()
    labelled = sum(1 for photo_id in expected if expected[photo_id] is not None)

    reports = []
    best_report = None

    for name, weights in weight_sets():
        print(f"[weights] {name} {weights}", flush=True)
        scored = rescore_items(items, weights)
        final_ids = simulate(scored, original_best_ids)

        stats = Counter()
        wrong_pairs = Counter()
        tracked = Counter()
        per_photo = {}

        for item, final_id in zip(items, final_ids):
            address = fp_to_address.get(str(final_id)) if final_id else None
            per_photo[item.photo_id] = address

            expected_address_id = expected.get(item.photo_id)
            if expected_address_id is None:
                continue

            stats["labelled"] += 1

            if address is None:
                stats["review"] += 1
            elif address == expected_address_id:
                stats["correct"] += 1
            else:
                stats["wrong"] += 1
                wrong_pairs[(expected_address_id, address)] += 1

            for label, pair in TRACKED_PAIRS.items():
                if (expected_address_id, address) == pair:
                    tracked[label] += 1

        item = {
            "name": name,
            "weights": {
                "global": weights[0],
                "environment": weights[1],
                "color": weights[2],
                "spatial": weights[3],
            },
            "labelled": stats["labelled"],
            "correct": stats["correct"],
            "wrong": stats["wrong"],
            "review": stats["review"],
            "accuracy": (
                stats["correct"] / stats["labelled"] if stats["labelled"] else None
            ),
            "tracked_pairs": dict(tracked),
            "wrong_pairs": [
                {
                    "expected": expected_id,
                    "expected_name": ADDRESS_NAMES.get(expected_id, ""),
                    "predicted": predicted_id,
                    "predicted_name": ADDRESS_NAMES.get(predicted_id, ""),
                    "count": count,
                }
                for (expected_id, predicted_id), count in wrong_pairs.most_common(10)
            ],
        }
        reports.append(item)

        if best_report is None or (item["correct"], -item["wrong"]) > (
            best_report["correct"],
            -best_report["wrong"],
        ):
            best_report = item

        # Keep the per-photo address map of the baseline for a later diff.
        if name == "base":
            (OUT_DIR / "base_addresses.json").write_text(
                json.dumps(per_photo, ensure_ascii=False),
                encoding="utf-8",
            )

    report = {
        "run_id": RUN_ID,
        "items": len(items),
        "labelled": labelled,
        "weights": reports,
        "best": best_report,
    }
    (OUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# HYBRID: перебор весов DINO-дескрипторов",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Только чтение: PostgreSQL и слепки не изменялись.",
        "",
        f"HYBRID run {RUN_ID}, фото: {len(items)}, подписано адресами: {labelled}.",
        "",
        "| Комбинация | global | env | color | spatial | Верно | Неверно | Review | Точность |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for item in reports:
        weights = item["weights"]
        accuracy = item["accuracy"] or 0.0
        lines.append(
            f"| `{item['name']}` | {weights['global']:.3f} | {weights['environment']:.3f} | "
            f"{weights['color']:.3f} | {weights['spatial']:.3f} | "
            f"{item['correct']} | {item['wrong']} | {item['review']} | {accuracy*100:.2f}% |"
        )

    lines += [
        "",
        "## Отслеживаемые hard-пары",
        "",
        "| Комбинация | " + " | ".join(TRACKED_PAIRS) + " |",
        "|---|" + "---:|" * len(TRACKED_PAIRS),
    ]
    for item in reports:
        counts = item["tracked_pairs"]
        lines.append(
            f"| `{item['name']}` | "
            + " | ".join(str(counts.get(label, 0)) for label in TRACKED_PAIRS)
            + " |"
        )

    if best_report is not None:
        lines += [
            "",
            f"Лучшая комбинация в этом прогоне: **`{best_report['name']}`** — "
            f"{best_report['correct']} верных, {best_report['wrong']} неверных.",
            "",
            "## Частые ошибки у базовой комбинации",
            "",
        ]
        base = next(item for item in reports if item["name"] == "base")
        for pair in base["wrong_pairs"]:
            lines.append(
                f"- {pair['expected_name']} → {pair['predicted_name']}: {pair['count']}"
            )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[weights] report: {REPORT}", flush=True)
    print(json.dumps(report["best"], ensure_ascii=False, indent=2)[:2000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

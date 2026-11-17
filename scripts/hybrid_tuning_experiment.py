#!/usr/bin/env python3
"""HYBRID: перебор весов env/spatial и вариантов правила соседей.

    .venv/bin/python scripts/hybrid_tuning_experiment.py [--run-id 11]

Только чтение: DINO и HYBRID не перезапускаются. Берутся сохранённые
кандидаты HYBRID-прогона, пересчитываются под каждой комбинацией весов и
каждым вариантом правил (бонус соседям, порог переключения, порог
low-margin) и результат сравнивается с адресом из имени файла.

Отличие от scripts/hybrid_weight_experiment.py: пространственный вес
(spatial) раньше не перебирался, а здесь он поднимается вместе с
environment; отдельно измеряется, сколько ошибок сделали правила
(оценка была за правильный адрес), а сколько — сама оценка.

Выходы:
    data/experiments/hybrid_tuning/report.json
    data/reports/hybrid_tuning_experiment_YYYYMMDD_runN.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.hybrid.database import get_run_items  # noqa: E402
from scripts import hybrid_weight_experiment as hwe  # noqa: E402
from scripts.batch_stats import accepted_variants  # noqa: E402
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    fingerprint_addresses,
)

OUT_DIR = Path("data/experiments/hybrid_tuning")

# Веса как в проде (simulate воспроизводит правила runner.py).
GLOBAL_WEIGHT = 10.0
NEIGHBOR_BONUS = 3.0
SWITCH_GAIN = 1.5
BEST_IMAGE_MARGIN = 0.01


def weight_sets() -> list[tuple[str, tuple[float, float, float, float]]]:
    """Сетка вокруг продовых весов: сначала цвет в ноль, потом env/spatial."""

    raw = [
        ("base", (0.70, 0.20, 0.07, 0.03)),
        ("nocolor", (0.75, 0.22, 0.00, 0.03)),
        ("s10", (0.70, 0.20, 0.00, 0.10)),
        ("s15", (0.65, 0.20, 0.00, 0.15)),
        ("s20", (0.60, 0.20, 0.00, 0.20)),
        ("e30c", (0.60, 0.30, 0.07, 0.03)),
        ("e30", (0.60, 0.30, 0.00, 0.10)),
        ("e35", (0.55, 0.35, 0.00, 0.10)),
        ("es1", (0.55, 0.25, 0.00, 0.20)),
        ("es2", (0.50, 0.30, 0.00, 0.20)),
        ("es3", (0.45, 0.30, 0.00, 0.25)),
        ("es4", (0.40, 0.35, 0.00, 0.25)),
        ("es5", (0.35, 0.40, 0.00, 0.25)),
        ("es6", (0.30, 0.45, 0.00, 0.25)),
        ("es7", (0.35, 0.35, 0.00, 0.30)),
        ("es8", (0.25, 0.50, 0.00, 0.25)),
        ("es9", (0.30, 0.40, 0.00, 0.30)),
    ]
    return [(name, hwe.normalized_weights(*weights)) for name, weights in raw]


def simulate_tuned(
    items,
    original_best_ids: list[str | None],
    *,
    neighbor_bonus: float = NEIGHBOR_BONUS,
    switch_gain: float = SWITCH_GAIN,
    best_image_margin: float = BEST_IMAGE_MARGIN,
    no_match: bool = False,
):
    """
    Один проход правил HYBRID над пересчитанными кандидатами.

    Возвращает (final_ids, mechanisms, pure_winner_ids): механизм решения
    для каждого фото и «чистый» победитель оценки без бонуса соседям.
    """

    result: list[str | None] = []
    mechanisms: list[str] = []
    pure_winners: list[str | None] = []

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

        base_scores = dict(scores)

        left_fp = items[index - 1].dino_best_id if index > 0 else None
        right_fp = (
            items[index + 1].dino_best_id
            if index < len(items) - 1
            else None
        )

        consensus = (
            left_fp
            if left_fp is not None and left_fp == right_fp
            else None
        )
        if consensus is not None and neighbor_bonus:
            scores[consensus] = scores.get(consensus, 0.0) + neighbor_bonus

        pure = None
        if base_scores:
            pure = max(base_scores.items(), key=lambda pair: pair[1])[0]

        best = item.dino_best_id
        mechanism = "score"
        used_custom_rule = False

        if original_best_ids[index] is None:
            if item.series_fp is not None and item.series_fp in candidate_ids[index]:
                best = item.series_fp
                mechanism = "series"
            elif consensus is not None and consensus in candidate_ids[index]:
                best = consensus
                mechanism = "neighbors"
            elif not no_match:
                ranked = sorted(
                    scores.items(), key=lambda pair: pair[1], reverse=True
                )
                if ranked:
                    best = ranked[0][0]
                    mechanism = "top1"
            else:
                # DINO без результата и нет подтверждения серией/соседями:
                # оставляем фото без адреса вместо форсированного TOP-1.
                best = None
            used_custom_rule = True

        elif (
            item.dino_margin is not None
            and item.dino_margin < best_image_margin
        ):
            if item.series_fp is not None and item.series_fp in candidate_ids[index]:
                best = item.series_fp
                mechanism = "series"
                used_custom_rule = True
            elif consensus is not None and consensus in candidate_ids[index]:
                best = consensus
                mechanism = "neighbors"
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
                        key=lambda candidate: float(
                            candidate["best_image_score"]
                        ),
                    )
                    best = str(chosen["id"])
                    mechanism = "best_image"
                    used_custom_rule = True

        if best is not None and not used_custom_rule:
            ranked = sorted(
                scores.items(), key=lambda pair: pair[1], reverse=True
            )
            if ranked:
                candidate = ranked[0][0]
                if (
                    candidate != best
                    and scores[candidate] - scores.get(best, 0.0) > switch_gain
                ):
                    best = candidate
                    mechanism = "switch"

        result.append(best)
        mechanisms.append(mechanism)
        pure_winners.append(pure)

    return result, mechanisms, pure_winners


def evaluation_context():
    expected = hwe.labeled_context()
    fp_to_address = {
        fingerprint_id: hwe.CANONICAL_ADDRESS.get(int(address), int(address))
        for fingerprint_id, address in fingerprint_addresses().items()
    }
    return expected, fp_to_address


def evaluate(
    items,
    final_ids,
    mechanisms,
    pure_winners,
    expected,
    fp_to_address,
    accepted,
):
    """Итоги варианта: точность (строго и с вариантами) + разбор ошибок."""

    stats: Counter = Counter()
    wrong_pairs: Counter = Counter()

    for item, final_id, mechanism, pure in zip(
        items, final_ids, mechanisms, pure_winners
    ):
        address = fp_to_address.get(str(final_id)) if final_id else None
        expected_id = expected.get(item.photo_id)
        if expected_id is None:
            continue

        stats["labelled"] += 1
        acc = accepted.get(expected_id, {expected_id})

        if address is None:
            stats["review"] += 1
        else:
            if address == expected_id:
                stats["correct"] += 1
            if address in acc:
                stats["correct_norm"] += 1
            else:
                stats["wrong_norm"] += 1
                stats[f"mech_{mechanism}"] += 1
                pure_address = fp_to_address.get(str(pure)) if pure else None
                if pure_address == expected_id:
                    stats["rule_errors"] += 1
                else:
                    stats["score_errors"] += 1
            if address != expected_id:
                stats["wrong"] += 1
                wrong_pairs[(expected_id, address)] += 1

    stats["wrong_pairs"] = wrong_pairs
    return stats


def stats_item(name: str, stats: Counter, weights=None, extra=None) -> dict:
    labelled = stats["labelled"]
    return {
        "name": name,
        "weights": weights,
        "labelled": labelled,
        "correct": stats["correct"],
        "wrong": stats["wrong"],
        "review": stats["review"],
        "accuracy": stats["correct"] / labelled if labelled else None,
        "correct_norm": stats["correct_norm"],
        "wrong_norm": stats["wrong_norm"],
        "accuracy_norm": (
            stats["correct_norm"] / labelled if labelled else None
        ),
        "rule_errors": stats["rule_errors"],
        "score_errors": stats["score_errors"],
        "mechanisms": {
            key[len("mech_"):]: stats[key]
            for key in stats
            if key.startswith("mech_")
        },
        "wrong_pairs": [
            {
                "expected": expected_id,
                "expected_name": ADDRESS_NAMES.get(expected_id, ""),
                "predicted": predicted_id,
                "predicted_name": ADDRESS_NAMES.get(predicted_id, ""),
                "count": count,
            }
            for (expected_id, predicted_id), count in stats["wrong_pairs"].most_common(10)
        ],
        **(extra or {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, default=hwe.RUN_ID)
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[tuning] loading HYBRID run {args.run_id}", flush=True)
    items = get_run_items(args.run_id)
    original_best_ids = [item.dino_best_id for item in items]
    print(f"[tuning] items={len(items)}", flush=True)

    expected, fp_to_address = evaluation_context()
    accepted = accepted_variants()

    base_stats = None
    weight_results = []

    # ---- часть A: веса, правила продовые ----
    for name, weights in weight_sets():
        scored = hwe.rescore_items(items, weights)
        final_ids, mechanisms, pure = simulate_tuned(scored, original_best_ids)
        stats = evaluate(
            scored, final_ids, mechanisms, pure, expected, fp_to_address, accepted
        )
        item = stats_item(
            name,
            stats,
            weights={
                "global": weights[0],
                "environment": weights[1],
                "color": weights[2],
                "spatial": weights[3],
            },
        )
        weight_results.append(item)
        if name == "base":
            base_stats = item
        print(
            f"[tuning] {name}: correct={item['correct']} wrong={item['wrong']} "
            f"rule_err={item['rule_errors']} score_err={item['score_errors']}",
            flush=True,
        )

    best_weights = max(
        weight_results,
        key=lambda item: (item["correct_norm"], -item["wrong_norm"]),
    )
    best_weight_set = next(
        weights
        for name, weights in weight_sets()
        if name == best_weights["name"]
    )

    # ---- часть B: правила на лучших весах и на base ----
    rule_results = []
    rule_variants = [
        ("prod_rules", {}),
        ("nb2", {"neighbor_bonus": 2.0}),
        ("nb1", {"neighbor_bonus": 1.0}),
        ("nb0", {"neighbor_bonus": 0.0}),
        ("sg3", {"switch_gain": 3.0}),
        ("nb2_sg3", {"neighbor_bonus": 2.0, "switch_gain": 3.0}),
        ("bim005", {"best_image_margin": 0.005}),
        ("bim005_nb2", {"best_image_margin": 0.005, "neighbor_bonus": 2.0}),
        ("bim005_nomatch", {"best_image_margin": 0.005, "no_match": True}),
    ]

    for weights_name, weights in (
        ("base", weight_sets()[0][1]),
        (best_weights["name"], best_weight_set),
    ):
        scored = hwe.rescore_items(items, weights)
        for name, kwargs in rule_variants:
            final_ids, mechanisms, pure = simulate_tuned(
                scored, original_best_ids, **kwargs
            )
            stats = evaluate(
                scored, final_ids, mechanisms, pure, expected, fp_to_address, accepted
            )
            item = stats_item(
                f"{weights_name}/{name}",
                stats,
                extra={"base_weights": weights_name},
            )
            rule_results.append(item)

    # ---- пары для слежения: топ ошибок base ----
    tracked = [
        (pair["expected"], pair["predicted"])
        for pair in (base_stats["wrong_pairs"] if base_stats else [])[:8]
    ]

    report = {
        "run_id": args.run_id,
        "items": len(items),
        "labelled": base_stats["labelled"] if base_stats else None,
        "weight_results": weight_results,
        "rule_results": rule_results,
        "best_weights": best_weights,
    }
    (OUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# HYBRID: веса env/spatial и варианты правила соседей",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Только чтение: DINO/HYBRID не "
        f"перезапускались, кандидаты из run {args.run_id}.",
        "",
        f"Фото: {len(items)}, подписано: {base_stats['labelled'] if base_stats else '—'}.",
        "",
        "## Часть A: веса (правила продовые)",
        "",
        "«Верно» — строгое совпадение адреса; «Верно (вар.)» — с допустимыми "
        "вариантами названия (label_variants_run4).",
        "",
        "| Вариант | global | env | color | spatial | Верно | Верно (вар.) | "
        "Rule-ошибок | Score-ошибок | Точность (вар.) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in weight_results:
        weights = item["weights"]
        accuracy = item["accuracy_norm"] or 0.0
        lines.append(
            f"| `{item['name']}` | {weights['global']:.2f} | "
            f"{weights['environment']:.2f} | {weights['color']:.2f} | "
            f"{weights['spatial']:.2f} | {item['correct']} | "
            f"{item['correct_norm']} | "
            f"{item['rule_errors']} | {item['score_errors']} | "
            f"{accuracy * 100:.2f}% |"
        )

    lines += [
        "",
        "Rule-ошибок — итог выбрал не тот адрес, хотя чистая оценка была за "
        "правильный (виноваты правила серии/соседей); score-ошибок — сама "
        "оценка выбрала неверный адрес.",
        "",
        "## Часть B: варианты правил",
        "",
        "| Вариант | Верно (вар.) | Ошибок (вар.) | Rule-ошибок | Score-ошибок | "
        "Точность (вар.) | Механизмы ошибок |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in rule_results:
        accuracy = item["accuracy_norm"] or 0.0
        mech = ", ".join(
            f"{key} {count}" for key, count in item["mechanisms"].items()
        )
        lines.append(
            f"| `{item['name']}` | {item['correct_norm']} | "
            f"{item['wrong_norm']} | "
            f"{item['rule_errors']} | {item['score_errors']} | "
            f"{accuracy * 100:.2f}% | {mech or '—'} |"
        )

    if tracked:
        lines += [
            "",
            "## Топ-пары ошибок base по вариантам",
            "",
            "| Пара | " + " | ".join(item["name"] for item in weight_results) + " |",
            "|---|" + "---:|" * len(weight_results),
        ]
        for expected_id, predicted_id in tracked:
            cells = []
            for item in weight_results:
                count = next(
                    (
                        pair["count"]
                        for pair in item["wrong_pairs"]
                        if pair["expected"] == expected_id
                        and pair["predicted"] == predicted_id
                    ),
                    0,
                )
                cells.append(str(count))
            lines.append(
                f"| {ADDRESS_NAMES.get(expected_id, expected_id)} → "
                f"{ADDRESS_NAMES.get(predicted_id, predicted_id)} | "
                + " | ".join(cells)
                + " |"
            )

    report_path = Path(
        f"data/reports/hybrid_tuning_experiment_{date.today():%Y%m%d}"
        f"_run{args.run_id}.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[tuning] json: {OUT_DIR / 'report.json'}", flush=True)
    print(f"[tuning] report: {report_path}", flush=True)
    print(
        f"[tuning] best weights: {best_weights['name']} "
        f"correct={best_weights['correct']} wrong={best_weights['wrong']}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""HYBRID: виртуальный перебор ширины окна правила соседей.

    .venv/bin/python scripts/neighbor_window_experiment.py [--run-id 12]

Только чтение: DINO/HYBRID не перезапускаются. На сохранённых кандидатах
прогона проверяется расширение правила соседей с «левый+правый» (прод) на
окно ±K соседей слева и справа:

- vote   — каждый сосед в окне, чей dino_best совпал с кандидатом, добавляет
           ему голос-бонус (vote_bonus за голос);
- majority — бонус только если максимум голосов достигает min_votes;
- guard  — голоса учитываются только за слепки из TOP-15 самого фото
           (сейчас бонус может уйти чужому слепку).

Порядок соседей — порядок items прогона (файлы отсортированы, как в batch).

Выходы:
    data/experiments/neighbor_window/report.json
    data/reports/neighbor_window_experiment_YYYYMMDD_runN.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.hybrid.database import get_run_items  # noqa: E402
from scripts import hybrid_weight_experiment as hwe  # noqa: E402
from scripts.hybrid_tuning_experiment import (  # noqa: E402
    BEST_IMAGE_MARGIN,
    GLOBAL_WEIGHT,
    NEIGHBOR_BONUS,
    SWITCH_GAIN,
    evaluation_context,
    evaluate,
    stats_item,
)

OUT_DIR = Path("data/experiments/neighbor_window")

ES4_WEIGHTS = hwe.normalized_weights(0.40, 0.35, 0.00, 0.25)


def simulate_window(
    items,
    original_best_ids,
    best_ids,
    candidate_ids,
    *,
    window: int = 1,
    vote_bonus: float | None = None,
    majority_bonus: float | None = None,
    min_votes: int = 2,
    guard_top15: bool = False,
    switch_gain: float = SWITCH_GAIN,
    best_image_margin: float = BEST_IMAGE_MARGIN,
):
    """Правила HYBRID с окном соседей ±window. Возвращает (итоги, механизмы, чистый победитель)."""

    result: list[str | None] = []
    mechanisms: list[str] = []
    pure_winners: list[str | None] = []
    n = len(items)

    for index, item in enumerate(items):
        scores: dict[str, float] = {}

        for candidate in item.candidates:
            fingerprint_id = str(candidate["id"])
            scores[fingerprint_id] = (
                scores.get(fingerprint_id, 0.0)
                + float(candidate["score"]) * GLOBAL_WEIGHT
            )

        base_scores = dict(scores)

        # Окно соседей: голоса за слепки по dino_best соседей.
        votes: Counter = Counter()
        lo = max(0, index - window)
        hi = min(n, index + window + 1)
        for offset in range(lo, hi):
            if offset == index:
                continue
            neighbor_fp = best_ids[offset]
            if neighbor_fp is None:
                continue
            if guard_top15 and neighbor_fp not in candidate_ids[index]:
                continue
            votes[neighbor_fp] += 1

        for fingerprint_id, count in votes.items():
            if vote_bonus:
                scores[fingerprint_id] = (
                    scores.get(fingerprint_id, 0.0) + count * vote_bonus
                )

        consensus = None
        if votes:
            top_fp, top_count = votes.most_common(1)[0]
            if top_count >= max(min_votes, 2):
                consensus = top_fp
            if majority_bonus and top_count >= max(min_votes, 2):
                scores[top_fp] = scores.get(top_fp, 0.0) + majority_bonus

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
            elif not vote_bonus and not majority_bonus:
                # Прод-фолбэк: форсировать TOP-1 (только у базового варианта).
                ranked = sorted(
                    scores.items(), key=lambda pair: pair[1], reverse=True
                )
                if ranked:
                    best = ranked[0][0]
                    mechanism = "top1"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, default=12)
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[window] loading HYBRID run {args.run_id}", flush=True)
    items = get_run_items(args.run_id)
    original_best_ids = [item.dino_best_id for item in items]
    print(f"[window] items={len(items)}", flush=True)

    expected, fp_to_address = evaluation_context()
    accepted = __import__("scripts.batch_stats", fromlist=["accepted_variants"]).accepted_variants()

    scored = hwe.rescore_items(items, ES4_WEIGHTS)
    best_ids = [item.dino_best_id for item in scored]
    candidate_ids = [
        {str(candidate["id"]) for candidate in item.candidates}
        for item in scored
    ]

    variants = [
        ("prod (K=1, бонус 3.0 при left==right)", {"prod": True}),
        ("K3 голос 1.0", {"window": 3, "vote_bonus": 1.0}),
        ("K5 голос 1.0", {"window": 5, "vote_bonus": 1.0}),
        ("K10 голос 1.0", {"window": 10, "vote_bonus": 1.0}),
        ("K5 голос 0.75", {"window": 5, "vote_bonus": 0.75}),
        ("K5 большинство>=3 бонус 3.0", {"window": 5, "majority_bonus": 3.0, "min_votes": 3}),
        ("K10 большинство>=5 бонус 3.0", {"window": 10, "majority_bonus": 3.0, "min_votes": 5}),
        ("K5 голос 1.0 + guard TOP-15", {"window": 5, "vote_bonus": 1.0, "guard_top15": True}),
        ("K10 голос 1.0 + guard TOP-15", {"window": 10, "vote_bonus": 1.0, "guard_top15": True}),
    ]

    results = []
    base_stats = None

    for name, kwargs in variants:
        if kwargs.get("prod"):
            from scripts.hybrid_tuning_experiment import simulate_tuned

            final_ids, mechanisms, pure = simulate_tuned(scored, original_best_ids)
        else:
            final_ids, mechanisms, pure = simulate_window(
                scored,
                original_best_ids,
                best_ids,
                candidate_ids,
                **kwargs,
            )
        stats = evaluate(
            scored, final_ids, mechanisms, pure, expected, fp_to_address, accepted
        )
        item = stats_item(name, stats)
        results.append(item)
        if base_stats is None:
            base_stats = item
        print(
            f"[window] {name}: ok={item['correct_norm']} wrong={item['wrong_norm']} "
            f"rule_err={item['rule_errors']} score_err={item['score_errors']}",
            flush=True,
        )

    tracked = [
        (pair["expected"], pair["predicted"])
        for pair in base_stats["wrong_pairs"][:8]
    ]

    report = {
        "run_id": args.run_id,
        "items": len(items),
        "labelled": base_stats["labelled"],
        "variants": results,
        "tracked_pairs": [
            {"expected": e, "predicted": p} for e, p in tracked
        ],
    }
    (OUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# HYBRID: окно правила соседей ±K (виртуальный прогон)",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Только чтение: кандидаты из "
        f"run {args.run_id}, веса 0.40/0.35/0/0.25, правила продовые.",
        "",
        f"Фото: {len(items)}, подписано: {base_stats['labelled']}.",
        "",
        "| Вариант | Верно (вар.) | Ошибок | Rule-ошибок | Score-ошибок | Точность (вар.) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        accuracy = item["accuracy_norm"] or 0.0
        lines.append(
            f"| `{item['name']}` | {item['correct_norm']} | {item['wrong_norm']} | "
            f"{item['rule_errors']} | {item['score_errors']} | {accuracy * 100:.2f}% |"
        )

    if tracked:
        lines += [
            "",
            "## Топ-пары ошибок прод-правил по вариантам",
            "",
            "| Пара | " + " | ".join(item["name"] for item in results) + " |",
            "|---|" + "---:|" * len(results),
        ]
        for expected_id, predicted_id in tracked:
            cells = []
            for item in results:
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
                f"| {expected_id} → {predicted_id} | " + " | ".join(cells) + " |"
            )

    report_path = Path(
        f"data/reports/neighbor_window_experiment_{date.today():%Y%m%d}"
        f"_run{args.run_id}.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[window] json: {OUT_DIR / 'report.json'}", flush=True)
    print(f"[window] report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

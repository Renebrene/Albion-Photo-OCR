#!/usr/bin/env python3
"""Подробная статистика по адресам для одного HYBRID-прогона.

    .venv/bin/python scripts/batch_stats.py --run-id 11

Только чтение: PostgreSQL и слепки не изменяются.

Считает по каждому подписанному адресу:
- найдено фото (строго и с учётом вариантов названия из
  data/experiments/label_variants_run4.json);
- сколько эталонных фото в активном слепке адреса;
- сколько совпало на уровне DINO (dino_best_id) и HYBRID (hybrid_final_id);
- процент ошибок и главных «противников» (с адресами, не только именами).

Отдельно — тест различимости: для ошибочных фото, где в TOP-15 есть
кандидаты и правильного, и ошибочного адреса, проверяется, какой компонент
оценки (global / environment / color / spatial / взвешенная сумма с цветом и
без) чаще ставит слепок правильного адреса выше слепка «противника».

Выходы:
    data/experiments/batch_stats/runN.json
    data/reports/batch_stats_YYYYMMDD_runN.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402
from scripts import hybrid_weight_experiment as hwe  # noqa: E402
from scripts.evaluate_sorting import (  # noqa: E402
    ADDRESS_NAMES,
    fingerprint_addresses,
)
from scripts.labeled_error_table import fingerprint_sizes  # noqa: E402

VARIANTS = Path("data/experiments/label_variants_run4.json")
OUT_DIR = Path("data/experiments/batch_stats")

COMPONENTS = ("global", "environment", "color", "spatial")
PROD_WEIGHTS = {"global": 0.70, "environment": 0.20, "color": 0.07, "spatial": 0.03}
NOCOLOR_WEIGHTS = {"global": 0.75, "environment": 0.22, "color": 0.00, "spatial": 0.03}
METRICS = COMPONENTS + ("prod_sum", "nocolor_sum", "best_image")

METRIC_LABELS = {
    "global": "global (DINO)",
    "environment": "environment",
    "color": "color",
    "spatial": "spatial",
    "prod_sum": "сумма 0.70/0.20/0.07/0.03",
    "nocolor_sum": "сумма без цвета 0.75/0.22/0/0.03",
    "best_image": "best_image (лучшее эталонное)",
}


def canonical(address_id) -> int | None:
    if address_id is None:
        return None
    address_id = int(address_id)
    return hwe.CANONICAL_ADDRESS.get(address_id, address_id)


def accepted_variants() -> dict[int, set[int]]:
    """Карта «адрес → допустимые адреса-варианты названия»."""

    if not VARIANTS.exists():
        return {}

    raw = json.loads(VARIANTS.read_text(encoding="utf-8"))
    result: dict[int, set[int]] = {}
    for key, values in raw.items():
        target = canonical(key)
        result[target] = {canonical(value) for value in values} | {target}
    return result


def load_verdicts(run_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT hv.photo_id, p.filename, dr.dino_best_id,
                       hv.hybrid_final_id, hv.dino_run_id
                FROM public.hybrid_results AS hv
                JOIN public.dino_runs AS dr
                  ON dr.run_id = hv.dino_run_id
                JOIN public.photos AS p
                  ON p.photo_id = hv.photo_id
                WHERE hv.hybrid_run_id = %s
                  AND hv.status = 'DONE'
                  AND dr.status = 'DONE'
                """,
                (run_id,),
            )
            return cur.fetchall()


def load_candidates(run_ids, fingerprint_ids) -> dict[int, dict[str, dict]]:
    """Кандидаты нужных слепков по каждому прогону: run_id → fp → данные."""

    result: dict[int, dict[str, dict]] = {}
    run_ids = list(run_ids)
    fingerprint_ids = list(fingerprint_ids)

    if not run_ids or not fingerprint_ids:
        return result

    with get_connection() as conn:
        with conn.cursor() as cur:
            for start in range(0, len(run_ids), 8000):
                chunk = run_ids[start : start + 8000]
                cur.execute(
                    """
                    SELECT run_id, fingerprint_id, rank,
                           global_score, environment_score,
                           color_score, spatial_score, best_image_score
                    FROM public.dino_candidates
                    WHERE run_id = ANY(%s)
                      AND fingerprint_id = ANY(%s)
                    """,
                    (chunk, fingerprint_ids),
                )
                for row in cur.fetchall():
                    cand = {
                        "rank": int(row[2]),
                        "global": float(row[3]),
                        "environment": float(row[4]),
                        "color": float(row[5]),
                        "spatial": float(row[6]),
                        "best_image": float(row[7]),
                    }
                    cand["prod_sum"] = sum(
                        PROD_WEIGHTS[name] * cand[name] for name in COMPONENTS
                    )
                    cand["nocolor_sum"] = sum(
                        NOCOLOR_WEIGHTS[name] * cand[name] for name in COMPONENTS
                    )
                    result.setdefault(int(row[0]), {})[str(row[1])] = cand

    return result


def pick_fp(
    candidates: dict[str, dict],
    fp_addr: dict[str, int],
    *,
    wanted: set[int] | None = None,
    exclude: set[int] | None = None,
):
    """Слепок с минимальным рангом среди адресов из *wanted*, кроме *exclude*."""

    best = None

    for fingerprint_id, cand in candidates.items():
        address = canonical(fp_addr.get(fingerprint_id))

        if address is None:
            continue
        if wanted is not None and address not in wanted:
            continue
        if exclude is not None and address in exclude:
            continue

        if best is None or cand["rank"] < best[1]["rank"]:
            best = (fingerprint_id, cand)

    return best


def component_test(
    groups: list[tuple],
    candidates_by_run: dict[int, dict[str, dict]],
    fp_addr: dict[str, int],
) -> tuple[dict, list[dict]]:
    """
    Для пар «правильный адрес против rival» — по каждому компоненту доля,
    где правильный выше. groups: (dino_run_id, exp, rival_addr | None, acc).

    Считается двумя способами:
    - min_rank — кандидаты с минимальным рангом каждого адреса;
    - best — лучший (максимальный) кандидат адреса по каждому компоненту,
      как HYBRID видит адрес целиком.
    Для ошибок дополнительно: winner по лучшей prod_sum — «score» (оценка
    выбрала rival) или «rule» (оценка была за правильный адрес, итог изменили
    правила серии/соседей).
    """

    rows: list[dict] = []
    missing = Counter()

    for run_id, exp, rival_addr, acc in groups:
        candidates = candidates_by_run.get(run_id, {})
        if not candidates:
            missing["no_candidates"] += 1
            continue

        exp_cands = [
            cand
            for fingerprint_id, cand in candidates.items()
            if canonical(fp_addr.get(fingerprint_id)) == exp
        ]
        if not exp_cands:
            missing["expected_not_in_top"] += 1
            continue

        if rival_addr is not None:
            rival_cands = [
                cand
                for fingerprint_id, cand in candidates.items()
                if canonical(fp_addr.get(fingerprint_id)) == rival_addr
            ]
            if not rival_cands:
                missing["rival_not_in_top"] += 1
                continue
        else:
            exclude = acc if acc else {exp}
            rival_cands = [
                cand
                for fingerprint_id, cand in candidates.items()
                if canonical(fp_addr.get(fingerprint_id)) not in exclude
            ]
            if not rival_cands:
                missing["no_other_candidate"] += 1
                continue

        exp_min = min(exp_cands, key=lambda cand: cand["rank"])
        rival_min = min(rival_cands, key=lambda cand: cand["rank"])

        row = {
            "exp": exp,
            "rival": rival_addr,
            "deltas": {},
            "wins": {},
            "best_deltas": {},
            "best_wins": {},
        }
        for metric in METRICS:
            best_exp = max(cand[metric] for cand in exp_cands)
            best_rival = max(cand[metric] for cand in rival_cands)
            row["deltas"][metric] = exp_min[metric] - rival_min[metric]
            row["wins"][metric] = row["deltas"][metric] > 0
            row["best_deltas"][metric] = best_exp - best_rival
            row["best_wins"][metric] = row["best_deltas"][metric] > 0

        prod_exp = max(cand["prod_sum"] for cand in exp_cands)
        prod_rival = max(cand["prod_sum"] for cand in rival_cands)
        row["prod_winner"] = "exp" if prod_exp > prod_rival else "rival"

        rows.append(row)

    summary: dict = {"n": len(rows), "missing": dict(missing)}

    if rows:
        summary["win_share"] = {
            metric: sum(1 for row in rows if row["wins"][metric]) / len(rows)
            for metric in METRICS
        }
        summary["win_share_best"] = {
            metric: sum(1 for row in rows if row["best_wins"][metric]) / len(rows)
            for metric in METRICS
        }
        summary["mean_delta"] = {
            metric: statistics.fmean(row["best_deltas"][metric] for row in rows)
            for metric in METRICS
        }
        summary["prod_winner"] = {
            "exp": sum(1 for row in rows if row["prod_winner"] == "exp") / len(rows),
            "rival": sum(1 for row in rows if row["prod_winner"] == "rival")
            / len(rows),
        }

    return summary, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)

    print(f"[stats] run {args.run_id}: загрузка контекста...", flush=True)

    expected = hwe.labeled_context()
    fp_addr = {
        fingerprint_id: canonical(address_id)
        for fingerprint_id, address_id in fingerprint_addresses().items()
    }
    sizes = fingerprint_sizes()
    accepted = accepted_variants()

    rows = load_verdicts(args.run_id)
    print(f"[stats] items={len(rows)}", flush=True)

    per: dict[int, Counter] = defaultdict(Counter)
    confusions: dict[int, Counter] = defaultdict(Counter)
    pair_groups: dict[tuple[int, int], list] = defaultdict(list)
    groups_w: list[tuple] = []
    groups_c: list[tuple] = []
    groups_e: list[tuple] = []

    for photo_id, _filename, dino_best, hybrid_final, dino_run_id in rows:
        exp = expected.get(str(photo_id))
        if exp is None:
            continue

        stats = per[exp]
        stats["photos"] += 1

        acc = accepted.get(exp, {exp})
        d_addr = canonical(fp_addr.get(str(dino_best))) if dino_best else None
        h_addr = canonical(fp_addr.get(str(hybrid_final))) if hybrid_final else None

        d_ok = d_addr is not None and d_addr in acc
        h_ok = h_addr is not None and h_addr in acc

        stats["dino_ok"] += d_ok
        stats["dino_none"] += dino_best is None
        stats["dino_wrong"] += d_addr is not None and not d_ok
        stats["hybrid_ok"] += h_addr == exp
        stats["hybrid_ok_norm"] += h_ok
        stats["hybrid_none"] += hybrid_final is None

        run_key = int(dino_run_id)

        if h_addr is not None and not h_ok:
            stats["wrong"] += 1
            confusions[exp][h_addr] += 1
            groups_w.append((run_key, exp, h_addr, acc))
            pair_groups[(exp, h_addr)].append(
                (run_key, exp, h_addr, acc)
            )
        elif h_ok and d_addr is not None and not d_ok:
            stats["hybrid_fixed"] += 1
            groups_c.append((run_key, exp, d_addr, acc))
        elif h_ok and d_addr is None:
            # DINO не дал результата, гибрид нашёл адрес по серии/соседям.
            stats["hybrid_rescued"] += 1
        elif h_ok and d_ok:
            stats["both_ok"] += 1
            groups_e.append((run_key, exp, None, acc))

    addresses = sorted(per, key=lambda a: (-per[a]["wrong"], -per[a]["photos"], a))

    # ---- таблица по адресам ----
    address_rows = []
    for a in addresses:
        stats = per[a]
        total = stats["photos"]
        wrong = stats["wrong"]
        address_rows.append(
            {
                "address_id": a,
                "name": ADDRESS_NAMES.get(a, str(a)),
                "photos": total,
                "fingerprint_photos": sizes.get(a, 0),
                "dino_ok": stats["dino_ok"],
                "dino_wrong": stats["dino_wrong"],
                "dino_none": stats["dino_none"],
                "hybrid_ok": stats["hybrid_ok"],
                "hybrid_ok_norm": stats["hybrid_ok_norm"],
                "hybrid_fixed": stats["hybrid_fixed"],
                "wrong": wrong,
                "error_rate": wrong / total if total else 0.0,
                "confusions": [
                    {
                        "address_id": b,
                        "name": ADDRESS_NAMES.get(b, str(b)),
                        "count": count,
                    }
                    for b, count in confusions[a].most_common(3)
                ],
            }
        )

    # ---- тест различимости ----
    print(
        f"[stats] компонентный тест: W={len(groups_w)} C={len(groups_c)} "
        f"E={len(groups_e)}",
        flush=True,
    )

    all_run_ids = {group[0] for group in groups_w + groups_c + groups_e}
    relevant_fps = set(fp_addr)
    candidates_by_run = load_candidates(all_run_ids, relevant_fps)

    test_w, _rows_w = component_test(groups_w, candidates_by_run, fp_addr)
    test_c, _rows_c = component_test(groups_c, candidates_by_run, fp_addr)
    test_e, _rows_e = component_test(groups_e, candidates_by_run, fp_addr)

    # разбивка по конкретным парам для главных ошибок
    pair_reports = []
    for (exp, rival), group in sorted(
        pair_groups.items(), key=lambda item: -len(item[1])
    )[:12]:
        summary, _ = component_test(group, candidates_by_run, fp_addr)
        pair_reports.append(
            {
                "expected": exp,
                "expected_name": ADDRESS_NAMES.get(exp, str(exp)),
                "predicted": rival,
                "predicted_name": ADDRESS_NAMES.get(rival, str(rival)),
                "count": len(group),
                "test": summary,
            }
        )

    labelled = sum(stats["photos"] for stats in per.values())
    totals = {
        "items": len(rows),
        "labelled": labelled,
        "unlabelled": len(rows) - labelled,
        "addresses": len(per),
        "dino_ok": sum(stats["dino_ok"] for stats in per.values()),
        "dino_wrong": sum(stats["dino_wrong"] for stats in per.values()),
        "dino_none": sum(stats["dino_none"] for stats in per.values()),
        "hybrid_ok": sum(stats["hybrid_ok"] for stats in per.values()),
        "hybrid_ok_norm": sum(stats["hybrid_ok_norm"] for stats in per.values()),
        "hybrid_fixed": sum(stats["hybrid_fixed"] for stats in per.values()),
        "hybrid_rescued": sum(stats["hybrid_rescued"] for stats in per.values()),
        "wrong": sum(stats["wrong"] for stats in per.values()),
        "no_fingerprint_photos": sum(
            stats["photos"]
            for a, stats in per.items()
            if not sizes.get(a, 0)
        ),
        "no_fingerprint_wrong": sum(
            stats["wrong"]
            for a, stats in per.items()
            if not sizes.get(a, 0)
        ),
    }

    report = {
        "run_id": args.run_id,
        "totals": totals,
        "addresses": address_rows,
        "discrimination": {
            "wrong": test_w,
            "hybrid_fixed": test_c,
            "easy": test_e,
            "pairs": pair_reports,
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"run{args.run_id}.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"# Подробная статистика по адресам — run {args.run_id}",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Только чтение: БД и слепки не изменялись.",
        "",
        f"Элементов: {totals['items']}, подписано: {totals['labelled']} "
        f"(варианты названия из label_variants_run4).",
        f"DINO совпадений: {totals['dino_ok']} "
        f"({totals['dino_ok'] / labelled * 100:.1f}%), "
        f"HYBRID совпадений (строго): {totals['hybrid_ok']} "
        f"({totals['hybrid_ok'] / labelled * 100:.1f}%), "
        f"с вариантами: {totals['hybrid_ok_norm']} "
        f"({totals['hybrid_ok_norm'] / labelled * 100:.1f}%), "
        f"ошибок: {totals['wrong']} "
        f"({totals['wrong'] / labelled * 100:.2f}%).",
        "",
        "Адресов без активного слепка: "
        f"{sum(1 for a in per if not sizes.get(a, 0))}, фото на них: "
        f"{totals['no_fingerprint_photos']}, ошибок на них: "
        f"{totals['no_fingerprint_wrong']}.",
        "",
        "## По адресам",
        "",
        "| Адрес | Фото | В слепке | DINO ок | HYBRID ок | Ок с вариантами | "
        "Ошибок | % ошибок | Главный противник |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in address_rows:
        top = row["confusions"][0] if row["confusions"] else None
        conf = (
            f"{top['name']} ({top['count']})" if top else "—"
        )
        lines.append(
            f"| {row['address_id']} {row['name']} | {row['photos']} | "
            f"{row['fingerprint_photos']} | {row['dino_ok']} | "
            f"{row['hybrid_ok']} | {row['hybrid_ok_norm']} | {row['wrong']} | "
            f"{row['error_rate'] * 100:.1f}% | {conf} |"
        )

    lines += [
        "",
        "## Различимость: правильный слепок против «противника»",
        "",
        "Группы: **W** — ошибочные фото (HYBRID указал другой адрес); "
        "**C** — DINO ошибся, HYBRID исправил; **E** — оба правы (сравнение с "
        "лучшим чужим кандидатом в TOP-15). Доля — в скольких % пар компонент "
        "ставит правильный слепок выше «противника».",
        "",
        "| Группа | Пар | " + " | ".join(METRIC_LABELS[m] for m in METRICS) + " |",
        "|---|---:|" + "---:|" * len(METRICS),
    ]
    for key, label in (("wrong", "W ошибки"), ("hybrid_fixed", "C исправленные"), ("easy", "E лёгкие")):
        test = report["discrimination"][key]
        if not test.get("n"):
            continue
        shares = test["win_share_best"]
        lines.append(
            f"| {label} | {test['n']} | "
            + " | ".join(f"{shares[m] * 100:.0f}%" for m in METRICS)
            + " |"
        )

    prod = report["discrimination"]["wrong"].get("prod_winner")
    if prod:
        lines += [
            "",
            f"В группе ошибок оценка (лучшая сумма по адресам) была на стороне "
            f"правильного адреса в {prod['exp'] * 100:.0f}% пар — эти ошибки "
            f"сделали правила серии/соседей, а не сама оценка.",
        ]

    if pair_reports:
        lines += [
            "",
            "## По конкретным парам (только ошибки)",
            "",
            "| Пара | Пар | " + " | ".join(METRIC_LABELS[m] for m in METRICS) + " |",
            "|---|---:|" + "---:|" * len(METRICS),
        ]
        for pair in pair_reports:
            test = pair["test"]
            if not test.get("n"):
                lines.append(
                    f"| {pair['expected_name']} → {pair['predicted_name']} | "
                    f"{pair['count']} (нет данных) | " + " | ".join("—" for _ in METRICS) + " |"
                )
                continue
            shares = test["win_share_best"]
            lines.append(
                f"| {pair['expected_name']} → {pair['predicted_name']} | {test['n']} | "
                + " | ".join(f"{shares[m] * 100:.0f}%" for m in METRICS)
                + " |"
            )

    missing_note = []
    for key in ("wrong", "hybrid_fixed", "easy"):
        test = report["discrimination"][key]
        if test.get("missing"):
            missing_note.append(f"{key}: {test['missing']}")
    if missing_note:
        lines += [
            "",
            "Не сравнено (нет нужного кандидата в TOP-15): " + "; ".join(missing_note) + ".",
        ]

    report_path = Path(
        f"data/reports/batch_stats_{date.today():%Y%m%d}_run{args.run_id}.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[stats] json: {json_path}", flush=True)
    print(f"[stats] report: {report_path}", flush=True)
    print(json.dumps(totals, ensure_ascii=False, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

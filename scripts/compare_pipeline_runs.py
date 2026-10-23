#!/usr/bin/env python
"""
Сравнить результаты полного прогона с сохранённым снимком прошлого.

Снимок делает скрипт перед очисткой базы (data/reports/before_reset_*.json):
для каждого фото он содержит DINO, HYBRID и QWEN. После повторного прогона
этот скрипт находит те же файлы по (имя, размер) и отвечает:

* совпал ли лучший слепок DINO и адрес;
* совпал ли итог HYBRID;
* совпали ли клиент/бренд/категория и описание QWEN;
* не изменилась ли точность по адресу из имени файла;
* как изменилось время этапов.

Ничего не пишет в базу.

    .venv/bin/python scripts/compare_pipeline_runs.py \
        data/reports/before_reset_20261023.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "scripts"))

from app.ingest.database import get_connection  # noqa: E402
from evaluate_sorting import expected_address, load_addresses  # noqa: E402

FIELDS = ("client", "brand", "category")


def load_current() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id, p.filename, p.size_bytes, p.taken_at,
                       d.dino_best_id, d.dino_score, d.dino_margin,
                       d.dino_confidence, d.dino_status, d.dino_time_sec,
                       h.hybrid_final_id, h.hybrid_score, h.hybrid_margin,
                       h.status,
                       q.status, q.client, q.brand, q.category, q.tags,
                       q.description, q.qwen_time_sec
                FROM public.photos p
                LEFT JOIN LATERAL (
                    SELECT * FROM public.dino_runs r
                    WHERE r.photo_id = p.photo_id AND r.status = 'DONE'
                    ORDER BY r.finished_at DESC NULLS LAST, r.run_id DESC
                    LIMIT 1
                ) d ON TRUE
                LEFT JOIN LATERAL (
                    SELECT * FROM public.hybrid_results hr
                    WHERE hr.photo_id = p.photo_id
                    ORDER BY hr.hybrid_run_id DESC LIMIT 1
                ) h ON TRUE
                LEFT JOIN public.photo_qwen q ON q.photo_id = p.photo_id
                ORDER BY p.photo_id
                """
            )
            columns = [item[0] for item in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def fingerprint_addresses() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT af.fingerprint_id, af.address_id
                FROM public.address_fingerprints AS af
                JOIN public.fingerprints AS f
                  ON f.fingerprint_id = af.fingerprint_id AND f.active
                WHERE af.active
                """
            )
            return {str(row[0]): int(row[1]) for row in cur.fetchall()}


def key(row: dict) -> tuple[str, int]:
    return (str(row.get("filename") or ""), int(row.get("size_bytes") or 0))


def norm(value: object) -> str:
    return str(value or "").strip().casefold()


def accuracy(rows: list[dict], column: str, addresses, fps) -> dict:
    labelled = 0
    correct = 0

    for row in rows:
        expected = expected_address(row["filename"], addresses)

        if expected is None:
            continue

        labelled += 1
        got = fps.get(str(row.get(column) or ""))

        if got == expected:
            correct += 1

    return {
        "labelled": labelled,
        "correct": correct,
        "accuracy": round(correct / labelled, 4) if labelled else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", help="снимок до очистки (JSON)")
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)

    old_rows = json.loads(Path(args.before).read_text("utf-8"))["rows"]
    new_rows = load_current()

    old_by_key = {key(row): row for row in old_rows}
    new_by_key = {key(row): row for row in new_rows}

    common = sorted(set(old_by_key) & set(new_by_key))
    fps = fingerprint_addresses()
    addresses = load_addresses()

    pairs = [(old_by_key[item], new_by_key[item]) for item in common]

    dino_same_best = sum(
        1
        for old, new in pairs
        if old.get("dino_best_id") and old.get("dino_best_id") == new.get("dino_best_id")
    )
    dino_old_best = sum(1 for old, _ in pairs if old.get("dino_best_id"))

    old_address = [
        {"filename": old["filename"], "dino_best_id": old.get("dino_best_id")}
        for old, _ in pairs
    ]
    new_address = [
        {"filename": new["filename"], "dino_best_id": new.get("dino_best_id")}
        for _, new in pairs
    ]

    qwen_old = [
        old for old, _ in pairs if old.get("status") == "DONE"
    ]
    qwen_both = [
        (old, new) for old, new in pairs if old.get("status") == "DONE"
    ]

    scores = [
        (
            float(old["dino_score"]) if old.get("dino_score") is not None else None,
            float(new["dino_score"]) if new.get("dino_score") is not None else None,
        )
        for old, new in pairs
        if old.get("dino_score") is not None and new.get("dino_score") is not None
    ]
    deltas = [abs(a - b) for a, b in scores]

    report = {
        "old_photos": len(old_rows),
        "new_photos": len(new_rows),
        "matched": len(common),
        "only_old": len(set(old_by_key) - set(new_by_key)),
        "only_new": len(set(new_by_key) - set(old_by_key)),
        "dino_same_best": dino_same_best,
        "dino_compared": dino_old_best,
        "dino_same_best_rate": round(dino_same_best / dino_old_best, 4)
        if dino_old_best
        else None,
        "dino_score_delta_mean": round(sum(deltas) / len(deltas), 6) if deltas else None,
        "dino_score_delta_max": round(max(deltas), 6) if deltas else None,
        "accuracy_old": accuracy(old_address, "dino_best_id", addresses, fps),
        "accuracy_new": accuracy(new_address, "dino_best_id", addresses, fps),
        "qwen_old_done": len(qwen_old),
        "qwen_new_done": sum(1 for _, new in pairs if new.get("status") == "DONE"),
        "qwen_client_same": sum(
            1
            for old, new in qwen_both
            if norm(old.get("client")) and norm(old.get("client")) == norm(new.get("client"))
        ),
        "qwen_brand_same": sum(
            1
            for old, new in qwen_both
            if norm(old.get("brand")) and norm(old.get("brand")) == norm(new.get("brand"))
        ),
        "qwen_category_same": sum(
            1
            for old, new in qwen_both
            if norm(old.get("category"))
            and norm(old.get("category")) == norm(new.get("category"))
        ),
        "qwen_description_same": sum(
            1
            for old, new in qwen_both
            if norm(old.get("description"))
            and norm(old.get("description")) == norm(new.get("description"))
        ),
        "time_old_dino_avg": round(
            sum(float(old["dino_time_sec"]) for old, _ in pairs if old.get("dino_time_sec"))
            / max(1, sum(1 for old, _ in pairs if old.get("dino_time_sec"))),
            3,
        ),
        "time_new_dino_avg": round(
            sum(float(new["dino_time_sec"]) for _, new in pairs if new.get("dino_time_sec"))
            / max(1, sum(1 for _, new in pairs if new.get("dino_time_sec"))),
            3,
        ),
        "only_old_samples": [item[0] for item in sorted(set(old_by_key) - set(new_by_key))[:10]],
        "only_new_samples": [item[0] for item in sorted(set(new_by_key) - set(old_by_key))[:10]],
    }

    if args.json:
        Path(args.json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
        )

    for name, value in report.items():
        if name.endswith("_samples"):
            continue
        print(f"{name}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Дописать отсутствующие описания QWEN (режим only_missing).

    .venv/bin/python scripts/enqueue_qwen_missing.py --dry-run
    .venv/bin/python scripts/enqueue_qwen_missing.py --apply

Ставит в очередь ТОЛЬКО фото без непустого описания (photo_qwen.description).
Уже описанные фото не трогаются — их результаты остаются как есть
(владелец, 20.11.2026). Фото с отсутствующим файлом-оригиналом пропускаются.

Логика зеркалит POST /v1/jobs/qwen с only_missing=true, но работает без
API (для systemd-таймера).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402
from app.jobs import database as jobs_db  # noqa: E402
from app.runs import history as run_history  # noqa: E402


def load_missing() -> tuple[list[str], int]:
    """photo_ids без описания и с существующим файлом + счётчик пропусков."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id, p.source_path
                FROM public.photos AS p
                LEFT JOIN public.photo_qwen AS q
                       ON q.photo_id = p.photo_id
                      AND q.description IS NOT NULL
                      AND btrim(q.description) <> ''
                WHERE q.photo_id IS NULL
                ORDER BY p.photo_id
                """
            )
            rows = cur.fetchall()

    targets: list[str] = []
    missing = 0
    for photo_id, source_path in rows:
        if source_path and Path(str(source_path)).is_file():
            targets.append(str(photo_id))
        else:
            missing += 1
    return targets, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    if args.apply == args.dry_run:
        print("укажите ровно одно: --dry-run или --apply", file=sys.stderr)
        return 2

    targets, missing = load_missing()
    print(
        f"фото без описания: {len(targets)}; "
        f"без файла на диске: {missing}"
    )

    if args.dry_run:
        return 0

    history_id = run_history.create_run(
        kind="qwen",
        mode="manual",
        title="QWEN: дописать отсутствующие",
        total=len(targets),
    )

    queued = 0
    deduped = 0
    job_ids: list[int] = []
    for photo_id in targets:
        job_id = jobs_db.enqueue_qwen(
            photo_id,
            source="manual",
            run_history_id=history_id,
        )
        if job_id is None:
            deduped += 1
        else:
            job_ids.append(job_id)
            queued += 1

    run_history.add_jobs(history_id, job_ids, skipped=deduped)
    run_history.finish_enqueue(history_id, total=len(targets), skipped=deduped)

    print(
        f"поставлено: {queued}; пропущено активных: {deduped}; "
        f"run_history_id: {history_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

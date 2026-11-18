#!/usr/bin/env python3
"""Массовая постановка QWEN-описаний по всему корпусу (кропы + полный кадр).

    .venv/bin/python scripts/enqueue_qwen_backlog.py --dry-run
    .venv/bin/python scripts/enqueue_qwen_backlog.py --apply

Зачем: у 38 752 кропов (photo_regions) нет описания QWEN (qwen_status IS
NULL), а чтение кропа — главный источник client/brand. run_photo() сам
читает кропы, если они есть, и сам запускает детекцию «по требованию» для
фото без регионов — поэтому в очередь ставятся только QWEN_PHOTO.

Порядок приоритета (воркер берёт задания по id):
    1) фото, у которых client и brand пусты, а кропы не описаны;
    2) фото вообще без регионов (детекция+описание по требованию);
    3) остальные фото с неописанными кропами.

Дедупликация как в enqueue_qwen: активные (PENDING/RUNNING) QWEN_PHOTO
по photo_id не дублируются. Постановка батчами в одной транзакции.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402

SOURCE = "automation"


def photo_groups(cur) -> dict[str, list[str]]:
    """Разложить целевые фото по приоритетным группам."""

    cur.execute(
        """
        SELECT p.photo_id,
               (q.client IS NOT NULL OR q.brand IS NOT NULL) AS has_client,
               EXISTS (SELECT 1 FROM public.photo_regions r
                       WHERE r.photo_id = p.photo_id) AS has_regions,
               EXISTS (SELECT 1 FROM public.photo_regions r
                       WHERE r.photo_id = p.photo_id
                         AND r.qwen_status IS NOT NULL) AS crops_described
        FROM public.photos p
        LEFT JOIN public.photo_qwen q ON q.photo_id = p.photo_id
        WHERE NOT EXISTS (
            SELECT 1 FROM public.job_queue j
            WHERE j.job_type = 'QWEN_PHOTO'
              AND j.status IN ('PENDING', 'RUNNING')
              AND j.payload ->> 'photo_id' = p.photo_id
        )
        ORDER BY p.photo_id
        """
    )
    groups: dict[str, list[str]] = {"priority": [], "detect_only": [], "rest": []}
    for photo_id, has_client, has_regions, crops_described in cur.fetchall():
        if not has_regions and not crops_described:
            if not has_client:
                groups["priority"].append(photo_id)
            else:
                groups["detect_only"].append(photo_id)
        elif not crops_described:
            if not has_client:
                groups["priority"].append(photo_id)
            else:
                groups["rest"].append(photo_id)
        # Фото с описанными кропами не трогаем: у них уже есть полный прогон.
    return groups


def enqueue_batch(cur, photo_ids: list[str]) -> int:
    cur.execute(
        """
        INSERT INTO public.job_queue (job_type, payload, status)
        SELECT 'QWEN_PHOTO', jsonb_build_object('photo_id', pid, 'source', %(source)s::text), 'PENDING'
        FROM unnest(%(ids)s::text[]) AS pid
        WHERE NOT EXISTS (
            SELECT 1 FROM public.job_queue j
            WHERE j.job_type = 'QWEN_PHOTO'
              AND j.status IN ('PENDING', 'RUNNING')
              AND j.payload ->> 'photo_id' = pid
        )
        """,
        {"source": SOURCE, "ids": photo_ids},
    )
    return cur.rowcount


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch", type=int, default=2000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.apply == args.dry_run:
        print("укажите ровно одно: --dry-run или --apply", file=sys.stderr)
        return 2

    with get_connection() as conn:
        with conn.cursor() as cur:
            groups = photo_groups(cur)
            total = sum(len(v) for v in groups.values())

            if not args.apply:
                report = {
                    "dry_run": True,
                    "priority_empty_client_brand": len(groups["priority"]),
                    "no_regions": len(groups["detect_only"]),
                    "crops_undescribed_rest": len(groups["rest"]),
                    "total": total,
                }
                if args.json:
                    print(json.dumps(report, ensure_ascii=False))
                else:
                    print(f"приоритет 1 (client/brand пуст, кропы не описаны): "
                          f"{len(groups['priority'])}")
                    print(f"приоритет 2 (без регионов — детекция по требованию): "
                          f"{len(groups['detect_only'])}")
                    print(f"приоритет 3 (кропы не описаны, клиент известен): "
                          f"{len(groups['rest'])}")
                    print(f"итого к постановке: {total}")
                return 0

            enqueued = 0
            for name in ("priority", "detect_only", "rest"):
                ids = groups[name]
                for start in range(0, len(ids), args.batch):
                    chunk = ids[start : start + args.batch]
                    enqueued += enqueue_batch(cur, chunk)
                    conn.commit()

    print(f"поставлено заданий QWEN_PHOTO: {enqueued} (из {total} целевых)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

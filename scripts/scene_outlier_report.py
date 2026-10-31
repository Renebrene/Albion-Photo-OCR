#!/usr/bin/env python3
"""Read-only scene-neighbour report for suspect QWEN results.

A detector error can leave one photo with a crop of a bus (or another object)
while its neighbours in the same scene read the billboard. This report groups
photos by the latest HYBRID screen and capture gap, then flags photos whose
client/brand does not occur in any neighbour.

By default nothing is written to the database: the reading transaction is
READ ONLY and the report goes to data/reports/. With --enqueue-outliers the
script additionally queues a full-frame QWEN rescan for every `outlier`
photo (never for `weak`). Run it after QWEN has finished a period.

    .venv/bin/python scripts/scene_outlier_report.py \
        --date-from 2026-10-24 --date-to 2026-10-31 --out data/reports/scene_outliers.json

    .venv/bin/python scripts/scene_outlier_report.py \
        --date-from 2026-10-24 --date-to 2026-10-31 --enqueue-outliers
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.ingest.database import get_connection
from app.qwen.crop_aggregation import _compact

SCREEN_SQL = """
    (SELECT h.hybrid_final_id
       FROM public.hybrid_results AS h
      WHERE h.photo_id = p.photo_id AND h.status = 'DONE'
      ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC
      LIMIT 1)
"""


def load_rows(date_from: str, date_to: str) -> list[dict]:
    sql = f"""
        SELECT p.photo_id,
               COALESCE({SCREEN_SQL}, '') AS screen,
               COALESCE(r.photo_taken_at, p.taken_at) AS taken_at,
               q.client,
               q.brand,
               q.tags
        FROM public.photos AS p
        JOIN public.photo_qwen AS q
          ON q.photo_id = p.photo_id AND q.status = 'DONE'
        LEFT JOIN public.photo_regions AS r
          ON r.photo_id = p.photo_id AND r.kind = 'billboard'
         AND r.region_id = (
             SELECT MIN(r2.region_id)
               FROM public.photo_regions AS r2
              WHERE r2.photo_id = p.photo_id AND r2.kind = 'billboard'
         )
        WHERE COALESCE(r.photo_taken_at, p.taken_at) >= %s::date
          AND COALESCE(r.photo_taken_at, p.taken_at) < (%s::date + interval '1 day')
        ORDER BY screen, taken_at, p.photo_id
    """  # noqa: S608 - fixed SQL, dates are parameters

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, (date_from, date_to))
            rows = cur.fetchall()

    return [
        {
            "photo_id": str(row[0]),
            "screen": str(row[1] or ""),
            "taken_at": row[2],
            "client": row[3],
            "brand": row[4],
            "tags": list(row[5] or []),
        }
        for row in rows
    ]


def build_groups(rows: list[dict], gap_seconds: int) -> list[list[dict]]:
    groups: list[list[dict]] = []
    current: list[dict] = []

    for row in rows:
        if not current:
            current = [row]
            continue

        previous = current[-1]
        same_screen = row["screen"] and row["screen"] == previous["screen"]
        gap = (row["taken_at"] - previous["taken_at"]).total_seconds()
        if same_screen and gap <= gap_seconds:
            current.append(row)
        else:
            groups.append(current)
            current = [row]

    if current:
        groups.append(current)
    return groups


GENERIC_TOKENS = {
    "ооо", "оао", "пао", "зао", "ао", "ип",
    "реклама", "рекламный", "бренд", "магазин", "сеть", "тц", "молл",
    "баннер", "щит", "акция", "сцена", "улица",
}


def _tokens(value: object) -> set[str]:
    text = str(value or "").casefold().replace("ё", "е")
    tokens = set()
    for token in re.split(r"[^\w]+", text, flags=re.UNICODE):
        if len(token) >= 3 and token not in GENERIC_TOKENS:
            tokens.add(token)
    return tokens


def _match_level(own: object, neighbour_values: set[str]) -> str:
    """full — точное совпадение, partial — вхождение/общий значимый токен."""

    text = str(own or "").strip()
    if not text:
        return "empty"

    key = _compact(text)
    if key in neighbour_values:
        return "full"

    own_tokens = _tokens(text)
    for candidate in neighbour_values:
        if key and (key in candidate or candidate in key):
            return "partial"
        if own_tokens & _tokens(candidate):
            return "partial"
    return "none"


def _names(row: dict) -> set[str]:
    result = set()
    for value in (row.get("client"), row.get("brand")):
        text = str(value or "").strip()
        if text:
            result.add(_compact(text))
    return result


def find_suspects(groups: list[list[dict]], min_group: int) -> list[dict]:
    suspects: list[dict] = []

    for group in groups:
        if len(group) < min_group:
            continue

        for row in group:
            own = _names(row)
            if not own:
                continue

            neighbour_names: set[str] = set()
            neighbour_tags: set[str] = set()
            for other in group:
                if other is row:
                    continue
                neighbour_names |= _names(other)
                neighbour_tags |= {
                    _compact(tag) for tag in other.get("tags") or [] if str(tag).strip()
                }

            brand_match = _match_level(row.get("brand"), neighbour_names)
            client_match = _match_level(row.get("client"), neighbour_names)
            own_tags = {
                _compact(tag) for tag in row.get("tags") or [] if str(tag).strip()
            }
            tag_overlap = len(own_tags & neighbour_tags)

            # Явный выброс: ни бренд, ни клиент не совпали даже частично.
            if brand_match == "none" and client_match in {"none", "empty"}:
                severity = "outlier"
            # Не выброс, но серия должна совпадать хотя бы частично.
            elif (
                brand_match != "full"
                or client_match not in {"full", "empty"}
                or tag_overlap == 0
            ):
                severity = "weak"
            else:
                continue

            suspects.append(
                {
                    "severity": severity,
                    "photo_id": row["photo_id"],
                    "screen": row["screen"],
                    "taken_at": row["taken_at"].isoformat(),
                    "client": row["client"],
                    "brand": row["brand"],
                    "brand_match": brand_match,
                    "client_match": client_match,
                    "tag_overlap": tag_overlap,
                    "tags": row["tags"][:10],
                    "group_size": len(group),
                    "neighbour_clients": sorted(
                        {str(other["client"]) for other in group if other is not row and other["client"]}
                    )[:8],
                    "neighbour_brands": sorted(
                        {str(other["brand"]) for other in group if other is not row and other["brand"]}
                    )[:8],
                    "neighbour_photo_ids": [
                        other["photo_id"] for other in group if other is not row
                    ][:8],
                }
            )

    suspects.sort(key=lambda item: (item["severity"] != "outlier", item["taken_at"]))
    return suspects


def enqueue_outliers(suspects: list[dict]) -> dict:
    """Queue full-frame QWEN rescan for `outlier` photos only."""

    from app.jobs import database as jobs_db
    from app.qwen import processor as qwen
    from app.runs import history as run_history

    photo_ids = [item["photo_id"] for item in suspects if item["severity"] == "outlier"]
    if not photo_ids:
        return {"outliers": 0, "jobs": 0, "skipped": 0, "run_history_id": None}

    config = qwen.resolve_settings()
    history_id = run_history.create_run(
        kind="qwen",
        mode="manual",
        title="QWEN: пересканирование выбросов сцены (полный кадр)",
        total=len(photo_ids),
    )

    job_ids: list[int] = []
    skipped = 0
    for photo_id in photo_ids:
        job_id = jobs_db.enqueue_qwen(
            photo_id,
            source="automation",
            provider=config.get("provider"),
            model=config.get("model"),
            run_history_id=history_id,
            skip_refine=True,
            full_frame=True,
        )
        if job_id is None:
            skipped += 1
        else:
            job_ids.append(job_id)

    run_history.add_jobs(history_id, job_ids, skipped=skipped)
    run_history.finish_enqueue(history_id, total=len(photo_ids), skipped=0)

    return {
        "outliers": len(photo_ids),
        "jobs": len(job_ids),
        "skipped": skipped,
        "run_history_id": history_id,
        "model": config.get("model"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", required=True)
    parser.add_argument("--date-to", required=True)
    parser.add_argument("--gap", type=int, default=10, help="секунд между соседями")
    parser.add_argument("--min-group", type=int, default=3)
    parser.add_argument(
        "--enqueue-outliers",
        action="store_true",
        help="поставить outlier-фото на пересканирование полного кадра",
    )
    parser.add_argument("--out", help="путь JSON-отчёта")
    args = parser.parse_args()

    rows = load_rows(args.date_from, args.date_to)
    groups = build_groups(rows, args.gap)
    suspects = find_suspects(groups, args.min_group)

    out = Path(args.out) if args.out else (
        Path("data") / "reports"
        / f"scene_outliers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_from": args.date_from,
        "date_to": args.date_to,
        "gap_seconds": args.gap,
        "min_group": args.min_group,
        "photos": len(rows),
        "groups": len(groups),
        "suspects": len(suspects),
        "writes_performed": False,
        "items": suspects,
    }

    if args.enqueue_outliers:
        enqueued = enqueue_outliers(suspects)
        payload["writes_performed"] = bool(enqueued["jobs"])
        payload["enqueued"] = enqueued

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"photos={len(rows)} groups={len(groups)} suspects={len(suspects)}")
    if args.enqueue_outliers:
        print(f"enqueued: {payload['enqueued']}")
    print(f"report: {out}")
    for item in suspects[:10]:
        print(
            f"  {item['photo_id']}  {item['client']} / {item['brand']}  "
            f"group={item['group_size']}  neighbours brands={item['neighbour_brands']}"
        )


if __name__ == "__main__":
    main()

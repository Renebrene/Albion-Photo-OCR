#!/usr/bin/env python
"""
Почистить уже сохранённые карточки от запрещённых к выдаче слов.

Фильтр (`app/qwen/sanitize.py`) применяется в момент записи результата QWEN
и ручной правки, поэтому строки, сохранённые до появления списка, его не
проходят. Скрипт догоняет их тем же правилом: целое слово без учёта регистра
(«педо» в «торпедо» не совпадает).

По умолчанию — только отчёт (dry-run): ничего не меняет. `--apply` обновляет
`photo_qwen`, предварительно складывая прежнюю строку в
`photo_qwen_history` с пометкой `forbidden-filter`, — данные не теряются.

Использование:

    .venv/bin/python scripts/sanitize_forbidden_words.py
    .venv/bin/python scripts/sanitize_forbidden_words.py --apply
    .venv/bin/python scripts/sanitize_forbidden_words.py --words педо,мат
    .venv/bin/python scripts/sanitize_forbidden_words.py --photo-id PH_ab...

Код возврата 1, если `--apply` упал на конкретной фото; 0 — успех или нечего
менять.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from psycopg.types.json import Json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402
from app.qwen import database as qwen_db  # noqa: E402
from app.qwen import processor  # noqa: E402
from app.qwen.sanitize import find_forbidden  # noqa: E402

REPORT_NAME = "forbidden_words_cleanup"
REPLACED_BY = "forbidden-filter"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Убрать запрещённые слова из сохранённых карточек",
    )
    parser.add_argument("--apply", action="store_true", help="записать изменения")
    parser.add_argument(
        "--words",
        default="",
        help="свой список через запятую (по умолчанию — настройка QWEN)",
    )
    parser.add_argument(
        "--photo-id",
        dest="photo_ids",
        action="append",
        default=None,
        help="только это фото (можно повторить)",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="не больше N карточек (0 — все)"
    )
    return parser.parse_args(argv)


def _words(args: argparse.Namespace) -> list[str]:
    if args.words.strip():
        return [item.strip() for item in args.words.split(",") if item.strip()]

    return processor.forbidden_words()


def _rows(words: list[str], photo_ids: list[str] | None, limit: int) -> list[dict]:
    """Карточки, где хотя бы одно поле содержит запрещённое слово целиком."""

    sql = """
        SELECT photo_id, description, address, client, brand, category, tags
        FROM public.photo_qwen
    """
    params: list[object] = []
    conditions: list[str] = []

    if photo_ids:
        conditions.append("photo_id = ANY(%s)")
        params.append(list(photo_ids))

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY photo_id"

    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    rows: list[dict] = []

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)

        for row in cur.fetchall():
            fields = {
                "description": row[1],
                "address": row[2],
                "client": row[3],
                "brand": row[4],
                "category": row[5],
                "tags": list(row[6] or []),
            }

            if find_forbidden(fields, words):
                rows.append({"photo_id": row[0], **fields})

    return rows


def _sanitized(fields: dict, words: list[str]) -> dict:
    from app.qwen.sanitize import sanitize_fields

    cleaned = sanitize_fields(fields, words)

    # sanitize_fields трогает только client/brand/tags/description — адрес и
    # категорию возвращаем как были.
    return {**fields, **cleaned}


def _apply(row: dict, fields: dict) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        qwen_db._archive_previous(cur, row["photo_id"], REPLACED_BY)
        cur.execute(
            """
            UPDATE public.photo_qwen
               SET description = %s, client = %s, brand = %s, tags = %s
             WHERE photo_id = %s
            """,
            (
                fields["description"],
                fields["client"],
                fields["brand"],
                Json(fields["tags"] or []),
                row["photo_id"],
            ),
        )


def _report_path() -> Path:
    from datetime import datetime

    folder = Path("data/reports")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return folder / f"{REPORT_NAME}_{stamp}.json"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    words = _words(args)

    if not words:
        print("Список запрещённых слов пуст — чистить нечего.", file=sys.stderr)
        return 0

    rows = _rows(words, args.photo_ids, args.limit)

    if not rows:
        print(f"Запрещённых слов ({', '.join(words)}) в сохранённых карточках нет.")
        return 0

    changes = [
        {
            "photo_id": row["photo_id"],
            "before": {
                "description": row["description"],
                "client": row["client"],
                "brand": row["brand"],
                "tags": row["tags"],
            },
            "after": {
                "description": (clean := _sanitized(row, words))["description"],
                "client": clean["client"],
                "brand": clean["brand"],
                "tags": clean["tags"],
            },
        }
        for row in rows
    ]

    for item in changes[:20]:
        before, after = item["before"], item["after"]
        print(f"{item['photo_id']}")
        print(f"  было:  client={before['client']!r} brand={before['brand']!r}")
        print(f"         description={str(before['description'])[:80]!r}")
        print(f"  стало: client={after['client']!r} brand={after['brand']!r}")
        print(f"         description={str(after['description'])[:80]!r}")

    if len(changes) > 20:
        print(f"... ещё {len(changes) - 20}")

    report = _report_path()
    report.write_text(
        json.dumps(
            {"words": words, "apply": bool(args.apply), "items": changes},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Карточек затронуто: {len(changes)}. Отчёт: {report}")

    if not args.apply:
        print("Dry-run: ничего не изменено. Для записи повторите с --apply.")
        return 0

    failed = 0

    for index, item in enumerate(changes, start=1):
        row = next(r for r in rows if r["photo_id"] == item["photo_id"])

        try:
            _apply(row, _sanitized(row, words))
        except Exception as exc:  # noqa: BLE001 — одна карточка не валит прогон
            failed += 1
            print(f"ОШИБКА {item['photo_id']}: {exc}", file=sys.stderr)

        if index % 50 == 0:
            print(f"  {index}/{len(changes)}")

    print(f"Обновлено: {len(changes) - failed}, ошибок: {failed}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

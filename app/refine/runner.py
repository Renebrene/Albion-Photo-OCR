"""
«Уточнение»: связать кадры одной серии и привести чтения к одному виду.

Запускается не кнопкой, а автоматически после того, как QWEN закончил: до
этого сравнивать нечего. Этап выключен по умолчанию (app/refine/config.py).

Что делает:

1. берёт кадры с кропом (у кропа есть хеш и время съёмки фото);
2. собирает серии: один экран, интервал ≤ N секунд, разница хешей кропов ≤ 6;
3. внутри серии дополняет пустые клиент/бренд и заменяет редкие короткие
   чтения полными — только когда группа не спорная;
4. пишет изменения в photo_qwen штатным путём: прежняя строка уходит в
   photo_qwen_history, поэтому всё обратимо.

Спорные группы (разные имена внутри одной картинки) не меняются — их считаем
и показываем в отчёте.
"""

from __future__ import annotations

from collections import defaultdict

from app.billboard.phash import from_db
from app.ingest.database import get_connection
from app.qwen import database as qwen_db
from app.refine import config as refine_config
from app.refine.logic import (
    DEFAULT_MAX_DISTANCE,
    DEFAULT_FIELDS,
    Frame,
    build_groups,
    propose,
)

# Сколько кадров разбирать за один прогон: очередь и так идёт пачками, а
# этап дешёвый — ограничение только чтобы не держать транзакцию долго.
DEFAULT_LIMIT = 5000

_LATEST_SCREEN = """
    (SELECT h.hybrid_final_id FROM public.hybrid_results AS h
      WHERE h.photo_id = p.photo_id AND h.status = 'DONE'
      ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC
      LIMIT 1)
"""


def ready_count() -> int:
    """Сколько кадров готово к «Уточнению»: есть кроп с хешем и описание."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM public.photo_regions AS r
                JOIN public.photo_qwen AS q
                  ON q.photo_id = r.photo_id AND q.status = 'DONE'
                WHERE r.kind = 'billboard'
                  AND r.crop_phash IS NOT NULL
                """
            )
            row = cur.fetchone()

    return int(row[0]) if row else 0


def load_frames(limit: int = DEFAULT_LIMIT) -> list[Frame]:
    """Кадры, у которых есть кроп с хешем и описание QWEN."""

    limit = max(1, min(int(limit), 20000))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id,
                       COALESCE(r.photo_taken_at, p.taken_at) AS taken_at,
                       r.crop_phash,
                       """
                + _LATEST_SCREEN
                + """ AS screen,
                       q.client,
                       q.brand
                FROM public.photo_regions AS r
                JOIN public.photos AS p ON p.photo_id = r.photo_id
                JOIN public.photo_qwen AS q
                  ON q.photo_id = r.photo_id AND q.status = 'DONE'
                WHERE r.kind = 'billboard'
                  AND r.crop_phash IS NOT NULL
                ORDER BY screen, taken_at, p.photo_id
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        Frame(
            photo_id=row[0],
            taken_at=row[1],
            phash=from_db(row[2]),
            screen=row[3],
            client=row[4],
            brand=row[5],
        )
        for row in rows
    ]


def run_refine(
    *,
    limit: int = DEFAULT_LIMIT,
    fields: tuple[str, ...] = DEFAULT_FIELDS,
    dry_run: bool = False,
) -> dict:
    """
    Один прогон «Уточнения». Возвращает сводку (её сохраняет очередь).

    Выключенный этап — не ошибка: возвращаем `status="disabled"`, чтобы
    задание завершилось успешно и не повторялось.
    """

    if not refine_config.enabled():
        return {
            "status": "disabled",
            "frames": 0,
            "groups": 0,
            "filled": 0,
            "replaced": 0,
            "photos_changed": 0,
            "disputed_groups": 0,
        }

    frames = load_frames(limit)

    if not frames:
        return {
            "status": "empty",
            "frames": 0,
            "groups": 0,
            "filled": 0,
            "replaced": 0,
            "photos_changed": 0,
            "disputed_groups": 0,
        }

    groups = build_groups(
        frames,
        gap_seconds=refine_config.gap_seconds(),
        max_distance=DEFAULT_MAX_DISTANCE,
    )

    # Собираем изменения по фото: одно фото может получить и клиента, и бренд.
    changes: dict[str, dict[str, str]] = defaultdict(dict)
    filled = replaced = disputed_groups = 0
    disputed_samples: list[list[str]] = []

    for group in groups:
        group_disputed = False

        for field in fields:
            proposal = propose(group, field)

            if proposal["disputed"]:
                group_disputed = True
                if len(disputed_samples) < 10:
                    disputed_samples.append(proposal["disputed"])
                continue

            for photo_id, value in proposal["fill"].items():
                changes[photo_id][field] = value
                filled += 1

            for photo_id, (_old, new) in proposal["replace"].items():
                changes[photo_id][field] = new
                replaced += 1

        if group_disputed:
            disputed_groups += 1

    updated = 0

    if dry_run:
        # Пробный прогон: считаем, но ничего не пишем. Нужен, чтобы посмотреть
        # эффект до включения этапа.
        updated = len(changes)
    else:
        for photo_id, values in changes.items():
            if qwen_db.apply_refined_values(photo_id, values, reason="refine"):
                updated += 1

    return {
        "status": "dry_run" if dry_run else "done",
        "frames": len(frames),
        "groups": len(groups),
        "filled": filled,
        "replaced": replaced,
        "photos_changed": updated,
        "disputed_groups": disputed_groups,
        "disputed_samples": disputed_samples,
    }

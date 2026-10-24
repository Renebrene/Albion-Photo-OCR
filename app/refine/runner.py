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


def list_screens() -> list[tuple[str, int]]:
    """
    Экраны с числом кадров, по возрастанию имени.

    «Уточнение» сравнивает кадры одного экрана между собой, поэтому страница
    режется по экранам целиком: страница, разрезанная посреди экрана, теряла
    бы его остаток (проверено: так пропадало 1 273 кадра из 14 074).
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE("""
                + _LATEST_SCREEN
                + """, '') AS screen, count(*) AS frames
                FROM public.photo_regions AS r
                JOIN public.photos AS p ON p.photo_id = r.photo_id
                JOIN public.photo_qwen AS q
                  ON q.photo_id = r.photo_id AND q.status = 'DONE'
                WHERE r.kind = 'billboard'
                  AND r.crop_phash IS NOT NULL
                GROUP BY 1
                ORDER BY 1
                """
            )
            return [(row[0], int(row[1])) for row in cur.fetchall()]


def load_frames(limit: int = DEFAULT_LIMIT, *, screens: list[str] | None = None) -> list[Frame]:
    """
    Кадры, у которых есть кроп с хешем и описание QWEN.

    `screens` ограничивает чтение списком экранов — так страница не режется
    посреди экрана, и его кадры не теряются.

    Экран берётся с COALESCE: у кадра без вердикта его нет, а сравнение с NULL
    выкинуло бы такие кадры из выборки.
    """

    limit = max(1, min(int(limit), 20000))
    filter_sql = ""
    filter_params: list[object] = []

    if screens is not None:
        filter_sql = "AND COALESCE(" + _LATEST_SCREEN + ", '') = ANY(%s)"
        filter_params = [list(screens)]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id,
                       COALESCE(r.photo_taken_at, p.taken_at) AS taken_at,
                       r.crop_phash,
                       COALESCE("""
                + _LATEST_SCREEN
                + """, '') AS screen,
                       q.client,
                       q.brand
                FROM public.photo_regions AS r
                JOIN public.photos AS p ON p.photo_id = r.photo_id
                JOIN public.photo_qwen AS q
                  ON q.photo_id = r.photo_id AND q.status = 'DONE'
                WHERE r.kind = 'billboard'
                  AND r.crop_phash IS NOT NULL
                  """
                + filter_sql
                + """
                ORDER BY screen, taken_at, p.photo_id
                LIMIT %s
                """,
                filter_params + [limit],
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


def _screen_batches(screens: list[tuple[str, int]], limit: int) -> list[list[str]]:
    """
    Экраны, разложенные по страницам: экран целиком попадает в одну страницу.

    Экран, который сам больше страницы, идёт отдельной страницей — иначе его
    кадры не поместились бы никогда.
    """

    batches: list[list[str]] = []
    current: list[str] = []
    current_frames = 0

    for screen, frames in screens:
        if current and current_frames + frames > limit:
            batches.append(current)
            current = []
            current_frames = 0

        current.append(screen)
        current_frames += frames

    if current:
        batches.append(current)

    return batches


def run_refine(
    *,
    limit: int = DEFAULT_LIMIT,
    fields: tuple[str, ...] = DEFAULT_FIELDS,
    dry_run: bool = False,
    progress=None,
) -> dict:
    """
    Прогон «Уточнения» по всему корпусу. Возвращает сводку (её сохраняет очередь).

    Выключенный этап — не ошибка: возвращаем `status="disabled"`, чтобы
    задание завершилось успешно и не повторялось.

    Кадры читаются страницами по экранам (`limit` — размер страницы), а не
    одним LIMIT: одиночный проход разбирал только первые кадры, и повторный
    запуск перечитывал те же самые, так что остальные не обрабатывались
    никогда. Продолжение идёт по последнему экрану страницы, поэтому экраны
    не разрываются между страницами.

    `progress(done, total)` — та же обратная связь, что у остальных этапов:
    шапка показывает «Уточнение 5000 / 14074», а задание можно отменить (вызов
    пишет прогресс в очередь и проверяет статус задания).
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

    # Экраны с числом кадров: страницы режутся по ним, а сумма даёт прогресс.
    screens = list_screens()
    total_ready = sum(frames for _screen, frames in screens)

    if not total_ready:
        return {
            "status": "empty",
            "frames": 0,
            "groups": 0,
            "filled": 0,
            "replaced": 0,
            "photos_changed": 0,
            "disputed_groups": 0,
        }

    if progress is not None:
        progress(0, total_ready)

    frames_done = groups_done = 0
    filled = replaced = disputed_groups = 0
    photos_changed = 0
    disputed_samples: list[list[str]] = []

    for batch in _screen_batches(screens, limit):
        page = load_frames(limit, screens=batch)

        if not page:
            continue

        changes, page_filled, page_replaced, page_disputed, page_groups = _propose_for_frames(
            page,
            fields,
            disputed_samples,
        )

        filled += page_filled
        replaced += page_replaced
        disputed_groups += page_disputed

        if dry_run:
            # Пробный прогон: считаем, но ничего не пишем.
            photos_changed += len(changes)
        else:
            for photo_id, values in changes.items():
                if qwen_db.apply_refined_values(photo_id, values, reason="refine"):
                    photos_changed += 1

        frames_done += len(page)
        groups_done += page_groups

        if progress is not None:
            progress(frames_done, total_ready)

    return {
        "status": "dry_run" if dry_run else "done",
        "frames": frames_done,
        "groups": groups_done,
        "filled": filled,
        "replaced": replaced,
        "photos_changed": photos_changed,
        "disputed_groups": disputed_groups,
        "disputed_samples": disputed_samples,
    }


def _propose_for_frames(
    frames: list[Frame],
    fields: tuple[str, ...],
    disputed_samples: list[list[str]],
) -> tuple[dict[str, dict[str, str]], int, int, int, int]:
    """
    Предложения по одной странице кадров.

    Возвращает изменения по фото и счётчики: дополнено, заменено, спорных
    серий, всего серий. Спорные серии не меняем, но показываем первые десять.
    """

    groups = build_groups(
        frames,
        gap_seconds=refine_config.gap_seconds(),
        max_distance=DEFAULT_MAX_DISTANCE,
    )

    # Собираем изменения по фото: одно фото может получить и клиента, и бренд.
    changes: dict[str, dict[str, str]] = defaultdict(dict)
    filled = replaced = disputed_groups = 0

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

    return changes, filled, replaced, disputed_groups, len(groups)

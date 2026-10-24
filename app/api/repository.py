"""
Read-only PostgreSQL access for the web API.

Reuses the INGEST connection env convention (INGEST_DB_*). Only SELECTs are
issued. photo_id is always passed as a query parameter, never interpolated.
"""

from __future__ import annotations

from datetime import datetime

from psycopg.types.json import Json

from app.api import fingerprints
from app.api.config import display_source_directory
from app.api.schemas import (
    DinoBatchSummary,
    DinoRunSummary,
    HybridRunSummary,
    PhotoSummary,
)
from app.hybrid import config as hybrid_config
from app.ingest.database import get_connection


# Значение фильтра «Требуют проверки» в панели адресов. Настоящие адреса — целые id,
# поэтому слово не может столкнуться с ними.
REVIEW_ADDRESS_ID = "review"
REVIEW_ADDRESS_VALUE = f"addr:{REVIEW_ADDRESS_ID}"
REVIEW_NAME = "Требуют проверки"


def _latest_hybrid_final_sql(photo_ref: str) -> str:
    """
    `hybrid_final_id` of the LATEST DONE HYBRID verdict (NULL if no match).

    Runs append rows, so an older successful verdict must not outlive a newer
    "no match" verdict. Callers use the same expression for the grid, the
    address panel and statistics.
    """

    return (
        "(SELECT h.hybrid_final_id FROM public.hybrid_results AS h "
        f"WHERE h.photo_id = {photo_ref}.photo_id AND h.status = 'DONE' "
        "ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC "
        "LIMIT 1)"
    )


def _latest_confidence_sql(photo_ref: str) -> str:
    """
    DINO-сходство выбранного кандидата (0…1) последнего вердикта HYBRID.

    Это `dino_candidates.score` первого ранга для того же DINO-прогона, что
    породил вердикт. Взвешенная сумма гибрида (`hybrid_score`, ~12) зависит от
    числа кандидатов и бонуса за согласие соседей, поэтому для порога не
    годится. NULL — вердикта нет либо у прогона нет кандидатов.
    """

    return (
        "(SELECT c.score FROM public.hybrid_results AS h "
        "JOIN public.dino_candidates AS c "
        "  ON c.run_id = h.dino_run_id AND c.rank = 1 "
        f"WHERE h.photo_id = {photo_ref}.photo_id AND h.status = 'DONE' "
        "ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC "
        "LIMIT 1)"
    )


def _latest_margin_sql(photo_ref: str) -> str:
    """
    Отрыв лучшего адреса от второго в последнем вердикте HYBRID.

    Уже хранится (`hybrid_results.hybrid_margin`, это разница между лучшим и
    вторым кандидатом DINO). Замер: медиана по корпусу 0.070, а у всех ручных
    исправлений — 0.005–0.014, то есть маленький отрыв и есть признак
    «уверенно, но мимо».
    """

    return (
        "(SELECT h.hybrid_margin FROM public.hybrid_results AS h "
        f"WHERE h.photo_id = {photo_ref}.photo_id AND h.status = 'DONE' "
        "ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC "
        "LIMIT 1)"
    )


def _runner_up_sql(photo_ref: str, column: str) -> str:
    """
    Лучший кандидат ДРУГОГО адреса в последнем вердикте: ближайшая альтернатива.

    Важно: сравнивать с выбранным слепком нельзя по рангу. Гибрид иногда
    выбирает не первый кандидат DINO (ранг 2 может оказаться выбранным), и
    тогда «второй по рангу» — это тот же адрес. Поэтому берём лучший кандидат,
    чей адрес отличается от адреса вердикта.
    """

    chosen = (
        "(SELECT afx.address_id FROM public.address_fingerprints AS afx "
        "WHERE afx.fingerprint_id = h.hybrid_final_id AND afx.active LIMIT 1)"
    )

    return (
        "(SELECT " + column + " FROM public.hybrid_results AS h "
        "JOIN public.dino_candidates AS c ON c.run_id = h.dino_run_id "
        "JOIN public.address_fingerprints AS af "
        "  ON af.fingerprint_id = c.fingerprint_id AND af.active "
        "JOIN public.fingerprints AS f "
        "  ON f.fingerprint_id = af.fingerprint_id AND f.active "
        "JOIN public.address_directory AS ad "
        "  ON ad.address_id = af.address_id AND ad.active "
        f"WHERE h.photo_id = {photo_ref}.photo_id AND h.status = 'DONE' "
        f"  AND af.address_id <> COALESCE({chosen}, -1) "
        "ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC, "
        "         c.score DESC "
        "LIMIT 1)"
    )


def _address_threshold_sql(
    confidence_sql: str,
    margin_sql: str,
    low_score: float | None = None,
    min_margin: float | None = None,
) -> str:
    """
    Условие «совпадению можно верить» для произвольных выражений сходства и отрыва.

    Порог берётся из настроек (`app/hybrid/config.py`); 0 отключает проверку и
    возвращает прежнее поведение. Явное значение нужно предпросмотру: оператор
    подбирает порог и хочет видеть размер корзины **до** сохранения.
    Сравнение подставляется числом: значение провалидировано (0…1), поэтому
    текст SQL от него не зависит.

    Выражения передаются снаружи, потому что те же условия нужны и для
    коррелированных подзапросов (`_address_sql`), и для колонок одного
    соединения LATERAL (`_verdict_source_sql`).

    Оба критерия независимы: можно включить только отрыв, только сходство или
    оба. NULL считается «не знаем» и фото не отбрасывает.
    """

    low = hybrid_config.low_score() if low_score is None else float(low_score)
    min_margin = hybrid_config.min_margin() if min_margin is None else float(min_margin)

    conditions: list[str] = []

    if low > 0:
        conditions.append(f"({confidence_sql} IS NULL OR {confidence_sql} >= {low})")

    if min_margin > 0:
        conditions.append(
            f"({margin_sql} IS NULL OR {margin_sql} >= {float(min_margin)})"
        )

    return " AND ".join(conditions) or "TRUE"


def _address_sql(
    photo_ref: str,
    low_score: float | None = None,
    min_margin: float | None = None,
) -> str:
    """Адрес с учётом порога уверенности: слабое совпадение адреса не даёт."""

    final = _latest_hybrid_final_sql(photo_ref)
    threshold = _address_threshold_sql(
        _latest_confidence_sql(photo_ref),
        _latest_margin_sql(photo_ref),
        low_score,
        min_margin,
    )

    if threshold == "TRUE":
        return final

    return f"(CASE WHEN {threshold} THEN {final} ELSE NULL END)"


def _dino_fallback_address_sql(photo_ref: str) -> str:
    """
    Запасной адрес для фото, у которых нет ни одного вердикта HYBRID.

    Пока вердикта нет, показывать нечего, кроме лучшего кандидата DINO: так
    фото видно в корзине «Требуют проверки» с предложенным адресом. Как только
    вердикт появился, запасной путь выключается — даже если порог уверенности
    его не пропустил.
    """

    return (
        "(CASE WHEN NOT EXISTS ("
        "     SELECT 1 FROM public.hybrid_results AS hx "
        f"     WHERE hx.photo_id = {photo_ref}.photo_id AND hx.status = 'DONE'"
        ") THEN ("
        "     SELECT r.dino_best_id FROM public.dino_runs AS r "
        f"     WHERE r.photo_id = {photo_ref}.photo_id AND r.status = 'DONE' "
        "       AND r.dino_best_id IS NOT NULL "
        "     ORDER BY r.finished_at DESC NULLS LAST, r.run_id DESC "
        "     LIMIT 1"
        ") END)"
    )


def _latest_verdict_lateral_sql(photo_ref: str = "p", alias: str = "v") -> str:
    """
    Последний вердикт HYBRID одним обращением: слепок, его сходство и отрыв.

    Раньше эти три величины брались тремя отдельными коррелированными
    подзапросами, и каждый заново проходил одну и ту же цепочку
    `hybrid_results` → `dino_candidates` (rank = 1). Для страницы фото это
    незаметно (LIMIT 50), но панель адресов и подвал считают по всему корпусу.

    Замер на 56 870 фото (рабочая база, ответ сверен до последнего счётчика):
    панель адресов 4.63 с → 1.29 с, подвал 3.45 с → 0.93 с.

    `LEFT JOIN LATERAL`: у фото без вердикта строка должна остаться, иначе оно
    пропадёт из счётчиков.
    """

    return (
        "LEFT JOIN LATERAL ("
        "    SELECT h.hybrid_final_id AS final_id, "
        "           h.hybrid_margin AS margin, "
        "           c.score AS confidence "
        "    FROM public.hybrid_results AS h "
        "    LEFT JOIN public.dino_candidates AS c "
        "           ON c.run_id = h.dino_run_id AND c.rank = 1 "
        f"    WHERE h.photo_id = {photo_ref}.photo_id AND h.status = 'DONE' "
        "    ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC "
        "    LIMIT 1"
        f") AS {alias} ON TRUE"
    )


# Карта «слепок → адрес» одним проходом по маленьким таблицам. Отдельная
# MATERIALIZED-выборка нужна потому, что иначе PostgreSQL пересканирует эти
# таблицы на каждое фото: в плане панели адресов было 36 542 последовательных
# сканирования по 140 строк.
#
# Несколько слепков на одном адресе — обычное дело, счётчик адреса их
# суммирует, и группировка этому не мешает (ключ — слепок). Она нужна против
# обратного: если один слепок окажется привязан к двум адресам, без неё фото
# попало бы в оба счётчика и сумма по адресам превысила бы число фото.
# Сейчас привязка 1:1 (38 активных слепков — 38 привязок), но в пору
# тестового этапа слепки и привязки меняются часто.
_ADDRESS_MAP_SQL = """
    SELECT af.fingerprint_id, min(af.address_id) AS address_id
    FROM public.address_fingerprints AS af
    JOIN public.fingerprints AS reg
      ON reg.fingerprint_id = af.fingerprint_id
     AND reg.active
    WHERE af.active
    GROUP BY af.fingerprint_id
"""


def _verdict_source_sql(
    *,
    photo_ref: str = "p",
    alias: str = "v",
    with_client: bool = False,
    low_score: float | None = None,
    min_margin: float | None = None,
) -> str:
    """
    Компактная выборка фото для счётчиков: адресный слепок, две даты, клиент.

    Панель адресов и подвал берут из полной `_PHOTO_SELECT` только адрес и даты,
    а она считает на каждое фото ещё подсказку, второй адрес и метаданные QWEN.
    Здесь остаётся ровно нужное, и адрес берётся из одного LATERAL-соединения.

    `addr_fp` — тот же адресный слепок, что у `_address_sql`: порог уверенности
    и отрыва применяется, запасной адрес по DINO — нет. Это важно: запасной
    адрес нужен только для показа в корзине «Требуют проверки» (`_PHOTO_BASE`),
    а распознанным фото делает `_recognized_sql` — без запасного пути. Иначе
    фото без вердикта HYBRID попало бы в счётчики адресов, тогда как грид с
    `recognized_only` его там не показывает.

    `with_client` добавляет клиента QWEN — он нужен только приоритету по
    клиентам (левая панель, режим «от клиента»).
    """

    threshold = _address_threshold_sql(
        f"{alias}.confidence",
        f"{alias}.margin",
        low_score,
        min_margin,
    )
    client_column = ", q.client AS client" if with_client else ""
    client_join = (
        "LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id"
        if with_client
        else ""
    )

    return (
        f"SELECT {photo_ref}.photo_id, {photo_ref}.created_at, {photo_ref}.taken_at"
        + client_column
        + f", (CASE WHEN {threshold} THEN {alias}.final_id END) AS addr_fp "
        + f"FROM public.photos AS {photo_ref} "
        + _latest_verdict_lateral_sql(photo_ref, alias)
        + " "
        + client_join
        + " "
        + "WHERE " + _PREVIEW_READY_SQL
    )


def _recognized_sql(
    photo_ref: str = "t",
    low_score: float | None = None,
    min_margin: float | None = None,
) -> str:
    """
    The single definition of "распознано" used by every read path.

    A photo is recognised when the latest HYBRID verdict has a final id **and
    its confidence is not below the review threshold**, or when an operator set
    a manual address override. Older verdicts cannot keep a photo in the grid
    after a failed re-run. Everything else — a weak match, no match, or no
    verdict at all — lands in «Требуют проверки» (see list_addresses).
    """

    return (
        f"({_address_sql(photo_ref, low_score, min_margin)} IS NOT NULL OR EXISTS ("
        "SELECT 1 FROM public.photo_address_overrides AS ov "
        f"WHERE ov.photo_id = {photo_ref}.photo_id))"
    )


# Address comes from the recognition pipeline: the latest HYBRID verdict. The
# DINO fallback is used only when the photo has no DONE HYBRID row at all.
# `client` comes from the parallel QWEN metadata.
#
# Замечание: сейчас все вызывающие передают recognized_only=True, поэтому
# фото без вердикта HYBRID до этой выборки не доходят и запасной путь по
# DINO не срабатывает. Он понадобится корзине «Требуют проверки», где такие фото
# как раз и показываются (см. docs/hybrid.txt).
# Фото видно в гриде и в счётчиках адресов только после того, как для него
# готово превью. Так «Обновление базы» наполняет галерею по мере создания
# превью, а не сразу после инспектора: до превью плитка была бы пустой
# заглушкой, а счётчики «Требуют проверки» росли бы на фото, которое ещё
# нельзя посмотреть. Битый исходник превью не получает и в выдаче не
# появляется — он виден в отчёте о превью.
_PREVIEW_READY_SQL = """
    EXISTS (
        SELECT 1 FROM public.photo_previews AS v
        WHERE v.photo_id = p.photo_id
    )
"""

_PHOTO_BASE = """
    SELECT
        p.photo_id        AS photo_id,
        p.filename        AS filename,
        p.width           AS width,
        p.height          AS height,
        p.container_format AS container_format,
        COALESCE(
            """ + _address_sql("p") + """,
            """ + _dino_fallback_address_sql("p") + """
        ) AS address,
        -- Что предложил бы DINO/HYBRID без порога: показывается в карточке
        -- фото из «Требуют проверки», чтобы человек видел автоматический
        -- вариант и мог его принять или отвергнуть.
        """ + _latest_hybrid_final_sql("p") + """ AS suggested_fingerprint,
        q.client AS client,
        q.brand AS brand,
        q.category AS category,
        q.status AS qwen_status,
        (q.description IS NOT NULL AND btrim(q.description) <> '')
            AS qwen_described,
        p.created_at AS created_at,
        p.taken_at AS taken_at,
        p.size_bytes AS size_bytes,
        p.source_path AS source_path,
        """ + _latest_confidence_sql("p") + """ AS confidence,
        """ + _latest_margin_sql("p") + """ AS margin,
        """ + _runner_up_sql("p", "COALESCE(ad.simple_address, ad.legal_address)") + """ AS runner_up_address,
        """ + _runner_up_sql("p", "c.score") + """ AS runner_up_score
    FROM public.photos AS p
    LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
    WHERE """ + _PREVIEW_READY_SQL + """
"""

# The recognised id (t.address) is resolved to the directory names in an outer
# query: the id is computed above, so it cannot be joined inside the same
# SELECT. Photos without a mapping read back with NULL names.
_PHOTO_DERIVED = """
    SELECT
        t.*,
        COALESCE(od.legal_address, d.legal_address) AS legal_address,
        COALESCE(od.simple_address, d.simple_address) AS simple_address,
        COALESCE(sd.simple_address, sd.legal_address) AS suggested_address
    FROM (""" + _PHOTO_BASE + """) AS t
    LEFT JOIN public.address_fingerprints AS f
           ON f.fingerprint_id = t.address
          AND f.active
    -- Архивный слепок не участвует и в отображении: имя адреса не подставляем.
    LEFT JOIN public.fingerprints AS reg
           ON reg.fingerprint_id = f.fingerprint_id
          AND reg.active
    LEFT JOIN public.address_directory AS d
           ON reg.fingerprint_id IS NOT NULL
          AND d.address_id = f.address_id
          AND d.active
    LEFT JOIN public.photo_address_overrides AS ov
           ON ov.photo_id = t.photo_id
    LEFT JOIN public.address_directory AS od
           ON od.address_id = ov.address_id
          AND od.active
    -- Предложенный (но не принятый) адрес: тот же справочник, отдельный join.
    LEFT JOIN public.address_fingerprints AS sf
           ON sf.fingerprint_id = t.suggested_fingerprint
          AND sf.active
    LEFT JOIN public.fingerprints AS sreg
           ON sreg.fingerprint_id = sf.fingerprint_id
          AND sreg.active
    LEFT JOIN public.address_directory AS sd
           ON sd.address_id = sf.address_id
          AND sd.active
"""

_PHOTO_SELECT = (
    "SELECT photo_id, filename, width, height, container_format, "
    "address, client, brand, category, created_at, taken_at, size_bytes, source_path, "
    "legal_address, simple_address, qwen_status, qwen_described, confidence, "
    "suggested_fingerprint, suggested_address, margin, runner_up_address, runner_up_score "
    "FROM (" + _PHOTO_DERIVED + ") AS t"
)


def _photo_row(row) -> PhotoSummary:
    return PhotoSummary(
        photo_id=row[0],
        filename=row[1],
        width=row[2],
        height=row[3],
        container_format=row[4],
        address=row[5],
        client=row[6],
        brand=row[7],
        category=row[8],
        created_at=row[9],
        taken_at=row[10],
        size_bytes=row[11],
        source_directory=display_source_directory(row[12]) if row[12] else "",
        legal_address=row[13],
        simple_address=row[14],
        qwen_status=row[15],
        qwen_described=bool(row[16]) if row[16] is not None else None,
        confidence=float(row[17]) if row[17] is not None else None,
        suggested_fingerprint=row[18],
        suggested_address=row[19],
        margin=float(row[20]) if row[20] is not None else None,
        runner_up_address=row[21],
        runner_up_score=float(row[22]) if row[22] is not None else None,
    )


# Сортировка выдачи: ключи те же, что в меню грида.
#
# Раньше порядок задавал клиент, пересортировывая уже загруженные страницы:
# сервер отдавал их по photo_id, поэтому догруженная страница вставала в
# середину списка. Теперь ключ уходит на сервер, а страницы продолжаются
# курсором по тому же ключу.
_SORT_EXPRESSIONS = {
    "photo_id": "t.photo_id",
    "filename": "t.filename",
    "address": (
        "COALESCE(NULLIF(btrim(t.simple_address), ''), t.legal_address,"
        " t.address, '')"
    ),
    "client": "COALESCE(t.client, '')",
    "date": "COALESCE(t.taken_at, t.created_at)",
}

SORT_KEYS = tuple(_SORT_EXPRESSIONS)


def sort_expression(sort: str) -> str:
    """ORDER BY-выражение для ключа сортировки (с подстановкой по умолчанию)."""

    return _SORT_EXPRESSIONS.get(sort, _SORT_EXPRESSIONS["photo_id"])


def encode_cursor(value, photo_id: str) -> str:
    """
    Курсор страницы: значение ключа сортировки и photo_id.

    Только photo_id, как раньше, годится лишь для сортировки по нему: при
    сортировке по дате или адресу граница страницы проходит по значению ключа,
    и одного идентификатора для продолжения недостаточно.
    """

    import base64
    import json as _json

    if isinstance(value, datetime):
        value = value.isoformat(sep=" ", timespec="microseconds")

    payload = _json.dumps({"v": value, "id": photo_id}, ensure_ascii=False)
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str):
    """Обратная операция; при мусоре возвращает None (страница начнётся с начала)."""

    import base64
    import json as _json

    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = _json.loads(raw)
    except Exception:  # noqa: BLE001 - курсор приходит от клиента
        return None

    if not isinstance(data, dict) or "id" not in data:
        return None

    return data.get("v"), str(data["id"])


def _photo_where(
    *,
    cursor: str | None = None,
    sort: str = "photo_id",
    order: str = "asc",
    query: str | None = None,
    addresses: list[str] | None = None,
    clients: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    collection_id: int | None = None,
    ids: list[str] | None = None,
    brand: str | None = None,
    tag: str | None = None,
    category: str | None = None,
    recognized_only: bool = False,
    combine: str = "union",
) -> tuple[str, list[object]]:
    """
    WHERE-часть запроса фото и её параметры.

    Вынесена из `list_photos`, чтобы счётчик «За период N фото» использовал
    ровно те же условия, что и сам грид: иначе подпись и выдача расходятся.
    Курсор сюда передаётся только для постраничного продолжения; счётчик
    вызывает функцию с `cursor=None`.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    if combine not in {"union", "address", "client"}:
        raise ValueError("combine must be 'union', 'address' or 'client'")

    date_column = "t.taken_at" if date_mode == "capture" else "t.created_at"

    clauses: list[str] = []
    params: list[object] = []
    # Теги (адреса, клиенты, бренд, тег, категория) складываются по ИЛИ:
    # выбранный бренд не сужает выбранных клиентов, а добавляет их фото.
    # Свободный текст, даты и «только распознанные» остаются отдельными
    # условиями И.
    tag_clauses: list[str] = []

    if not ids and cursor:
        if sort == "photo_id":
            # По умолчанию страница продолжается по photo_id — как раньше.
            clauses.append(
                "t.photo_id > %s" if order == "asc" else "t.photo_id < %s"
            )
            params.append(cursor)
        else:
            decoded = decode_cursor(cursor)

            if decoded is not None:
                value, last_id = decoded
                expression = sort_expression(sort)
                comparator = ">" if order == "asc" else "<"
                # Ключ сортировки не уникален: границу задаёт пара
                # (значение ключа, photo_id), иначе строки на границе
                # страниц повторялись бы или терялись.
                cast = "%s::timestamp" if sort == "date" else "%s::text"
                clauses.append(
                    f"(({expression}), t.photo_id) {comparator}"
                    f" ({cast}, %s::text)"
                )
                params.extend([value, last_id])

    if query:
        like = f"%{query}%"
        # Split by relation so each predicate can use its trigram GIN index
        # (schema/014): a multi-relation OR spanning photos and photo_qwen
        # cannot be pushed into index scans, but a UNION of per-table lookups
        # can (BitmapOr on photo_qwen). `address` is a computed column and
        # stays as a plain ILIKE on the outer query. `tags` is a JSONB array
        # (schema/007); the CASE keeps jsonb_array_elements_text from raising
        # on a NULL or a non-array value that a manual edit could leave behind.
        #
        # Client and brand are also matched through the alias dictionary
        # (schema/035): typing the canonical name finds the raw spellings QWEN
        # invented (and vice versa is not needed - the raw value is stored).
        clauses.append(
            "(t.photo_id IN ("
            "  SELECT photo_id FROM public.photos WHERE filename ILIKE %s "
            "  UNION "
            "  SELECT photo_id FROM public.photo_qwen "
            "  WHERE (client ILIKE %s "
            "         OR client IN (SELECT alias FROM public.client_aliases "
            "                       WHERE kind = 'client' AND canonical ILIKE %s)"
            "         OR brand ILIKE %s "
            "         OR brand IN (SELECT alias FROM public.client_aliases "
            "                      WHERE kind = 'brand' AND canonical ILIKE %s)"
            "         OR category ILIKE %s OR description ILIKE %s "
            "         OR EXISTS (SELECT 1 FROM jsonb_array_elements_text("
            "              CASE WHEN jsonb_typeof(tags) = 'array' THEN tags END"
            "            ) AS tag WHERE tag ILIKE %s))"
            ") OR t.address ILIKE %s"
            " OR t.legal_address ILIKE %s OR t.simple_address ILIKE %s)"
        )
        params.extend([like] * 11)

    address_parts: list[str] = []
    address_params: list[object] = []

    if addresses:
        # The panel sends ``addr:<address_id>`` — a legal address may have
        # several active fingerprints. Legacy fingerprint ids stay supported
        # for old collections and saved searches. A manual override wins over
        # the recognised id; archived fingerprints never match.
        for value in addresses:
            text = str(value).strip()

            if text.lower().startswith("addr:"):
                suffix = text.split(":", 1)[1].strip()

                if suffix.lower() == REVIEW_ADDRESS_ID:
                    # «Требуют проверки»: всё, что не получило адреса — слабое
                    # совпадение, отсутствие совпадения или отсутствие
                    # вердикта. Ручное переопределение выводит фото отсюда.
                    address_parts.append(
                        "NOT " + _recognized_sql("t")
                    )
                    continue

                try:
                    address_id = int(suffix)
                except ValueError:
                    # Never silently drop a malformed value: with address
                    # priority it would turn into "no filter" and show ALL
                    # photos. A false predicate yields an empty page instead.
                    address_parts.append("FALSE")
                    continue

                address_parts.append(
                    "(EXISTS ("
                    "   SELECT 1 FROM public.photo_address_overrides AS ov"
                    "   JOIN public.address_directory AS od"
                    "     ON od.address_id = ov.address_id AND od.active"
                    "   WHERE ov.photo_id = t.photo_id"
                    "     AND ov.address_id = %s)"
                    " OR (NOT EXISTS ("
                    "   SELECT 1 FROM public.photo_address_overrides AS ov2"
                    "   JOIN public.address_directory AS od2"
                    "     ON od2.address_id = ov2.address_id AND od2.active"
                    "   WHERE ov2.photo_id = t.photo_id)"
                    "  AND EXISTS ("
                    "   SELECT 1 FROM public.address_fingerprints AS af"
                    "   JOIN public.fingerprints AS reg"
                    "     ON reg.fingerprint_id = af.fingerprint_id"
                    "    AND reg.active"
                    "   JOIN public.address_directory AS d"
                    "     ON d.address_id = af.address_id AND d.active"
                    "   WHERE af.address_id = %s AND af.active"
                    "     AND LOWER(af.fingerprint_id) = LOWER(t.address))))"
                )
                address_params.extend([address_id, address_id])
                continue

            address_parts.append(
                "(EXISTS ("
                "   SELECT 1 FROM public.photo_address_overrides AS ov"
                "   JOIN public.address_fingerprints AS af"
                "     ON af.address_id = ov.address_id AND af.active"
                "   JOIN public.fingerprints AS reg"
                "     ON reg.fingerprint_id = af.fingerprint_id AND reg.active"
                "   JOIN public.address_directory AS od"
                "     ON od.address_id = af.address_id AND od.active"
                "   WHERE ov.photo_id = t.photo_id"
                "     AND LOWER(af.fingerprint_id) = LOWER(%s))"
                " OR (NOT EXISTS ("
                "   SELECT 1 FROM public.photo_address_overrides AS ov2"
                "   JOIN public.address_directory AS od2"
                "     ON od2.address_id = ov2.address_id AND od2.active"
                "   WHERE ov2.photo_id = t.photo_id)"
                "  AND EXISTS ("
                "   SELECT 1 FROM public.address_fingerprints AS af2"
                "   JOIN public.fingerprints AS reg2"
                "     ON reg2.fingerprint_id = af2.fingerprint_id"
                "    AND reg2.active"
                "   JOIN public.address_directory AS d2"
                "     ON d2.address_id = af2.address_id AND d2.active"
                "   WHERE LOWER(af2.fingerprint_id) = LOWER(%s)"
                "     AND af2.active"
                "     AND LOWER(t.address) = LOWER(af2.fingerprint_id))))"
            )
            address_params.extend([text, text])

    client_parts: list[str] = []
    client_params: list[object] = []

    if clients:
        # Exact value (case-insensitive), not a substring: selecting «СТС»
        # must not also pull a client whose name merely contains «стс».
        # A raw spelling is folded through the alias dictionary to the chosen
        # canonical client. `kind = 'client'`: the dictionary also holds
        # brands, and a brand alias must not pull photos by their client.
        for value in clients:
            client_parts.append(
                "(LOWER(t.client) = LOWER(%s) OR EXISTS ("
                "SELECT 1 FROM public.client_aliases AS ca "
                "WHERE LOWER(ca.alias) = LOWER(t.client) "
                "  AND ca.kind = 'client' "
                "  AND LOWER(ca.canonical) = LOWER(%s)))"
            )
            client_params.extend([value, value])

    other_clauses: list[str] = []
    other_params: list[object] = []

    if brand:
        # Бренды нормализуются так же, как клиенты: выбор канонического
        # названия находит и сырые написания из словаря алиасов.
        other_clauses.append(
            "(LOWER(t.brand) = LOWER(%s) OR EXISTS ("
            "SELECT 1 FROM public.client_aliases AS ca "
            "WHERE LOWER(ca.alias) = LOWER(t.brand) "
            "  AND ca.kind = 'brand' "
            "  AND LOWER(ca.canonical) = LOWER(%s)))"
        )
        other_params.extend([brand, brand])

    if category:
        other_clauses.append("LOWER(t.category) = LOWER(%s)")
        other_params.append(category)

    if tag:
        other_clauses.append(
            "EXISTS ("
            "  SELECT 1 FROM public.photo_qwen AS qq"
            "  CROSS JOIN LATERAL jsonb_array_elements_text("
            "    CASE WHEN jsonb_typeof(qq.tags) = 'array' THEN qq.tags END"
            "  ) AS item"
            "  WHERE qq.photo_id = t.photo_id"
            "    AND LOWER(item) = LOWER(%s))"
        )
        other_params.append(tag)

    address_clause = (
        "(" + " OR ".join(address_parts) + ")" if address_parts else None
    )
    client_clause = (
        "(" + " OR ".join(client_parts) + ")" if client_parts else None
    )

    # union — все теги альтернативы; address/client — приоритетная сторона
    # задаёт вселенную, остальные теги объединяются внутри неё.
    if combine == "address" and address_clause:
        inner = ([client_clause] if client_clause else []) + other_clauses

        if inner:
            clauses.append(
                "(" + address_clause + " AND (" + " OR ".join(inner) + "))"
            )
            params.extend(address_params + client_params + other_params)
        else:
            clauses.append(address_clause)
            params.extend(address_params)
    elif combine == "client" and client_clause:
        inner = ([address_clause] if address_clause else []) + other_clauses

        if inner:
            clauses.append(
                "(" + client_clause + " AND (" + " OR ".join(inner) + "))"
            )
            params.extend(client_params + address_params + other_params)
        else:
            clauses.append(client_clause)
            params.extend(client_params)
    else:
        parts = (
            ([address_clause] if address_clause else [])
            + ([client_clause] if client_clause else [])
            + other_clauses
        )

        if parts:
            clauses.append("(" + " OR ".join(parts) + ")")
            params.extend(address_params + client_params + other_params)

    if date_from:
        clauses.append(f"{date_column} >= %s::date")
        params.append(date_from)

    if date_to:
        clauses.append(f"{date_column} < (%s::date + interval '1 day')")
        params.append(date_to)

    if collection_id is not None:
        clauses.append(
            "t.photo_id IN ("
            "SELECT member_value FROM public.collection_members "
            "WHERE collection_id = %s AND member_type = 'photo')"
        )
        params.append(collection_id)

    if ids:
        clauses.append("t.photo_id = ANY(%s)")
        params.append(list(ids))

    # Фильтр «Требуют проверки» выбирает ровно те фото, которые НЕ распознаны, поэтому
    # вместе с recognized_only он дал бы пустую страницу: «только распознанные»
    # и «только требующие уточнения» не пересекаются. Когда корзина выбрана,
    # показываем её содержимое (объединение с обычными адресами работает как
    # раньше — обе части уже ограничены обработанными фото).
    review_requested = bool(
        addresses
        and any(
            str(value).strip().lower().endswith(f":{REVIEW_ADDRESS_ID}")
            for value in addresses
        )
    )

    if recognized_only and not review_requested:
        # The grid shows a photo only after recognition has produced an
        # address: the LATEST HYBRID verdict has a final id, or a manual
        # override exists. A newer failed re-run hides the photo; an older
        # successful verdict does not keep it alive.
        # Videos live in a separate list and are not affected.
        clauses.append(_recognized_sql("t"))

    if not clauses:
        return "", params

    return " WHERE " + " AND ".join(clauses), params


def count_photos(
    *,
    query: str | None = None,
    addresses: list[str] | None = None,
    clients: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    collection_id: int | None = None,
    ids: list[str] | None = None,
    brand: str | None = None,
    tag: str | None = None,
    category: str | None = None,
    recognized_only: bool = False,
    combine: str = "union",
) -> int:
    """Сколько фото подходит под те же фильтры, что и грид."""

    where, params = _photo_where(
        query=query,
        addresses=addresses,
        clients=clients,
        date_from=date_from,
        date_to=date_to,
        date_mode=date_mode,
        collection_id=collection_id,
        ids=ids,
        brand=brand,
        tag=tag,
        category=category,
        recognized_only=recognized_only,
        combine=combine,
    )
    sql = "SELECT count(*) FROM (" + _PHOTO_SELECT + where + ") AS filtered"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return int(cur.fetchone()[0])


def list_photos(
    *,
    limit: int,
    cursor: str | None = None,
    sort: str = "photo_id",
    order: str = "asc",
    query: str | None = None,
    addresses: list[str] | None = None,
    clients: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    collection_id: int | None = None,
    ids: list[str] | None = None,
    brand: str | None = None,
    tag: str | None = None,
    category: str | None = None,
    recognized_only: bool = False,
    combine: str = "union",
) -> tuple[list[PhotoSummary], str | None]:
    """
    Return one page of registered photos ordered by photo_id.

    `addresses` are recognition results (HYBRID/DINO) and `clients` are the
    QWEN metadata; both accept several values with OR semantics (matching the
    legacy multi-select panels). `query` searches several fields at once
    (filename, client, brand, category, description, tags, address) and also
    resolves client/brand through the alias dictionary, so the canonical name
    finds the raw spellings QWEN produced. date_from/date_to filter by the upload date
    (photos.created_at) or, with date_mode="capture", by the EXIF capture
    date (photos.taken_at; photos without one are not matched). Fetches
    limit + 1 rows to detect a further page.

    `ids` switches the page to the caller's own order (a ranked search): the
    page is then taken by *rank offset*, and the cursor carries that offset as
    "rank:N". A photo_id cursor cannot continue a ranked list - it would both
    skip and repeat rows - so it is ignored in that mode.
    """

    if sort not in _SORT_EXPRESSIONS:
        raise ValueError(f"unsupported sort key: {sort}")

    if order not in {"asc", "desc"}:
        raise ValueError("order must be 'asc' or 'desc'")

    where, params = _photo_where(
        cursor=cursor,
        sort=sort,
        order=order,
        query=query,
        addresses=addresses,
        clients=clients,
        date_from=date_from,
        date_to=date_to,
        date_mode=date_mode,
        collection_id=collection_id,
        ids=ids,
        brand=brand,
        tag=tag,
        category=category,
        recognized_only=recognized_only,
        combine=combine,
    )
    sql = _PHOTO_SELECT + where

    order_param: list[str] | None = None
    offset = 0

    if ids:
        # Preserve the caller's order (e.g. a ranked search result) instead of
        # re-sorting by photo_id: the array position is the intended rank.
        order_param = list(ids)

        if cursor and cursor.startswith("rank:"):
            try:
                offset = max(0, int(cursor[len("rank:"):]))
            except ValueError:
                offset = 0

    if order_param is not None:
        sql += (
            " ORDER BY array_position(%s::text[], t.photo_id) "
            "LIMIT %s OFFSET %s"
        )
        params.extend([order_param, limit + 1, offset])
    elif sort == "photo_id":
        sql += " ORDER BY t.photo_id%s LIMIT %%s" % (
            " DESC" if order == "desc" else ""
        )
        params.append(limit + 1)
    else:
        # Порядок задаёт сервер: клиент больше не пересортировывает страницы.
        # Второй ключ (photo_id) делает порядок полным и устойчивым к
        # одинаковым значениям.
        direction = "DESC" if order == "desc" else "ASC"
        sql += (
            f" ORDER BY {sort_expression(sort)} {direction},"
            f" t.photo_id {direction} LIMIT %s"
        )
        params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [_photo_row(row) for row in rows]

    if order_param is not None:
        # Rank-based cursor: the offset of the next page inside the ranked list.
        next_cursor = (
            f"rank:{offset + len(items)}" if has_next and items else None
        )
    elif sort == "photo_id":
        next_cursor = items[-1].photo_id if has_next and items else None
    else:
        # Продолжение страницы — по значению ключа сортировки и photo_id.
        next_cursor = (
            encode_cursor(_sort_value(items[-1], sort), items[-1].photo_id)
            if has_next and items
            else None
        )

    return items, next_cursor


def _sort_value(item, sort: str):
    """Значение ключа сортировки у строки выдачи (для курсора страницы)."""

    if sort == "date":
        return item.taken_at or item.created_at

    if sort == "address":
        return item.simple_address or item.legal_address or item.address or ""

    return getattr(item, sort, "") or ""


def qwen_status_counts() -> dict:
    """photo_qwen row counts grouped by status."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, count(*) FROM public.photo_qwen GROUP BY status"
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}


def qwen_stats() -> dict:
    """
    One snapshot for the QWEN card: base size, statuses and last runs.

    `photo_qwen` only has a row per described photo, so its status counts are
    *not* the base size: a photo that was never queued has no row at all. The
    card needs both numbers, hence `photos` (registered photos) next to
    `counts`.

    `processed` counts photos that HAVE a description, not rows currently in
    status DONE: a re-run flips the row to RUNNING while the previous
    description stays in place (`mark_running` does not clear it), so counting
    DONE made the counter go backwards during a re-recognition pass.

    `runs` groups finished QWEN jobs by the trigger recorded in the payload
    ("manual" / "automation" / "pipeline"; older rows default to "manual"),
    so the window can show when each kind last ran.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM public.photos")
            photos = int(cur.fetchone()[0])

            cur.execute(
                "SELECT status, count(*) FROM public.photo_qwen GROUP BY status"
            )
            counts = {row[0]: int(row[1]) for row in cur.fetchall()}

            cur.execute(
                "SELECT count(*) FROM public.photo_qwen "
                "WHERE description IS NOT NULL AND btrim(description) <> ''"
            )
            described = int(cur.fetchone()[0])

            # Какая модель дала описания: при смене модели видно, что
            # перераспознано, а что ещё держит старый результат.
            cur.execute(
                "SELECT qwen_model, count(*) FROM public.photo_qwen "
                "WHERE qwen_model IS NOT NULL AND qwen_model <> '' "
                "GROUP BY 1 ORDER BY 2 DESC, 1"
            )
            models = [
                {"model": row[0], "photos": int(row[1])}
                for row in cur.fetchall()
            ]

            # Расход облака: локальная Ollama токенов не сообщает.
            cur.execute(
                "SELECT COALESCE(SUM(prompt_tokens), 0), "
                "       COALESCE(SUM(completion_tokens), 0), "
                "       COALESCE(SUM(total_tokens), 0) "
                "FROM public.photo_qwen"
            )
            tokens_row = cur.fetchone()
            tokens = {
                "prompt": int(tokens_row[0]),
                "completion": int(tokens_row[1]),
                "total": int(tokens_row[2]),
            }

            cur.execute("SELECT count(*) FROM public.photo_qwen_history")
            history_rows = int(cur.fetchone()[0])

            # Очередь распознавания: сколько заданий ждёт и сколько выполняется.
            # `counts` выше — это строки описаний, а не очередь: фото без
            # строки в photo_qwen там не видно, поэтому шапке нужен счётчик
            # именно заданий.
            cur.execute(
                """
                SELECT count(*) FILTER (WHERE status = 'PENDING'),
                       count(*) FILTER (WHERE status = 'RUNNING'),
                       count(*) FILTER (WHERE status = 'PAUSED')
                FROM public.job_queue
                WHERE job_type = 'QWEN_PHOTO'
                """
            )
            jobs_row = cur.fetchone()
            jobs = {
                "pending": int(jobs_row[0]),
                "running": int(jobs_row[1]),
                "paused": int(jobs_row[2]),
            }

            # Текущая выборка распознавания: «обработано / всего» для той
            # партии, которая идёт сейчас (обычно это дозаполнение за период).
            # Числа берём живыми из связей задания↔запуск, а не из сохранённых
            # счётчиков: они отстают, пока очередь ещё идёт.
            cur.execute(
                """
                SELECT run_id, title, status
                FROM public.run_history
                WHERE kind = 'qwen'
                ORDER BY (status IN ('RUNNING', 'PENDING')) DESC, run_id DESC
                LIMIT 1
                """
            )
            batch_row = cur.fetchone()
            batch = None

            if batch_row is not None:
                batch_run_id, batch_title, batch_status = batch_row
                cur.execute(
                    """
                    SELECT count(*) AS total,
                           count(*) FILTER (WHERE q.status = 'DONE') AS done,
                           count(*) FILTER (WHERE q.status = 'FAILED') AS failed
                    FROM public.run_history_jobs AS j
                    JOIN public.job_queue AS q ON q.id = j.job_id
                    WHERE j.run_id = %s
                    """,
                    (int(batch_run_id),),
                )
                total_row = cur.fetchone()
                batch = {
                    "run_id": int(batch_run_id),
                    "title": batch_title,
                    "status": batch_status,
                    "total": int(total_row[0]),
                    "done": int(total_row[1]),
                    "failed": int(total_row[2]),
                }

            cur.execute(
                """
                SELECT COALESCE(payload ->> 'source', 'manual') AS source,
                       count(*) AS jobs,
                       max(finished_at) AS last_finished_at,
                       count(*) FILTER (WHERE status = 'FAILED') AS failed
                FROM public.job_queue
                WHERE job_type = 'QWEN_PHOTO'
                GROUP BY 1
                ORDER BY 1
                """
            )
            runs = [
                {
                    "source": row[0],
                    "jobs": int(row[1]),
                    "last_finished_at": row[2],
                    "failed": int(row[3]),
                }
                for row in cur.fetchall()
            ]

    return {
        "photos": photos,
        "counts": counts,
        "processed": described,
        "remaining": max(0, photos - described),
        "queued": counts.get("PENDING", 0) + counts.get("RUNNING", 0),
        "jobs": jobs,
        "batch": batch,
        "models": models,
        "tokens": tokens,
        "history_rows": history_rows,
        "runs": runs,
    }


def photo_ids_with_qwen_status(status: str) -> list[str]:
    """photo_ids whose QWEN row has the given status (ordered)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id FROM public.photo_qwen "
                "WHERE status = %s ORDER BY photo_id",
                (status,),
            )
            return [row[0] for row in cur.fetchall()]


def get_photo(photo_id: str) -> PhotoSummary | None:
    """Return one registered photo, or None when it does not exist."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _PHOTO_SELECT + " WHERE t.photo_id = %s",
                (photo_id,),
            )
            row = cur.fetchone()

    return _photo_row(row) if row is not None else None


def all_photo_ids() -> list[str]:
    """Return every registered photo_id, ordered."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT photo_id FROM public.photos ORDER BY photo_id")
            return [row[0] for row in cur.fetchall()]


def review_count(
    low_score: float | None = None,
    min_margin: float | None = None,
) -> int:
    """
    Сколько фото попадёт в «Требуют проверки» при заданном пороге.

    Ничего не меняет: используется предпросмотром в настройках, чтобы подобрать
    значение по своему корпусу, не сохраняя его вслепую.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT count(*) FROM public.photos AS p "
                f"WHERE NOT {_recognized_sql('p', low_score, min_margin)} "
                f"AND {_PREVIEW_READY_SQL}"
            )
            row = cur.fetchone()

    return int(row[0]) if row else 0


def list_addresses(
    *,
    limit: int = 1000,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    clients: list[str] | None = None,
) -> list[dict]:
    """
    The address filter of the photo page: one entry per legal address.

    The list is built from ``address_directory``, not from fingerprints: one
    row per legal address, shown under its short (simple) name. Several active
    fingerprints may belong to one address; their photos are summed. An
    address without an active fingerprint stays in the panel with count 0
    until a fingerprint is linked and photos are recognised. Archived
    fingerprints take part in neither recognition nor the panel.

    ``address`` is the value the filter sends (``addr:<address_id>``); legacy
    fingerprint ids are still accepted for old collections and saved searches.
    ``fingerprints`` lists the active ids behind the address.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    # Два запроса ниже используют разные алиасы: список адресов — `eff AS e`,
    # счётчик «Требуют проверки» — CTE `t`. Один общий период с `e.` в обоих
    # давал UndefinedTable во втором запросе.
    date_column = "e.taken_at" if date_mode == "capture" else "e.created_at"
    date_column_t = "t.taken_at" if date_mode == "capture" else "t.created_at"
    period_parts: list[str] = []
    period_parts_t: list[str] = []
    period_params: list[object] = []

    if date_from:
        period_parts.append(f"{date_column} >= %s::date")
        period_parts_t.append(f"{date_column_t} >= %s::date")
        period_params.append(date_from)

    if date_to:
        period_parts.append(f"{date_column} < (%s::date + interval '1 day')")
        period_parts_t.append(
            f"{date_column_t} < (%s::date + interval '1 day')"
        )
        period_params.append(date_to)

    period_sql = " AND ".join(period_parts) or "TRUE"
    period_sql_t = " AND ".join(period_parts_t) or "TRUE"

    # В режиме приоритета по клиентам адреса сужаются до тех, где эти
    # клиенты есть; счётчики считаются по тому же условию.
    client_sql = ""
    client_params: list[object] = []

    if clients:
        client_where, client_params = _photo_where(clients=clients)
        client_sql = client_where.removeprefix(" WHERE ")

    # Клиентский отбор написан для алиаса `t` (общий с гридом), а источник
    # счётчиков называется `t` в одном запросе и `s` в другом.
    client_filter_t = f"AND ({client_sql})" if client_sql else ""
    client_filter_s = (
        f"AND ({client_sql.replace('t.', 's.')})" if client_sql else ""
    )
    # Источник одинаков для обоих запросов: адресный слепок и две даты.
    # Клиент QWEN добавляется только когда он действительно отбирается.
    source_sql = _verdict_source_sql(with_client=bool(clients))

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Фото считаются по юридическому адресу из справочника: у адреса
            # может быть несколько активных слепков, а адрес без слепков
            # остаётся в списке с нулём. Архивные слепки не участвуют.
            cur.execute(
                """
                WITH src AS (""" + source_sql + """),
                amap AS MATERIALIZED (""" + _ADDRESS_MAP_SQL + """),
                eff AS (
                    SELECT s.photo_id, s.created_at, s.taken_at,
                           COALESCE(ov.address_id, m.address_id) AS address_id
                    FROM src AS s
                    LEFT JOIN public.photo_address_overrides AS ov
                           ON ov.photo_id = s.photo_id
                    LEFT JOIN amap AS m ON m.fingerprint_id = s.addr_fp
                    WHERE (s.addr_fp IS NOT NULL OR ov.address_id IS NOT NULL)
                    """ + client_filter_s + """
                )
                SELECT d.address_id, d.simple_address, d.legal_address,
                       count(e.photo_id) AS count,
                       count(e.photo_id) FILTER (WHERE """ + period_sql + """) AS period_count
                FROM public.address_directory AS d
                LEFT JOIN eff AS e ON e.address_id = d.address_id
                WHERE d.active
                GROUP BY d.address_id, d.simple_address, d.legal_address
                """ + ("HAVING count(e.photo_id) > 0 " if clients else "") + """
                ORDER BY lower(COALESCE(NULLIF(btrim(d.simple_address), ''),
                                        d.legal_address)),
                         d.address_id
                LIMIT %s
                """,
                client_params + period_params + [limit],
            )
            rows = cur.fetchall()

            # «Требуют проверки»: фото, которые не разошлись по адресам. Считаются тем
            # же условием распознавания и тем же периодом, что и адреса выше.
            cur.execute(
                """
                WITH src AS (""" + source_sql + """)
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE """ + period_sql_t + """) AS period_total
                FROM src AS t
                LEFT JOIN public.photo_address_overrides AS ov
                       ON ov.photo_id = t.photo_id
                WHERE NOT (t.addr_fp IS NOT NULL OR ov.address_id IS NOT NULL)
                  """ + client_filter_t + """
                """,
                period_params + client_params,
            )
            review_total, review_period = cur.fetchone()

            cur.execute(
                """
                SELECT af.address_id, af.fingerprint_id
                FROM public.address_fingerprints AS af
                JOIN public.fingerprints AS reg
                  ON reg.fingerprint_id = af.fingerprint_id
                 AND reg.active
                WHERE af.active
                ORDER BY af.address_id, af.fingerprint_id
                """
            )
            mapped: dict[int, list[str]] = {}
            for address_id, fingerprint_id in cur.fetchall():
                mapped.setdefault(int(address_id), []).append(fingerprint_id)

    items: list[dict] = []

    if int(review_total or 0) > 0:
        items.append(
            {
                "address": REVIEW_ADDRESS_VALUE,
                "address_id": None,
                "name": REVIEW_NAME,
                "simple_address": REVIEW_NAME,
                "legal_address": "",
                "fingerprints": [],
                "count": int(review_total),
                "period_count": int(review_period or 0),
                "review": True,
            }
        )

    for address_id, simple_address, legal_address, count, period_count in rows:
        address_id = int(address_id)
        name = (simple_address or legal_address or f"Адрес {address_id}").strip()

        items.append(
            {
                "address": f"addr:{address_id}",
                "address_id": address_id,
                "name": name,
                "simple_address": simple_address,
                "legal_address": legal_address,
                "fingerprints": mapped.get(address_id, []),
                "count": int(count),
                "period_count": int(period_count),
                "review": False,
            }
        )

    return items


def stats(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
) -> dict:
    """
    Counts for the status bar at the bottom of the window.

    `photos`/`videos` and `last_*` are all-time. `period_photos`/`period_videos`
    repeat the counts with the caller's date range. `addresses` counts the
    addresses that actually received a HYBRID verdict (or a manual override),
    not every row of the address directory.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    date_column = "created_at" if date_mode == "upload" else "taken_at"
    period_parts: list[str] = []
    period_params: list[object] = []

    if date_from:
        period_parts.append(f"{date_column} >= %s::date")
        period_params.append(date_from)

    if date_to:
        period_parts.append(f"{date_column} < (%s::date + interval '1 day')")
        period_params.append(date_to)

    period_sql = " AND ".join(period_parts) or "TRUE"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    (SELECT count(*) FROM public.photos),
                    (SELECT count(*) FROM public.photos WHERE """ + period_sql + """),
                    (SELECT count(DISTINCT LOWER(COALESCE(a.canonical, q.client)))
                       FROM public.photo_qwen AS q
                       LEFT JOIN public.client_aliases AS a
                              ON LOWER(a.alias) = LOWER(q.client)
                             AND a.kind = 'client'
                      WHERE q.client IS NOT NULL AND q.client <> ''
                        AND """ + _recognized_sql("q") + """),
                    (SELECT max(created_at) FROM public.photos)
                """,
                period_params,
            )
            row = cur.fetchone()

            # Recognised addresses: a HYBRID final id or a manual override,
            # folded to the legal address exactly like the panel.
            #
            # Запрос намеренно НЕ использует _PHOTO_SELECT: для счётчика нужен
            # только адрес, а полная выборка считает ещё пять коррелированных
            # подзапросов на каждое фото (подсказка, уверенность, отрыв,
            # второй адрес). На 57 тысячах фото это выливалось в минуту работы
            # и держало соединение пула — интерфейс висел на загрузке.
            #
            # Адресный слепок берётся одним LATERAL-соединением: иначе сходство,
            # отрыв и адрес считались тремя подзапросами по одной и той же
            # цепочке (замер — в докстринге _latest_verdict_lateral_sql).
            cur.execute(
                """
                WITH src AS (""" + _verdict_source_sql() + """),
                amap AS MATERIALIZED (""" + _ADDRESS_MAP_SQL + """),
                mapped AS (
                    SELECT COALESCE(ov.address_id, m.address_id) AS address_id
                    FROM src AS s
                    LEFT JOIN public.photo_address_overrides AS ov
                           ON ov.photo_id = s.photo_id
                    LEFT JOIN amap AS m ON m.fingerprint_id = s.addr_fp
                    WHERE s.addr_fp IS NOT NULL OR ov.address_id IS NOT NULL
                )
                SELECT count(DISTINCT m.address_id)
                FROM mapped AS m
                JOIN public.address_directory AS d
                  ON d.address_id = m.address_id
                 AND d.active
                WHERE m.address_id IS NOT NULL
                """
            )
            addresses = int(cur.fetchone()[0])

            cur.execute("SELECT to_regclass('public.video_assets')")
            has_video_table = cur.fetchone()[0] is not None

            if has_video_table:
                # Video assets carry taken_at as well (ingest fills it); use
                # the same date mode as the video list and the photo grid.
                video_date_column = (
                    "taken_at" if date_mode == "capture" else "created_at"
                )
                video_parts: list[str] = []
                video_params: list[object] = []

                if date_from:
                    video_parts.append(
                        f"{video_date_column} >= %s::date"
                    )
                    video_params.append(date_from)

                if date_to:
                    video_parts.append(
                        f"{video_date_column} < (%s::date + interval '1 day')"
                    )
                    video_params.append(date_to)

                video_period_sql = " AND ".join(video_parts) or "TRUE"
                cur.execute(
                    "SELECT count(*), max(created_at), "
                    "count(*) FILTER (WHERE " + video_period_sql + ") "
                    "FROM public.video_assets",
                    video_params,
                )
                video_count, last_video_at, period_videos = cur.fetchone()
            else:
                video_count, last_video_at, period_videos = 0, None, 0

    return {
        "photos": int(row[0]),
        "videos": int(video_count),
        "period_photos": int(row[1]),
        "period_videos": int(period_videos),
        "addresses": addresses,
        "clients": int(row[2]),
        "last_photo_at": row[3],
        "last_video_at": last_video_at,
    }


def get_photo_address_override(photo_id: str) -> dict | None:
    """Manual legal-address override of one photo (None when not set)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.address_id, d.legal_address, d.simple_address,
                       o.updated_at
                FROM public.photo_address_overrides AS o
                JOIN public.address_directory AS d
                  ON d.address_id = o.address_id
                 AND d.active
                WHERE o.photo_id = %s
                """,
                (photo_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "address_id": int(row[0]),
        "legal_address": row[1],
        "simple_address": row[2],
        "updated_at": row[3],
    }


def set_photo_address_override(photo_id: str, address_id: int) -> dict | None:
    """Create or replace the manual address of one photo."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_address_overrides (photo_id, address_id)
                VALUES (%s, %s)
                ON CONFLICT (photo_id)
                DO UPDATE SET
                    address_id = EXCLUDED.address_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING address_id
                """,
                (photo_id, int(address_id)),
            )
            row = cur.fetchone()

    return get_photo_address_override(photo_id) if row is not None else None


def clear_photo_address_override(photo_id: str) -> bool:
    """Remove the manual override; recognition data stays untouched."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.photo_address_overrides
                WHERE photo_id = %s
                RETURNING photo_id
                """,
                (photo_id,),
            )
            return cur.fetchone() is not None


def suggest_terms(term: str, *, limit: int = 8) -> list[dict]:
    """
    Search-bar suggestions from existing QWEN values.

    Matches tags, clients, brands and categories by substring (ILIKE) or
    trigram similarity (pg_trgm), so a slightly misspelled word still finds a
    real tag. Prefix matches rank first, then similarity, then usage count.

    One value may be a client AND a brand (or a tag): each role is returned as
    its own suggestion, otherwise picking it would silently filter only one
    side. Case variants are one suggestion with summed usage.
    """

    like = f"%{term}%"
    prefix = f"{term}%"

    sql = """
        WITH values AS (
            SELECT 'tag' AS kind, tag AS value
            FROM public.photo_qwen AS q
            CROSS JOIN LATERAL jsonb_array_elements_text(
                CASE WHEN jsonb_typeof(q.tags) = 'array' THEN q.tags END
            ) AS tag
            WHERE tag <> ''
            UNION ALL
            SELECT 'client', client FROM public.photo_qwen
            WHERE client IS NOT NULL AND client <> ''
            UNION ALL
            SELECT 'brand', brand FROM public.photo_qwen
            WHERE brand IS NOT NULL AND brand <> ''
            UNION ALL
            SELECT 'category', category FROM public.photo_qwen
            WHERE category IS NOT NULL AND category <> ''
            UNION ALL
            SELECT 'address', simple_address FROM public.address_directory
            WHERE active AND simple_address <> ''
            UNION ALL
            SELECT 'address', legal_address FROM public.address_directory
            WHERE active AND legal_address <> ''
        ),
        grouped AS (
            SELECT lower(value) AS norm,
                   mode() WITHIN GROUP (ORDER BY value) AS value,
                   kind,
                   count(*) AS uses
            FROM values
            WHERE value ILIKE %s OR value %% %s
            GROUP BY lower(value), kind
        )
        SELECT value, kind, uses
        FROM grouped
        ORDER BY (norm LIKE lower(%s)) DESC,
                 similarity(norm, lower(%s)) DESC,
                 uses DESC,
                 norm
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (like, term, prefix, term, limit))
            return [
                {"value": row[0], "kind": row[1], "uses": int(row[2])}
                for row in cur.fetchall()
            ]


def list_clients(
    *,
    limit: int = 100,
    addresses: list[str] | None = None,
    recognized_only: bool = True,
) -> list[dict]:
    """
    Distinct QWEN clients with photo counts.

    Aliased raw values are folded into their canonical client (client_aliases).
    With ``addresses`` the list is narrowed to clients present on those
    addresses (client-priority mode) and counts follow the same predicate as
    the grid.
    """

    where_sql, where_params = _photo_where(
        addresses=addresses,
        recognized_only=recognized_only,
    )
    extra = where_sql.removeprefix(" WHERE ")

    if extra:
        extra = " AND (" + extra + ")"

    # Case variants are one client: the filter is case-insensitive anyway,
    # so two rows would show half-counts for the same selection.
    sql = (
        "SELECT mode() WITHIN GROUP (ORDER BY COALESCE(a.canonical, t.client)) "
        "       AS client, count(*) AS count "
        "FROM (" + _PHOTO_SELECT + ") AS t "
        "LEFT JOIN public.client_aliases AS a "
        "       ON LOWER(a.alias) = LOWER(t.client) AND a.kind = 'client' "
        "WHERE t.client IS NOT NULL AND t.client <> ''" + extra + " "
        "GROUP BY lower(COALESCE(a.canonical, t.client)) "
        "ORDER BY lower(COALESCE(a.canonical, t.client)) LIMIT %s"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, where_params + [limit])
            return [
                {"client": row[0], "count": int(row[1])}
                for row in cur.fetchall()
            ]


# ---------------------------------------------------------------------------
# Client aliases (QWEN client name normalization)
# ---------------------------------------------------------------------------


def list_client_aliases(kind: str = "client") -> list[dict]:
    """
    One alias dictionary. `kind` is 'client' or 'brand' (schema/035).

    Brands are normalised exactly like clients: QWEN invents strings for both.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT alias, canonical, kind FROM public.client_aliases "
                "WHERE kind = %s ORDER BY lower(alias)",
                (kind,),
            )
            return [
                {"alias": row[0], "canonical": row[1], "kind": row[2]}
                for row in cur.fetchall()
            ]


def upsert_client_alias(
    alias: str,
    canonical: str,
    *,
    kind: str = "client",
    actor: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Case-insensitive lookup: "Сбер" and "сбер" are the same alias,
            # and the facet join is case-insensitive too. Prefer an exact
            # spelling when it already exists.
            cur.execute(
                "SELECT alias, canonical FROM public.client_aliases "
                "WHERE kind = %s AND LOWER(alias) = LOWER(%s) "
                "ORDER BY (alias = %s) DESC, alias LIMIT 1",
                (kind, alias, alias),
            )
            row = cur.fetchone()

            if row is not None:
                existing_alias, old = row
                cur.execute(
                    "UPDATE public.client_aliases SET canonical = %s "
                    "WHERE kind = %s AND alias = %s",
                    (canonical, kind, existing_alias),
                )
            else:
                old = None
                cur.execute(
                    """
                    INSERT INTO public.client_aliases (alias, canonical, kind)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (kind, alias) DO UPDATE
                        SET canonical = EXCLUDED.canonical
                    """,
                    (alias, canonical, kind),
                )

            _record_alias_audit(
                cur,
                actor=actor,
                alias=alias,
                kind=kind,
                canonical_old=old,
                canonical_new=canonical,
                action="update" if old is not None else "create",
            )

    return {"alias": alias, "canonical": canonical, "kind": kind}


def delete_client_alias(
    alias: str,
    *,
    kind: str = "client",
    actor: str | None = None,
) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT canonical FROM public.client_aliases "
                "WHERE kind = %s AND alias = %s",
                (kind, alias),
            )
            row = cur.fetchone()

            if row is None:
                return False

            cur.execute(
                "DELETE FROM public.client_aliases WHERE kind = %s AND alias = %s",
                (kind, alias),
            )
            deleted = cur.rowcount == 1

            if deleted:
                _record_alias_audit(
                    cur,
                    actor=actor,
                    alias=alias,
                    kind=kind,
                    canonical_old=row[0],
                    canonical_new=None,
                    action="delete",
                )

            return deleted


def _record_alias_audit(
    cur, *, actor, alias, kind, canonical_old, canonical_new, action
) -> None:
    cur.execute(
        """
        INSERT INTO public.client_alias_audit
            (actor, alias, kind, canonical_old, canonical_new, action)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (actor, alias, kind, canonical_old, canonical_new, action),
    )


def list_client_alias_audit(
    *, limit: int = 100, kind: str | None = None
) -> list[dict]:
    limit = max(1, min(int(limit), 500))

    sql = (
        "SELECT audit_id, actor, alias, canonical_old, canonical_new, "
        "action, created_at, COALESCE(kind, 'client') "
        "FROM public.client_alias_audit"
    )
    params: list[object] = []

    if kind is not None:
        # Старые записи не имеют kind и относятся к клиентам.
        sql += " WHERE COALESCE(kind, 'client') = %s"
        params.append(kind)

    sql += " ORDER BY audit_id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [
        {
            "audit_id": int(row[0]),
            "actor": row[1],
            "alias": row[2],
            "canonical_old": row[3],
            "canonical_new": row[4],
            "action": row[5],
            "created_at": row[6],
            "kind": row[7],
        }
        for row in rows
    ]


def list_qwen_client_names() -> list[dict]:
    """Distinct client/brand strings QWEN produced, alphabetical, with counts."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kind, name, count(*) AS n
                FROM (
                    SELECT 'client' AS kind, client AS name
                    FROM public.photo_qwen WHERE client IS NOT NULL AND client <> ''
                    UNION ALL
                    SELECT 'brand' AS kind, brand AS name
                    FROM public.photo_qwen WHERE brand IS NOT NULL AND brand <> ''
                ) AS t
                GROUP BY kind, name
                ORDER BY lower(name), kind
                """
            )
            return [
                {"kind": row[0], "name": row[1], "count": int(row[2])}
                for row in cur.fetchall()
            ]


# ---------------------------------------------------------------------------
# Collections / bookmarks
# ---------------------------------------------------------------------------


# One scope owns exactly one member type; the API rejects a mismatch instead
# of letting a "photos" collection contain clients (its count would then
# disagree with the grid).
COLLECTION_MEMBER_TYPES = {
    "addresses": "address",
    "clients": "client",
    "photos": "photo",
}


def member_type_for_scope(scope: str | None) -> str | None:
    return COLLECTION_MEMBER_TYPES.get(str(scope)) if scope else None


def _collection_row(row) -> dict:
    return {
        "collection_id": int(row[0]),
        "name": row[1],
        "kind": row[2],
        "client": row[3],
        "scope": row[4],
        "created_at": row[5],
        "members": int(row[6]),
    }


def list_collections(user_id: str | None = None) -> list[dict]:
    sql = """
        SELECT
            c.collection_id,
            c.name,
            c.kind,
            c.client,
            c.scope,
            c.created_at,
            (
                SELECT count(*)
                FROM public.collection_members AS m
                WHERE m.collection_id = c.collection_id
                  AND m.member_type = CASE c.scope
                        WHEN 'addresses' THEN 'address'
                        WHEN 'clients' THEN 'client'
                        ELSE 'photo'
                      END
            ) AS members
        FROM public.collections AS c
    """
    params: list[object] = []

    # A user identity scopes the list to its owner; None (service token / auth
    # disabled) keeps the system-wide view.
    if user_id is not None:
        sql += " WHERE c.user_id = %s"
        params.append(user_id)

    sql += " ORDER BY lower(c.name)"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_collection_row(row) for row in cur.fetchall()]


def get_collection(collection_id: int, user_id: str | None = None) -> dict | None:
    sql = """
        SELECT
            c.collection_id, c.name, c.kind, c.client, c.scope, c.created_at,
            (
                SELECT count(*)
                FROM public.collection_members AS m
                WHERE m.collection_id = c.collection_id
                  AND m.member_type = CASE c.scope
                        WHEN 'addresses' THEN 'address'
                        WHEN 'clients' THEN 'client'
                        ELSE 'photo'
                      END
            ) AS members
        FROM public.collections AS c
        WHERE c.collection_id = %s
    """
    params: list[object] = [collection_id]

    if user_id is not None:
        sql += " AND c.user_id = %s"
        params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()

    return _collection_row(row) if row is not None else None


def create_collection(
    *,
    name: str,
    kind: str = "Моя",
    client: str | None = None,
    scope: str = "photos",
    user_id: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.collections (name, kind, client, scope, user_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING collection_id
                """,
                (name, kind, client, scope, user_id),
            )
            collection_id = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT c.collection_id, c.name, c.kind, c.client, c.scope,
                       c.created_at, 0 AS members
                FROM public.collections AS c
                WHERE c.collection_id = %s
                """,
                (collection_id,),
            )
            return _collection_row(cur.fetchone())


def delete_collection(collection_id: int, user_id: str | None = None) -> bool:
    sql = "DELETE FROM public.collections WHERE collection_id = %s"
    params: list[object] = [collection_id]

    if user_id is not None:
        sql += " AND user_id = %s"
        params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount == 1


def collection_member_values(
    collection_id: int,
    member_type: str = "photo",
) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT member_value
                FROM public.collection_members
                WHERE collection_id = %s AND member_type = %s
                ORDER BY member_value
                """,
                (collection_id, member_type),
            )
            return [row[0] for row in cur.fetchall()]


COLLECTION_LIMITS = {"client": 100, "address": 1000, "photo": 5000}


def add_collection_members(
    collection_id: int,
    *,
    member_type: str,
    values: list[str],
) -> int:
    if not values:
        return 0

    limit = COLLECTION_LIMITS.get(member_type)

    if limit is None:
        raise ValueError(f"unknown member type: {member_type}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Не даём подборке вырасти за лимиты панелей: иначе применение
            # такой подборки упирается в 422 списковых параметров.
            cur.execute(
                "SELECT member_value FROM public.collection_members "
                "WHERE collection_id = %s AND member_type = %s",
                (collection_id, member_type),
            )
            existing = {row[0] for row in cur.fetchall()}
            fresh = {value for value in values if value not in existing}

            if len(existing) + len(fresh) > limit:
                raise ValueError(
                    f"collection limit is {limit} {member_type} values"
                )

            cur.executemany(
                """
                INSERT INTO public.collection_members (
                    collection_id, member_type, member_value
                )
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [(collection_id, member_type, value) for value in values],
            )
            inserted = cur.rowcount

            cur.execute(
                "UPDATE public.collections SET updated_at = CURRENT_TIMESTAMP "
                "WHERE collection_id = %s",
                (collection_id,),
            )

            return inserted


def remove_collection_members(
    collection_id: int,
    *,
    member_type: str,
    values: list[str],
) -> int:
    if not values:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.collection_members
                WHERE collection_id = %s
                  AND member_type = %s
                  AND member_value = ANY(%s)
                """,
                (collection_id, member_type, values),
            )
            return cur.rowcount


def photo_sources(photo_ids: list[str]) -> dict[str, dict]:
    """
    {photo_id: {source_path, filename}} for the registered ids.

    One query for a whole selection: the ZIP download needs many rows at once.
    Unknown ids are simply absent from the result.
    """

    ids = [item for item in photo_ids if item]

    if not ids:
        return {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id, source_path, filename "
                "FROM public.photos WHERE photo_id = ANY(%s)",
                (ids,),
            )
            rows = cur.fetchall()

    return {
        row[0]: {"source_path": row[1], "filename": row[2]}
        for row in rows
    }


def get_photo_source(photo_id: str) -> dict | None:
    """
    Return the registered source path/metadata for one photo.

    The path comes from the database registration; it is never taken from
    client input.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_path, filename, container_format "
                "FROM public.photos WHERE photo_id = %s",
                (photo_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "source_path": row[0],
        "filename": row[1],
        "container_format": row[2],
    }


# ---------------------------------------------------------------------------
# DINO batches / runs and HYBRID runs (read-only status views)
# ---------------------------------------------------------------------------


def _as_dino_batch(row) -> DinoBatchSummary:
    return DinoBatchSummary(
        batch_id=row[0],
        run_type=row[1],
        status=row[2],
        total_count=row[3],
        completed_count=row[4],
        failed_count=row[5],
        created_at=row[6],
        finished_at=row[7],
    )


def list_dino_batches(
    *,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[DinoBatchSummary], int | None]:
    """Return DINO batches ordered by batch_id (newest last)."""

    sql = (
        "SELECT batch_id, run_type, status, total_count, "
        "completed_count, failed_count, created_at, finished_at "
        "FROM public.dino_batches"
    )
    params: list[object] = []

    if cursor is not None:
        sql += " WHERE batch_id > %s"
        params.append(cursor)

    sql += " ORDER BY batch_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [_as_dino_batch(row) for row in rows]
    next_cursor = items[-1].batch_id if has_next and items else None

    return items, next_cursor


def get_dino_batch(batch_id: int) -> DinoBatchSummary | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT batch_id, run_type, status, total_count, "
                "completed_count, failed_count, created_at, finished_at "
                "FROM public.dino_batches WHERE batch_id = %s",
                (batch_id,),
            )
            row = cur.fetchone()

    return _as_dino_batch(row) if row is not None else None


def list_dino_runs(
    *,
    batch_id: int,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[DinoRunSummary], int | None]:
    """Return the runs of one DINO batch ordered by run_id."""

    sql = (
        "SELECT run_id, photo_id, run_type, status, dino_best_id, "
        "dino_score, dino_confidence, dino_status, dino_time_sec, "
        "error_message, finished_at "
        "FROM public.dino_runs WHERE batch_id = %s"
    )
    params: list[object] = [batch_id]

    if cursor is not None:
        sql += " AND run_id > %s"
        params.append(cursor)

    sql += " ORDER BY run_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        DinoRunSummary(
            run_id=row[0],
            photo_id=row[1],
            run_type=row[2],
            status=row[3],
            dino_best_id=row[4],
            dino_score=row[5],
            dino_confidence=row[6],
            dino_status=row[7],
            dino_time_sec=row[8],
            error_message=row[9],
            finished_at=row[10],
        )
        for row in rows
    ]

    next_cursor = items[-1].run_id if has_next and items else None

    return items, next_cursor


def list_hybrid_runs(
    *,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[HybridRunSummary], int | None]:
    """Return HYBRID runs ordered by hybrid_run_id."""

    sql = (
        "SELECT hybrid_run_id, dino_batch_id, status, total_count, "
        "completed_count, failed_count, created_at, finished_at "
        "FROM public.hybrid_runs"
    )
    params: list[object] = []

    if cursor is not None:
        sql += " WHERE hybrid_run_id > %s"
        params.append(cursor)

    sql += " ORDER BY hybrid_run_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        HybridRunSummary(
            hybrid_run_id=row[0],
            dino_batch_id=row[1],
            status=row[2],
            total_count=row[3],
            completed_count=row[4],
            failed_count=row[5],
            created_at=row[6],
            finished_at=row[7],
        )
        for row in rows
    ]

    next_cursor = items[-1].hybrid_run_id if has_next and items else None

    return items, next_cursor


# ---------------------------------------------------------------------------
# Saved searches (bookmarked GRID filters)
# ---------------------------------------------------------------------------


def _saved_search_row(row) -> dict:
    return {
        "search_id": int(row[0]),
        "name": row[1],
        "filters": row[2] or {},
        "created_at": row[3],
    }


def list_saved_searches(user_id: str | None = None) -> list[dict]:
    sql = """
        SELECT search_id, name, filters, created_at
        FROM public.saved_searches
    """
    params: list[object] = []

    if user_id is not None:
        sql += " WHERE user_id = %s"
        params.append(user_id)

    sql += " ORDER BY lower(name)"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_saved_search_row(row) for row in cur.fetchall()]


def create_saved_search(
    *,
    name: str,
    filters: dict,
    user_id: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.saved_searches (name, filters, user_id)
                VALUES (%s, %s, %s)
                RETURNING search_id, name, filters, created_at
                """,
                (name, Json(filters or {}), user_id),
            )
            return _saved_search_row(cur.fetchone())


def delete_saved_search(search_id: int, user_id: str | None = None) -> bool:
    sql = "DELETE FROM public.saved_searches WHERE search_id = %s"
    params: list[object] = [search_id]

    if user_id is not None:
        sql += " AND user_id = %s"
        params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount == 1


# ---------------------------------------------------------------------------
# Per-manager UI state
# ---------------------------------------------------------------------------


def get_manager_selection(user_id: str) -> dict | None:
    """Return the stored state blob for one user, or None when absent."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT state FROM public.manager_selections WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    return row[0] if row is not None else None


def save_manager_selection(user_id: str, state: dict) -> None:
    """Upsert the state blob for one user."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.manager_selections (user_id, state)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                    SET state = EXCLUDED.state,
                        updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, Json(state or {})),
            )

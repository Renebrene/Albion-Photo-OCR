"""
Natural-language search over the photo metadata.

The NL query is mapped to structured filters by the local QWEN model, then a
normal photo search runs. Inference happens in the worker (job_type
NL_SEARCH), never inside an HTTP request handler.

Only read-only queries are issued; nothing is written except the job result.
"""

from __future__ import annotations

import json
import re

from app.qwen.processor import chat_text

_OUTPUT_KEYS = ("q", "client", "brand", "category", "address")

# Result bounds: page size fetched per extracted term and the overall cap on
# unioned photo_ids. Exceeding either sets `truncated` in the result.
MAX_PER_TERM = 200
MAX_TOTAL = 500

PROMPT = (
    "Ты помощник поиска по базе фотографий вывесок. "
    "Преобразуй запрос пользователя в СТРОГО JSON без пояснений со ключами: "
    "q (свободный текст/ключевое слово или null), "
    "client (клиент с вывески или null), "
    "brand (бренд или null), "
    "category (категория объекта, например 'рекламный щит', или null), "
    "address (адрес/ориентир или null). "
    "Заполняй только те поля, которые явно следуют из запроса; остальные — null."
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(content) -> dict:
    if isinstance(content, dict):
        return content

    text = _THINK_RE.sub("", str(content)).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(text)

        if match is None:
            raise ValueError("QWEN NL response has no JSON object")

        return json.loads(match.group(0))


def build_filters(query: str) -> dict:
    """Ask the active QWEN provider to translate a NL query into filters."""

    content = chat_text(f"{PROMPT}\n\nЗапрос: {query}")

    data = _extract_json(content)

    if not isinstance(data, dict):
        raise ValueError("QWEN NL response is not a JSON object")

    filters: dict = {}

    for key in _OUTPUT_KEYS:
        value = data.get(key)

        if isinstance(value, str):
            value = value.strip()

        filters[key] = value or None

    return filters


def run(query: str, *, limit: int = MAX_PER_TERM) -> dict:
    """
    Translate *query* and run the corresponding photo search.

    Returns {"filters", "photo_ids", "count", "truncated"}. `truncated` is set
    when the result hit the per-term page size or the overall cap, so callers
    know the list is not exhaustive. Importing the repository here keeps this
    module light at worker startup.
    """

    from app.api import repository

    filters = build_filters(query)

    terms = [
        term
        for term in (
            filters.get("q"),
            filters.get("client"),
            filters.get("brand"),
            filters.get("category"),
            filters.get("address"),
        )
        if term
    ]

    # `filters["address"]` — человеческий адрес («Комарова 13»), а не id
    # слепка. Передавать его в `addresses` нельзя: точный фильтр по id давал
    # ноль результатов по всем терминам. Адрес и так участвует как term:
    # свободный `q` ищет его по legal/simple.
    seen: dict[str, None] = {}
    truncated = False

    for term in terms or [query]:
        items, next_cursor = repository.list_photos(
            limit=limit,
            query=term,
            # The grid shows only recognised photos; searching must use the
            # same universe or "found N" and the result grid disagree.
            recognized_only=True,
        )

        if next_cursor is not None:
            truncated = True

        for item in items:
            seen.setdefault(item.photo_id, None)

            if len(seen) >= MAX_TOTAL:
                truncated = True
                break

        if len(seen) >= MAX_TOTAL:
            break

    return {
        "filters": filters,
        "photo_ids": list(seen),
        "count": len(seen),
        "truncated": truncated,
    }

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

# Page size for cursor pagination while collecting every match.  MAX_TOTAL is
# only a runaway guard (the corpus is ~57k), not a product limit: the old
# 200/500 caps silently hid matches.
PAGE_SIZE = 1000
MAX_TOTAL = 100_000
# Backwards-compatible name used by callers/tests; this is a page size, not a
# result cap.
MAX_PER_TERM = PAGE_SIZE

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


def run(query: str, *, limit: int = PAGE_SIZE) -> dict:
    """
    Translate *query* and run the corresponding photo search.

    Returns {"filters", "photo_ids", "count", "truncated"}.  Every page of
    every extracted term is collected; `truncated` is set only when the
    runaway guard MAX_TOTAL is reached. Importing the repository here keeps
    this module light at worker startup.
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
        cursor = None

        while True:
            items, next_cursor = repository.list_photos(
                limit=limit,
                cursor=cursor,
                query=term,
                # The grid shows only recognised photos; searching must use
                # the same universe or "found N" and the result grid disagree.
                recognized_only=True,
            )

            for item in items:
                seen.setdefault(item.photo_id, None)

                if len(seen) >= MAX_TOTAL:
                    truncated = True
                    break

            if len(seen) >= MAX_TOTAL or next_cursor is None:
                break

            cursor = next_cursor

    return {
        "filters": filters,
        "photo_ids": list(seen),
        "count": len(seen),
        "truncated": truncated,
    }

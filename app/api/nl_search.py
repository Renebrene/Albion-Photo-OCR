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
import urllib.request

from app.qwen.config import OLLAMA_URL, QWEN_TIMEOUT
from app.qwen.processor import resolve_model

_OUTPUT_KEYS = ("q", "client", "brand", "category", "address")

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
    """Ask QWEN to translate a NL query into structured filters."""

    body = json.dumps(
        {
            "model": resolve_model(),
            "messages": [
                {"role": "user", "content": f"{PROMPT}\n\nЗапрос: {query}"}
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "keep_alive": 0,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=QWEN_TIMEOUT) as response:
        payload = json.loads(response.read())

    content = (payload.get("message") or {}).get("content")

    if not content:
        content = payload.get("response")

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


def run(query: str, *, limit: int = 100) -> dict:
    """
    Translate *query* and run the corresponding photo search.

    Returns {"filters": ..., "photo_ids": [...], "count": n}. Importing the
    repository here keeps this module light at worker startup.
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

    addresses = [filters["address"]] if filters.get("address") else None

    seen: dict[str, None] = {}

    for term in terms or [query]:
        items, _ = repository.list_photos(
            limit=limit,
            query=term,
            addresses=addresses,
        )

        for item in items:
            seen.setdefault(item.photo_id, None)

    return {
        "filters": filters,
        "photo_ids": list(seen),
        "count": len(seen),
    }

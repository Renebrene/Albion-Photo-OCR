"""
Короткий кэш дорогих ответов: панели, подвал, счётчик фото (аудит 28.10.2026).

Панель адресов, панель клиентов, подвал и счётчик размера выборки считаются по
всему корпусу (1-5 с на 56 934 фото), а зависят только от параметров фильтра —
периода, режима даты, группы верхней панели и активных подборок. Перебор кнопок
верхней панели и возврат к прежнему периоду запрашивали одно и то же заново,
каждый раз с полным проходом.

Кэш живёт в процессе API (одна машина, один процесс — отдельного хранилища не
нужно), ключ — имя и параметры запроса. Срок задаётся `SCENE_API_CACHE_TTL`
(секунды, по умолчанию 10; 0 отключает кэш целиком).

Честные границы: данные меняет пайплайн, поэтому кэш намеренно короткий —
счётчики могут отстать не больше чем на TTL. Всё, что показывает сами фото
(страница грида, превью, карточка), не кэшируется: там важна свежесть, а
запрос и так быстрый (LIMIT по индексу даты).
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Callable, TypeVar

T = TypeVar("T")

# Сколько записей держим: ключи — сочетания фильтров, их немного.
MAX_ENTRIES = 64

_lock = threading.Lock()
_entries: "OrderedDict[tuple, tuple[float, object]]" = OrderedDict()
_hits = 0
_misses = 0


def ttl_seconds() -> float:
    """Срок жизни записи; 0 отключает кэш."""

    raw = os.getenv("SCENE_API_CACHE_TTL", "10").strip()

    try:
        return max(0.0, float(raw))
    except ValueError:
        return 10.0


def cached(key: tuple, producer: Callable[[], T]) -> T:
    """
    Значение из кэша или результат `producer`, положенный в кэш.

    `key` обязан включать все параметры, от которых зависит результат: кэш не
    знает, что такое «тот же фильтр». Сбой внутри `producer` наружу не
    кэшируется — исключение уходит вызывающему, запись не создаётся.
    """

    global _hits, _misses

    ttl = ttl_seconds()

    if ttl <= 0:
        return producer()

    now = time.monotonic()

    with _lock:
        entry = _entries.get(key)

        if entry is not None and entry[0] > now:
            _entries.move_to_end(key)
            _hits += 1
            return entry[1]  # type: ignore[return-value]

        _misses += 1

    value = producer()

    with _lock:
        _entries[key] = (now + ttl, value)
        _entries.move_to_end(key)

        while len(_entries) > MAX_ENTRIES:
            _entries.popitem(last=False)

    return value


def clear() -> None:
    """Сбросить кэш (нужно тестам и ручной диагностике)."""

    with _lock:
        _entries.clear()


def stats() -> dict:
    """Сколько попаданий и промахов: для тестов и диагностики."""

    with _lock:
        return {"hits": _hits, "misses": _misses, "size": len(_entries)}

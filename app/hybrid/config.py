"""
Порог уверенности распознавания: корзина «Уточнить».

Фото, у которого последний вердикт HYBRID выбрал отпечаток со сходством ниже
порога, адреса не получает: оно попадает в «Уточнить» и разбирается руками
(переопределение адреса побеждает автоматику). Так слабые совпадения не
растворяются среди уверенных.

Уверенность — это `dino_candidates.score` первого ранга того DINO-прогона,
который породил вердикт (0…1). Взвешенная сумма `hybrid_score` (~12) для порога
не годится: она зависит от числа кандидатов и бонуса за согласие соседей.

Значение хранится в `app_settings` (`hybrid_low_score`) и правится в
«Техническом разделе» без перезапуска; `SCENE_HYBRID_LOW_SCORE` — умолчание.
0 отключает проверку: тогда адрес получает любое совпадение, как раньше.
"""

from __future__ import annotations

import os
import time

from app import settings_store

LOW_SCORE_KEY = "hybrid_low_score"

DEFAULT_LOW_SCORE = float(os.getenv("SCENE_HYBRID_LOW_SCORE", "0.85"))

MIN_LOW_SCORE = 0.0
MAX_LOW_SCORE = 1.0

# Порог спрашивают при построении SQL на каждый запрос грида, поэтому значение
# кэшируется на несколько секунд: правка в интерфейсе видна почти сразу, а
# база не опрашивается на каждый запрос.
_CACHE_SECONDS = 5.0
_cached: tuple[float, float] | None = None


def low_score() -> float:
    """Текущий порог уверенности (0 — проверка выключена)."""

    global _cached

    now = time.monotonic()

    if _cached is not None and now - _cached[1] < _CACHE_SECONDS:
        return _cached[0]

    value = DEFAULT_LOW_SCORE

    try:
        stored = settings_store.get(LOW_SCORE_KEY)

        if stored is not None:
            value = float(stored)
    except Exception:  # noqa: BLE001 - без базы остаётся умолчание
        value = DEFAULT_LOW_SCORE

    value = max(MIN_LOW_SCORE, min(MAX_LOW_SCORE, value))
    _cached = (value, now)

    return value


def set_low_score(value: object) -> float:
    """Сохранить порог; нечисловое или выходящее за 0…1 значение отклоняется."""

    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError("порог должен быть числом от 0 до 1") from exc

    if not MIN_LOW_SCORE <= parsed <= MAX_LOW_SCORE:
        raise ValueError("порог должен быть числом от 0 до 1")

    settings_store.set_value(LOW_SCORE_KEY, parsed)
    invalidate()

    return parsed


def invalidate() -> None:
    """Сбросить кэш (после записи настройки или в тестах)."""

    global _cached
    _cached = None


def resolve_settings() -> dict:
    """Текущее значение для интерфейса."""

    return {
        "low_score": low_score(),
        "default_low_score": DEFAULT_LOW_SCORE,
        "enabled": low_score() > 0,
    }

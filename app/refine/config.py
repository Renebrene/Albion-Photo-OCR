"""
Настройки этапа «Уточнение».

Этап выключен по умолчанию: он меняет клиента и бренд, которые уже записал
QWEN, поэтому включать его должен владелец осознанно. Запускается не кнопкой,
а автоматически после того, как QWEN закончил: раньше сравнивать нечего.

Кропы нужны этапу, поэтому они больше не удаляются сразу после описания.
Если этап не успел пройти за `refine_crop_retention_days`, кропы удаляются —
место на диске важнее (docs/series_merge.md).
"""

from __future__ import annotations

import os

from app import settings_store

ENABLED_KEY = "refine_enabled"
GAP_SECONDS_KEY = "refine_gap_seconds"
RETENTION_DAYS_KEY = "refine_crop_retention_days"

DEFAULT_ENABLED = os.getenv("SCENE_REFINE_ENABLED", "0") == "1"
DEFAULT_GAP_SECONDS = float(os.getenv("SCENE_REFINE_GAP_SECONDS", "30"))
DEFAULT_RETENTION_DAYS = int(os.getenv("SCENE_REFINE_CROP_RETENTION_DAYS", "7"))

MAX_GAP_SECONDS = 600.0
MAX_RETENTION_DAYS = 90


def _stored(key: str):
    try:
        return settings_store.get(key)
    except Exception:  # noqa: BLE001 - без базы остаются умолчания
        return None


def enabled() -> bool:
    """Включён ли этап (по умолчанию выключен)."""

    stored = _stored(ENABLED_KEY)

    return bool(stored) if stored is not None else DEFAULT_ENABLED


def gap_seconds() -> float:
    """Максимальный интервал между кадрами одной серии."""

    stored = _stored(GAP_SECONDS_KEY)

    try:
        value = float(stored) if stored is not None else DEFAULT_GAP_SECONDS
    except (TypeError, ValueError):
        value = DEFAULT_GAP_SECONDS

    return max(0.0, min(MAX_GAP_SECONDS, value))


def retention_days() -> int:
    """Сколько дней кропы ждут прогона, прежде чем их удалят."""

    stored = _stored(RETENTION_DAYS_KEY)

    try:
        value = int(stored) if stored is not None else DEFAULT_RETENTION_DAYS
    except (TypeError, ValueError):
        value = DEFAULT_RETENTION_DAYS

    return max(1, min(MAX_RETENTION_DAYS, value))


def qwen_has_results() -> bool:
    """Есть ли в базе хоть одно описание QWEN."""

    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT 1 FROM public.photo_qwen)")
                row = cur.fetchone()
        return bool(row and row[0])
    except Exception:  # noqa: BLE001 - без базы этап просто недоступен
        return False


def available() -> bool:
    """
    Есть ли что уточнять.

    Этап сравнивает описания QWEN между кадрами одной серии, поэтому без
    QWEN он бессмысленен: либо QWEN участвует в прогоне, либо в базе уже
    лежат его результаты (например, после дозаполнения за период).
    """

    try:
        from app.qwen import processor as qwen_processor

        if qwen_processor.in_pipeline():
            return True
    except Exception:  # noqa: BLE001 - настройка недоступна, смотрим данные
        pass

    return qwen_has_results()


def set_enabled(value: object) -> bool:
    parsed = bool(value)
    settings_store.set_value(ENABLED_KEY, parsed)

    return parsed


def set_gap_seconds(value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError("интервал должен быть числом секунд") from exc

    if not 0 <= parsed <= MAX_GAP_SECONDS:
        raise ValueError(f"интервал должен быть от 0 до {MAX_GAP_SECONDS:g} секунд")

    settings_store.set_value(GAP_SECONDS_KEY, parsed)

    return parsed


def set_retention_days(value: object) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError("срок хранения должен быть числом дней") from exc

    if not 1 <= parsed <= MAX_RETENTION_DAYS:
        raise ValueError(f"срок хранения должен быть от 1 до {MAX_RETENTION_DAYS} дней")

    settings_store.set_value(RETENTION_DAYS_KEY, parsed)

    return parsed


def resolve_settings() -> dict:
    return {
        "enabled": enabled(),
        # Можно ли включать этап сейчас (QWEN в прогоне или его результаты).
        "available": available(),
        "gap_seconds": gap_seconds(),
        "crop_retention_days": retention_days(),
        "default_gap_seconds": DEFAULT_GAP_SECONDS,
        "default_crop_retention_days": DEFAULT_RETENTION_DAYS,
    }

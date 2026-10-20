"""
Настройки файлохранилища Albion: значения из БД поверх env-умолчаний.

Токен — секрет. Он хранится в `app_settings`, никогда не возвращается в API
и показывается только маской (как ключ QWEN в `app/qwen/processor.py`).

Env-переменные остаются fallback'ом, чтобы существующая установка работала без
единой записи в БД:
  ALBION_BASE_URL, ALBION_API_KEY, ALBION_FOLDER_ID,
  ALBION_LINK_TTL_DAYS (по умолчанию 90), ALBION_UPLOAD_TIMEOUT.

Устаревшая `ALBION_UPLOAD_URL` ещё читается: берётся только её origin, потому
что новый контракт ждёт базовый URL хранилища, а не готовый upload-endpoint.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from app.settings_store import get as get_setting
from app.settings_store import set_value as set_setting

BASE_URL_KEY = "albion_base_url"
API_KEY_KEY = "albion_api_key"
FOLDER_ID_KEY = "albion_folder_id"
TTL_DAYS_KEY = "albion_ttl_days"

DEFAULT_TTL_DAYS = 90


def _stored(key: str) -> Any:
    # Env остаётся рабочим fallback'ом: если БД недоступна или миграция с
    # app_settings ещё не применена, клиент не должен падать на чтении
    # настроек. Отсутствие значений видно через configured=false.
    try:
        return get_setting(key, None)
    except Exception:  # noqa: BLE001 - optional settings, env is the fallback
        return None


def _env_base_url() -> str:
    value = (os.getenv("ALBION_BASE_URL") or "").strip()

    if value:
        return value.rstrip("/")

    # Backward compatibility for one release: the old variable pointed at a
    # full upload endpoint, which no longer exists. Keep only its origin.
    legacy = (os.getenv("ALBION_UPLOAD_URL") or "").strip()

    if not legacy:
        return ""

    parsed = urlparse(legacy)

    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    return ""


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

    return value if value > 0 else default


def _ttl_days(value: Any) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TTL_DAYS

    return max(1, min(days, 3650))


def _clean_base_url(value: str) -> str:
    value = str(value or "").strip().rstrip("/")

    parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url должен быть http(s)-адресом")

    if parsed.username or parsed.password:
        raise ValueError("base_url не должен содержать логин или пароль")

    return value


def resolve_settings() -> dict:
    """Действующая конфигурация: БД, затем env."""

    stored_ttl = _stored(TTL_DAYS_KEY)

    return {
        "base_url": str(_stored(BASE_URL_KEY) or _env_base_url()).strip().rstrip("/"),
        "api_key": str(
            _stored(API_KEY_KEY) or os.getenv("ALBION_API_KEY") or ""
        ).strip(),
        "folder_id": str(
            _stored(FOLDER_ID_KEY) or os.getenv("ALBION_FOLDER_ID") or ""
        ).strip(),
        "ttl_days": _ttl_days(
            stored_ttl
            if stored_ttl is not None
            else os.getenv("ALBION_LINK_TTL_DAYS", DEFAULT_TTL_DAYS)
        ),
        "timeout": _positive_float("ALBION_UPLOAD_TIMEOUT", 120.0),
    }


def is_configured() -> bool:
    current = resolve_settings()

    return bool(current["base_url"] and current["api_key"])


def mask_api_key(api_key: str) -> str | None:
    """Безопасная для показа часть токена (никогда не весь секрет)."""

    if not api_key:
        return None

    if len(api_key) <= 8:
        return "…" + api_key[-2:]

    return "…" + api_key[-4:]


def public_settings() -> dict:
    """Настройки для API: без токена, только маска."""

    current = resolve_settings()

    return {
        "base_url": current["base_url"],
        "folder_id": current["folder_id"],
        "ttl_days": current["ttl_days"],
        "configured": is_configured(),
        "api_key_set": bool(current["api_key"]),
        "api_key_hint": mask_api_key(current["api_key"]),
    }


def update_settings(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    folder_id: str | None = None,
    ttl_days: int | None = None,
) -> dict:
    """Сохранить переданные поля; None — не менять, "" — очистить."""

    if base_url is not None:
        cleaned = _clean_base_url(base_url) if str(base_url).strip() else ""
        set_setting(BASE_URL_KEY, cleaned)

    if api_key is not None:
        set_setting(API_KEY_KEY, str(api_key).strip())

    if folder_id is not None:
        set_setting(FOLDER_ID_KEY, str(folder_id).strip())

    if ttl_days is not None:
        set_setting(TTL_DAYS_KEY, _ttl_days(ttl_days))

    return public_settings()

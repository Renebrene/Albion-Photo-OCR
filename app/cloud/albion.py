"""
Клиент машинной интеграции с файлохранилищем Albion.

Контракт намеренно узкий: один файл за запрос, заголовок `X-API-Key`, ответ с
публичной ссылкой и сроком. Настройки (адрес, токен, папка, TTL) приходят из
`app/cloud/config.py`: значения из БД перекрывают env-умолчания. Токен никогда
не логируется и не возвращается клиентам.
"""

from __future__ import annotations

import mimetypes
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.cloud import config


class CloudConfigError(RuntimeError):
    """Albion upload is not configured."""


class CloudUploadError(RuntimeError):
    """A safe, user-facing upload failure (no credentials or local paths)."""


def settings() -> dict[str, Any]:
    """Действующие настройки (совместимость с прежним вызовом)."""

    return config.resolve_settings()


def is_configured() -> bool:
    return config.is_configured()


def _endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _safe_url(value: str) -> str:
    parsed = urlparse(value.strip())

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CloudUploadError("Albion вернул некорректную ссылку")

    if parsed.username or parsed.password:
        raise CloudUploadError("Albion вернул ссылку с учётными данными")

    return value.strip()


def _expiry(raw: Any, ttl_days: int) -> datetime:
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass

    return datetime.now(timezone.utc) + timedelta(days=ttl_days)


def _network_error(exc: Exception) -> CloudUploadError:
    if isinstance(exc, httpx.TimeoutException):
        return CloudUploadError("Albion не ответил вовремя")

    return CloudUploadError("не удалось соединиться с Albion")


def verify() -> dict:
    """Проверить токен и его права: GET /api/v1/integration/verify."""

    current = settings()

    if not current["base_url"] or not current["api_key"]:
        raise CloudConfigError("облачное хранилище Albion не настроено")

    headers = {"X-API-Key": current["api_key"]}

    try:
        response = httpx.get(
            _endpoint(current["base_url"], "/api/v1/integration/verify"),
            headers=headers,
            timeout=current["timeout"],
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        raise _network_error(exc) from exc
    finally:
        headers.clear()

    if response.status_code == 401:
        raise CloudUploadError("Albion отклонил токен")

    if response.status_code == 403:
        raise CloudUploadError("у токена нет права загрузки или доступа к папке")

    if response.status_code >= 400:
        raise CloudUploadError(f"Albion вернул HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise CloudUploadError("Albion вернул некорректный ответ") from exc

    if not isinstance(payload, dict):
        raise CloudUploadError("Albion вернул некорректный ответ")

    return {
        "ok": bool(payload.get("ok", True)),
        "name": payload.get("name") or "",
        "scopes": payload.get("scopes") or [],
        "folder_id": payload.get("folder_id") or "",
        "base_url": payload.get("base_url") or current["base_url"],
    }


def upload_file(path: Path, filename: str, *, ttl_days: int | None = None) -> dict:
    """Загрузить один файл и вернуть {url, expires_at, object_key}."""

    current = settings()

    if not current["base_url"] or not current["api_key"]:
        raise CloudConfigError("облачное хранилище Albion не настроено")

    ttl = int(ttl_days or current["ttl_days"])

    path = Path(path)

    if not path.is_file():
        raise CloudUploadError("исходный файл не найден")

    if path.stat().st_size <= 0:
        raise CloudUploadError("исходный файл пуст")

    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    headers = {"X-API-Key": current["api_key"]}
    data = {"ttl_days": str(ttl)}

    if current["folder_id"]:
        data["folder_id"] = current["folder_id"]

    try:
        with path.open("rb") as stream:
            response = httpx.post(
                _endpoint(current["base_url"], "/api/v1/integration/upload"),
                headers=headers,
                data=data,
                files={"file": (filename, stream, content_type)},
                timeout=current["timeout"],
                follow_redirects=False,
            )
    except httpx.HTTPError as exc:
        raise _network_error(exc) from exc
    finally:
        # Keep the API key out of tracebacks if a caller logs the exception.
        headers.clear()

    if response.status_code in {401, 403}:
        raise CloudUploadError("Albion отклонил API-ключ или права токена")

    if response.status_code == 404:
        raise CloudUploadError("папка Albion не найдена")

    if response.status_code == 413:
        raise CloudUploadError("файл слишком велик для Albion")

    if response.status_code == 429:
        retry = response.headers.get("Retry-After")
        suffix = f"; повтор через {retry} с" if retry else ""
        raise CloudUploadError(f"Albion ограничил частоту загрузок{suffix}")

    if response.status_code == 507:
        raise CloudUploadError("на хранилище Albion нет свободного места")

    if response.status_code >= 400:
        raise CloudUploadError(f"Albion вернул HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise CloudUploadError("Albion вернул некорректный ответ") from exc

    if not isinstance(payload, dict):
        raise CloudUploadError("Albion вернул некорректный ответ")

    item = payload
    links = payload.get("links")

    if isinstance(links, list) and links and isinstance(links[0], dict):
        item = links[0]

    url = item.get("url")

    if not isinstance(url, str) or not url.strip():
        raise CloudUploadError("Albion не вернул ссылку")

    return {
        "url": _safe_url(url),
        "expires_at": _expiry(item.get("expires_at"), ttl),
        "object_key": item.get("object_key") or item.get("key") or item.get("file_id"),
    }

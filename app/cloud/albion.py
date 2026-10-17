"""Minimal client for the Albion limited upload endpoint.

The contract is intentionally narrow: one multipart file per request, an
X-API-Key header, and a JSON response with a public URL and an expiry. The API
key is read from the environment and is never logged or returned to clients.
"""

from __future__ import annotations

import mimetypes
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


class CloudConfigError(RuntimeError):
    """Albion upload is not configured."""


class CloudUploadError(RuntimeError):
    """A safe, user-facing upload failure (no credentials or local paths)."""


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def settings() -> dict[str, Any]:
    url = (os.getenv("ALBION_UPLOAD_URL") or "").strip()
    key = (os.getenv("ALBION_API_KEY") or "").strip()
    try:
        ttl = int(os.getenv("ALBION_LINK_TTL_DAYS", "90"))
    except ValueError:
        ttl = 90
    ttl = max(1, min(ttl, 3650))
    return {
        "url": url,
        "api_key": key,
        "ttl_days": ttl,
        "timeout": _positive_float("ALBION_UPLOAD_TIMEOUT", 120.0),
    }


def is_configured() -> bool:
    current = settings()
    return bool(current["url"] and current["api_key"])


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


def upload_file(path: Path, filename: str, *, ttl_days: int | None = None) -> dict:
    """Upload one file and return {url, expires_at, object_key}."""

    current = settings()
    if not current["url"] or not current["api_key"]:
        raise CloudConfigError("облачное хранилище Albion не настроено")

    ttl = int(ttl_days or current["ttl_days"])
    path = Path(path)
    if not path.is_file():
        raise CloudUploadError("исходный файл не найден")
    if path.stat().st_size <= 0:
        raise CloudUploadError("исходный файл пуст")

    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    headers = {"X-API-Key": current["api_key"]}

    try:
        with path.open("rb") as stream:
            response = httpx.post(
                current["url"],
                headers=headers,
                data={"ttl_days": str(ttl)},
                files={"file": (filename, stream, content_type)},
                timeout=current["timeout"],
            )
    except httpx.TimeoutException as exc:
        raise CloudUploadError("Albion не ответил вовремя") from exc
    except httpx.HTTPError as exc:
        raise CloudUploadError("не удалось соединиться с Albion") from exc
    finally:
        # Keep the API key out of tracebacks if a caller logs the exception.
        headers.clear()

    if response.status_code in {401, 403}:
        raise CloudUploadError("Albion отклонил API-ключ")
    if response.status_code == 413:
        raise CloudUploadError("файл слишком велик для Albion")
    if response.status_code == 429:
        retry = response.headers.get("Retry-After")
        suffix = f"; повтор через {retry} с" if retry else ""
        raise CloudUploadError(f"Albion ограничил частоту загрузок{suffix}")
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
        "object_key": item.get("object_key") or item.get("key"),
    }

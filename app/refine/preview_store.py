"""Short-lived in-memory tokens for explicit REFINE preview application."""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from typing import Any

_TTL_SECONDS = 15 * 60
_lock = threading.Lock()
_previews: dict[str, dict[str, Any]] = {}


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_preview(*, proposals: list[dict], scope: dict, rules_version: int) -> dict[str, str]:
    token = secrets.token_urlsafe(24)
    expires = time.time() + _TTL_SECONDS
    fingerprint = _fingerprint({"proposals": proposals, "scope": scope, "rules_version": rules_version})
    with _lock:
        _purge_expired()
        _previews[token] = {
            "proposals": proposals,
            "scope": scope,
            "rules_version": rules_version,
            "fingerprint": fingerprint,
            "expires": expires,
        }
    return {"preview_token": token, "preview_fingerprint": fingerprint, "expires_in_seconds": _TTL_SECONDS}


def consume_preview(token: str) -> dict[str, Any] | None:
    with _lock:
        _purge_expired()
        return _previews.pop(token, None)


def _purge_expired() -> None:
    now = time.time()
    for token in [key for key, value in _previews.items() if value["expires"] <= now]:
        _previews.pop(token, None)

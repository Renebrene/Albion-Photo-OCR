"""In-process security counters for the System tab and network alerts.

The counters are intentionally small and bounded: the API process keeps a
rolling window of failed logins and request rates. They reset on restart,
which is acceptable for early-warning alerts; durable audit of destructive
actions is a separate feature.
"""

from __future__ import annotations

import os
import time
from collections import deque

LOGIN_FAILURE_WINDOW = int(os.getenv("SCENE_LOGIN_FAILURE_WINDOW", "600"))
LOGIN_FAILURE_LIMIT = int(os.getenv("SCENE_LOGIN_FAILURE_LIMIT", "10"))
REQUEST_WINDOW = int(os.getenv("SCENE_REQUEST_WINDOW", "60"))
REQUEST_LIMIT = int(os.getenv("SCENE_REQUEST_LIMIT", "300"))

_failures: deque[tuple[float, str, str]] = deque(maxlen=5000)
_requests: deque[tuple[float, str, str]] = deque(maxlen=20000)


def record_login_failure(ip: str, name: str) -> None:
    _failures.append((time.time(), str(ip or "unknown"), str(name or "")))


def record_request(ip: str, path: str) -> None:
    _requests.append((time.time(), str(ip or "unknown"), str(path or "")))


def _prune(now: float) -> None:
    login_deadline = now - LOGIN_FAILURE_WINDOW
    while _failures and _failures[0][0] < login_deadline:
        _failures.popleft()

    request_deadline = now - REQUEST_WINDOW
    while _requests and _requests[0][0] < request_deadline:
        _requests.popleft()


def snapshot() -> dict:
    """Current failure/request counters (no persistence, bounded memory)."""

    now = time.time()
    _prune(now)

    by_ip: dict[str, int] = {}
    for _, ip, _ in _failures:
        by_ip[ip] = by_ip.get(ip, 0) + 1

    requests_by_ip: dict[str, int] = {}
    for _, ip, _ in _requests:
        requests_by_ip[ip] = requests_by_ip.get(ip, 0) + 1

    return {
        "login_failures": len(_failures),
        "login_failures_by_ip": by_ip,
        "login_failure_window_sec": LOGIN_FAILURE_WINDOW,
        "login_failure_limit": LOGIN_FAILURE_LIMIT,
        "requests_by_ip": requests_by_ip,
        "request_window_sec": REQUEST_WINDOW,
        "request_limit": REQUEST_LIMIT,
    }


def client_ip(request) -> str:
    """Client address; X-Forwarded-For is trusted only with SCENE_TRUST_PROXY=1."""

    if os.getenv("SCENE_TRUST_PROXY", "0") == "1":
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()

    client = getattr(request, "client", None)
    return getattr(client, "host", "") or "unknown"

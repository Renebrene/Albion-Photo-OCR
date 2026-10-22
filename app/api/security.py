"""In-process security counters, login lockout and request-rate enforcement.

The counters are intentionally small and bounded: the API process keeps a
rolling window of failed logins and request rates. They reset on restart,
which is acceptable for early-warning alerts; durable audit of destructive
actions is a separate feature.

Two of them also *act*, not only report:

- login lockout — after `SCENE_LOGIN_FAILURE_LIMIT` failures from one address
  within `SCENE_LOGIN_FAILURE_WINDOW`, login from that address is refused with
  429 until the oldest failure leaves the window (`SCENE_LOGIN_LOCKOUT=0`
  turns it off);
- API request rate — off by default (`SCENE_API_RATE_LIMIT=0`), because a
  single grid page legitimately loads hundreds of preview images. Turn it on
  when the API is reachable from the internet.
"""

from __future__ import annotations

import os
import time
from collections import deque

LOGIN_FAILURE_WINDOW = int(os.getenv("SCENE_LOGIN_FAILURE_WINDOW", "600"))
LOGIN_FAILURE_LIMIT = int(os.getenv("SCENE_LOGIN_FAILURE_LIMIT", "10"))
REQUEST_WINDOW = int(os.getenv("SCENE_REQUEST_WINDOW", "60"))
REQUEST_LIMIT = int(os.getenv("SCENE_REQUEST_LIMIT", "300"))
# Requests per minute per address; 0 disables enforcement (default).
RATE_LIMIT = int(os.getenv("SCENE_API_RATE_LIMIT", "0"))
LOGIN_LOCKOUT_ENABLED = os.getenv("SCENE_LOGIN_LOCKOUT", "1") != "0"

_failures: deque[tuple[float, str, str]] = deque(maxlen=5000)
_requests: deque[tuple[float, str, str]] = deque(maxlen=20000)
# Fixed-window counters for enforcement: address -> (window index, count).
_rate_window: dict[str, tuple[int, int]] = {}


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


def login_lockout(ip: str) -> int:
    """
    Seconds the address must wait before another login attempt; 0 = allowed.

    The rule is deliberately simple: `SCENE_LOGIN_FAILURE_LIMIT` failures from
    the same address inside `SCENE_LOGIN_FAILURE_WINDOW` block it until the
    oldest of them ages out. A legitimate user who mistyped a few times is not
    affected; a guessing loop is stopped after the limit and stays stopped for
    as long as it keeps trying.
    """

    if not LOGIN_LOCKOUT_ENABLED:
        return 0

    now = time.time()
    _prune(now)

    stamps = [moment for moment, address, _ in _failures if address == str(ip)]

    if len(stamps) < LOGIN_FAILURE_LIMIT:
        return 0

    # До тех пор, пока самая старая ошибка окна не выйдет за его границу.
    return max(1, int(LOGIN_FAILURE_WINDOW - (now - min(stamps))) + 1)


def clear_login_failures(ip: str) -> None:
    """A successful login forgets earlier failures from the same address."""

    global _failures

    address = str(ip)
    kept = deque(
        (item for item in _failures if item[1] != address),
        maxlen=_failures.maxlen,
    )
    _failures = kept


def note_request(ip: str) -> int:
    """
    Count one API request and return seconds to wait, 0 when it is allowed.

    Fixed-window counter per address: cheap (O(1) per request) and enough to
    stop a hammering client. Disabled unless SCENE_API_RATE_LIMIT is set.
    """

    if RATE_LIMIT <= 0:
        return 0

    window = int(time.time() // max(1, REQUEST_WINDOW))
    address = str(ip)
    index, count = _rate_window.get(address, (window, 0))

    if index != window:
        index, count = window, 0

    count += 1
    _rate_window[address] = (index, count)

    # Словарь ограничен: адреса прошлых окон уходят при следующем обращении.
    if len(_rate_window) > 10000:
        _rate_window.clear()
        _rate_window[address] = (index, count)

    if count <= RATE_LIMIT:
        return 0

    return REQUEST_WINDOW


def rate_limit_enabled() -> bool:
    return RATE_LIMIT > 0


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

"""
Блокировка подбора пароля и ограничение частоты запросов.

Проверяется без базы: правило срабатывает до обращения к пользователям,
поэтому 429 должен приходить и при недоступной БД.
"""

from __future__ import annotations

from collections import deque

import pytest
from fastapi.testclient import TestClient

from app.api import security
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_counters(monkeypatch):
    """Каждый тест получает пустые счётчики и предсказуемые пределы."""

    monkeypatch.setattr(security, "_failures", deque(maxlen=5000))
    monkeypatch.setattr(security, "_requests", deque(maxlen=20000))
    monkeypatch.setattr(security, "_rate_window", {})
    monkeypatch.setattr(security, "LOGIN_FAILURE_LIMIT", 3)
    monkeypatch.setattr(security, "LOGIN_FAILURE_WINDOW", 600)
    monkeypatch.setattr(security, "LOGIN_LOCKOUT_ENABLED", True)
    monkeypatch.setattr(security, "RATE_LIMIT", 0)
    yield


# ---- правило блокировки (чистые функции) ----------------------------------


def test_below_the_limit_is_allowed():
    for _ in range(2):
        security.record_login_failure("10.0.0.1", "admin")

    assert security.login_lockout("10.0.0.1") == 0


def test_limit_reached_blocks_for_the_rest_of_the_window():
    for _ in range(3):
        security.record_login_failure("10.0.0.1", "admin")

    wait = security.login_lockout("10.0.0.1")

    assert 1 <= wait <= 601


def test_failures_of_another_address_do_not_block():
    for _ in range(5):
        security.record_login_failure("10.0.0.9", "admin")

    assert security.login_lockout("10.0.0.1") == 0


def test_successful_login_forgets_earlier_failures():
    for _ in range(3):
        security.record_login_failure("10.0.0.1", "admin")
    assert security.login_lockout("10.0.0.1") > 0

    security.clear_login_failures("10.0.0.1")

    assert security.login_lockout("10.0.0.1") == 0
    # Ошибки других адресов не затронуты.
    security.record_login_failure("10.0.0.2", "admin")
    security.clear_login_failures("10.0.0.1")
    assert security.snapshot()["login_failures"] == 1


def test_lockout_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(security, "LOGIN_LOCKOUT_ENABLED", False)

    for _ in range(10):
        security.record_login_failure("10.0.0.1", "admin")

    assert security.login_lockout("10.0.0.1") == 0


# ---- маршрут входа ---------------------------------------------------------


def test_login_returns_429_after_the_limit():
    for _ in range(3):
        security.record_login_failure("testclient", "кто-то")

    response = client.post(
        "/api/v1/auth/login",
        json={"name": "кто-то", "password": "что-то"},
    )

    assert response.status_code == 429
    assert "попыток входа" in response.json()["detail"]
    assert int(response.headers["retry-after"]) >= 1


def test_login_is_not_blocked_before_the_limit():
    """Ниже порога 429 быть не должно: идёт обычная проверка учётных данных."""

    for _ in range(2):
        security.record_login_failure("testclient", "кто-то")

    response = client.post(
        "/api/v1/auth/login",
        json={"name": "кто-то", "password": "что-то"},
    )

    assert response.status_code != 429


# ---- ограничение частоты запросов ------------------------------------------


def test_rate_limit_is_off_by_default():
    assert security.RATE_LIMIT == 0
    assert security.note_request("10.0.0.1") == 0
    for _ in range(1000):
        assert security.note_request("10.0.0.1") == 0


def test_rate_limit_counts_per_address(monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMIT", 2)

    assert security.note_request("10.0.0.1") == 0
    assert security.note_request("10.0.0.1") == 0
    assert security.note_request("10.0.0.1") == security.REQUEST_WINDOW
    # Другой адрес считает своё окно.
    assert security.note_request("10.0.0.2") == 0


def test_rate_limit_returns_429_when_enabled(monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMIT", 1)

    first = client.get("/api/v1/photos?limit=1")
    second = client.get("/api/v1/photos?limit=1")

    assert first.status_code != 429
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_health_is_never_rate_limited(monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMIT", 1)

    for _ in range(5):
        assert client.get("/api/health").status_code == 200


# ---- документация API ------------------------------------------------------


def test_docs_are_closed_by_default():
    from app.api import main as api_main

    assert api_main.ENABLE_DOCS is False

    anonymous = TestClient(app)

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert anonymous.get(path).status_code == 404, path


def test_docs_can_be_enabled(monkeypatch):
    from app.api import main as api_main

    monkeypatch.setattr(api_main, "ENABLE_DOCS", True)
    enabled = TestClient(api_main.create_app())

    assert enabled.get("/openapi.json").status_code == 200
    assert enabled.get("/docs").status_code == 200

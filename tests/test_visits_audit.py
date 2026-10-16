"""
Посещения (schema/033) и аудит нормализации клиентов.

DB-free тесты покрывают валидацию, права на маршруты и запись входа; тесты,
которые читают/пишут строки, требуют PostgreSQL и пропускаются без него.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.api.main import app
from app import visits as visits_mod

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.user_visits')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="schema/033 (visits/audit) is not applied / no PostgreSQL",
)


def test_visit_event_must_be_known():
    with pytest.raises(ValueError):
        visits_mod.record_visit(user_id=1, user_name="x", event="banana")


def test_visits_endpoint_requires_admin_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/visits", headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_alias_audit_requires_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/client-aliases/audit", headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_qwen_names_require_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/client-aliases/qwen-names",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_login_records_a_visit(monkeypatch):
    user = {
        "user_id": 1, "name": "Администратор", "role": "Администратор",
        "active": True, "password_hash": "scrypt$s$h",
    }
    monkeypatch.setattr(api_routes.users_db, "get_user_by_name", lambda name: user)
    monkeypatch.setattr(api_routes, "has_password", lambda h: True)
    monkeypatch.setattr(api_routes, "verify_password", lambda p, h: True)
    monkeypatch.setattr(api_routes.users_db, "create_session", lambda uid: "tok")

    seen = {}
    monkeypatch.setattr(visits_mod, "record_visit", lambda **kw: seen.update(kw))

    response = client.post(
        "/api/v1/auth/login", json={"name": "Администратор", "password": "x"},
    )

    assert response.status_code == 200
    assert seen.get("event") == "login"
    assert seen.get("user_name") == "Администратор"


def test_login_still_succeeds_when_visit_logging_fails(monkeypatch):
    user = {
        "user_id": 1, "name": "Администратор", "role": "Администратор",
        "active": True, "password_hash": "scrypt$s$h",
    }
    monkeypatch.setattr(api_routes.users_db, "get_user_by_name", lambda name: user)
    monkeypatch.setattr(api_routes, "has_password", lambda h: True)
    monkeypatch.setattr(api_routes, "verify_password", lambda p, h: True)
    monkeypatch.setattr(api_routes.users_db, "create_session", lambda uid: "tok")

    def boom(**_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(visits_mod, "record_visit", boom)

    response = client.post(
        "/api/v1/auth/login", json={"name": "Администратор", "password": "x"},
    )

    assert response.status_code == 200
    assert response.json()["token"] == "tok"


@requires_db
def test_alias_change_is_audited(monkeypatch):
    from app.api import repository

    alias = "ТестКлиент-аудит-7788"
    try:
        repository.upsert_client_alias(alias, "Канон", actor="Тестер")
        audit = repository.list_client_alias_audit(limit=5)
        top = audit[0]
        assert top["alias"] == alias
        assert top["action"] == "create"
        assert top["actor"] == "Тестер"

        repository.delete_client_alias(alias, actor="Тестер")
        audit = repository.list_client_alias_audit(limit=5)
        assert audit[0]["action"] == "delete"
        assert audit[0]["alias"] == alias
    finally:
        repository.delete_client_alias(alias)

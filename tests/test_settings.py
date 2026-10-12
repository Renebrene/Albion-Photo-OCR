"""
Tests for app_settings (QWEN model selection).

Scope checks run everywhere; persistence needs PostgreSQL with schema 008.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import settings_store
from app.api.main import app
from app.ingest.database import get_connection

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.app_settings')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="app_settings not available (INGEST_DB_* / schema 008)",
)


def test_set_model_requires_jobs_write(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.put(
        "/api/v1/qwen/model",
        json={"model": "qwen3-vl:8b"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_unload_requires_jobs_write(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/qwen/unload",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_models_requires_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:jobs:write,jobs:read")
    response = client.get(
        "/api/v1/qwen/models",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


@requires_db
def test_settings_store_roundtrip():
    key = "qwen_model"
    original = settings_store.get(key)

    try:
        settings_store.set_value(key, "test-model-x")
        assert settings_store.get(key) == "test-model-x"
    finally:
        if original is None:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.app_settings WHERE key = %s",
                        (key,),
                    )
        else:
            settings_store.set_value(key, original)


@requires_db
def test_api_sets_model(monkeypatch):
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)

    key = "qwen_model"
    original = settings_store.get(key)

    try:
        response = client.put(
            "/api/v1/qwen/model",
            json={"model": "qwen3-vl:8b"},
        )
        assert response.status_code == 200
        assert response.json()["model"] == "qwen3-vl:8b"
        assert settings_store.get(key) == "qwen3-vl:8b"
    finally:
        if original is None:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.app_settings WHERE key = %s",
                        (key,),
                    )
        else:
            settings_store.set_value(key, original)

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


# Ключи, которыми тесты настроек не должны «сочиться» в рабочую базу.
MODEL_KEYS = ("qwen_model", "qwen_model_ollama", "qwen_model_openai")


def _snapshot_model_keys() -> dict:
    return {key: settings_store.get(key) for key in MODEL_KEYS}


def _restore_model_keys(snapshot: dict) -> None:
    """
    Вернуть настройки к состоянию до теста, включая «ключа не было».

    Тесты писали в НАСТОЯЩИЕ настройки рабочей базы: однажды после прогона
    осталась несуществующая облачная модель, и воркер отвечал «Not Found» на
    каждом фото.
    """

    for key, value in snapshot.items():
        if value is None:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.app_settings WHERE key = %s",
                        (key,),
                    )
        else:
            settings_store.set_value(key, value)


@requires_db
def test_settings_store_roundtrip():
    snapshot = _snapshot_model_keys()

    try:
        settings_store.set_value("qwen_model", "test-model-x")
        assert settings_store.get("qwen_model") == "test-model-x"
    finally:
        _restore_model_keys(snapshot)


@requires_db
def test_api_sets_model(monkeypatch):
    """Модель сохраняется для ТЕКУЩЕГО провайдера (своя у каждого)."""

    from app.qwen import processor as qwen_processor

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)

    provider = qwen_processor.resolve_settings()["provider"]
    key = qwen_processor.QWEN_MODEL_KEYS[provider]
    snapshot = _snapshot_model_keys()
    probe = "__probe_model__"

    try:
        response = client.put(
            "/api/v1/qwen/model",
            json={"model": probe},
        )
        assert response.status_code == 200
        assert response.json()["model"] == probe
        assert settings_store.get(key) == probe
        # Сохранение модели не подменяет модель другого провайдера.
        other = next(
            name
            for name in qwen_processor.QWEN_MODEL_KEYS.values()
            if name != key
        )
        assert settings_store.get(other) == snapshot[other]
    finally:
        _restore_model_keys(snapshot)

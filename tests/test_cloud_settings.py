"""
API настроек файлохранилища Albion.

Без PostgreSQL: `set_setting`/`get_setting` подменяются словарём в памяти,
поэтому тесты проверяют только контракт и маскировку секрета.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.cloud import albion, config

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def memory_store(monkeypatch):
    values: dict = {}

    monkeypatch.setattr(
        config, "get_setting", lambda key, default=None: values.get(key, default)
    )
    monkeypatch.setattr(
        config, "set_setting", lambda key, value: values.__setitem__(key, value)
    )

    return values


def test_settings_are_masked(memory_store, monkeypatch):
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")

    response = client.put(
        "/api/v1/cloud/settings",
        json={
            "base_url": "https://files.example.ru",
            "api_key": "super-secret-token",
            "folder_id": "folder-1",
            "ttl_days": 30,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["base_url"] == "https://files.example.ru"
    assert body["folder_id"] == "folder-1"
    assert body["ttl_days"] == 30
    assert body["api_key_set"] is True
    assert "super-secret-token" not in response.text

    assert client.get("/api/v1/cloud/settings").json()["api_key_set"] is True


def test_an_empty_token_clears_it(memory_store):
    config.update_settings(api_key="secret")
    config.update_settings(api_key="")

    assert config.resolve_settings()["api_key"] == ""


def test_a_missing_token_keeps_the_stored_one(memory_store):
    config.update_settings(api_key="secret")
    config.update_settings(api_key=None)

    assert config.resolve_settings()["api_key"] == "secret"


def test_only_the_administrator_can_change_settings(memory_store, monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "reader:read")

    response = client.put(
        "/api/v1/cloud/settings",
        json={"base_url": "https://files.example.ru"},
        headers={"Authorization": "Bearer reader"},
    )

    assert response.status_code == 403


def test_an_invalid_url_is_rejected(memory_store, monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "admin:*")

    response = client.put(
        "/api/v1/cloud/settings",
        json={"base_url": "javascript:alert(1)"},
        headers={"Authorization": "Bearer admin"},
    )

    assert response.status_code == 422


def test_verify_reports_success(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "admin:*")
    monkeypatch.setattr(
        albion,
        "verify",
        lambda: {
            "ok": True,
            "name": "Photobase",
            "scopes": ["upload"],
            "folder_id": "folder-1",
        },
    )

    response = client.post(
        "/api/v1/cloud/verify",
        headers={"Authorization": "Bearer admin"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Photobase"


def test_verify_maps_a_rejected_token(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "admin:*")
    monkeypatch.setattr(
        albion,
        "verify",
        Mock(side_effect=albion.CloudUploadError("Albion отклонил токен")),
    )

    response = client.post(
        "/api/v1/cloud/verify",
        headers={"Authorization": "Bearer admin"},
    )

    assert response.status_code == 422
    assert "отклонил" in response.json()["detail"]


def test_verify_without_configuration_is_503(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "admin:*")
    monkeypatch.setattr(
        albion,
        "verify",
        Mock(side_effect=albion.CloudConfigError("Albion не настроен")),
    )

    response = client.post(
        "/api/v1/cloud/verify",
        headers={"Authorization": "Bearer admin"},
    )

    assert response.status_code == 503

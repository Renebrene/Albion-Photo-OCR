"""
Tests for optional bearer-token authentication (app.api.auth).

When SCENE_API_TOKENS is unset the API is open; when it is set, read
endpoints need scope "read" and originals need scope "originals".
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_is_always_open(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    assert client.get("/api/health").status_code == 200


def test_open_when_tokens_unset(monkeypatch):
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    # No token configured -> endpoint is reachable (DB may 500 without creds,
    # but it must not be 401/403).
    response = client.get("/api/v1/photos?limit=1")
    assert response.status_code not in (401, 403)


def test_missing_token_is_401(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get("/api/v1/photos")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_invalid_token_is_401(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/photos",
        headers={"Authorization": "Bearer nope"},
    )
    assert response.status_code == 401


def test_insufficient_scope_is_403(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:originals")
    response = client.get(
        "/api/v1/photos",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_originals_needs_originals_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/photos/PH_" + "0" * 24 + "/original",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_wildcard_scope_allows_read(monkeypatch):
    if not os.getenv("INGEST_DB_PASSWORD"):
        pytest.skip("integration PostgreSQL is not configured")

    monkeypatch.setenv("SCENE_API_TOKENS", "admin:*")
    response = client.get(
        "/api/v1/photos?limit=1",
        headers={"Authorization": "Bearer admin"},
    )
    assert response.status_code == 200

"""
Tests for the automation scheduler (schema 012).

Scope checks run everywhere; settings/lifecycle need PostgreSQL. Ticks are
run with auto_dino/auto_qwen disabled so the tests never enqueue jobs.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.ingest.database import get_connection

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.automation_settings')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="automation_settings not available (INGEST_DB_* / schema 012)",
)


@pytest.fixture
def restore_settings():
    yield
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.automation_settings SET "
                "enabled = FALSE, auto_dino = FALSE, auto_qwen = TRUE, "
                "interval_minutes = 60, last_tick = NULL WHERE id = 1"
            )


def test_update_requires_jobs_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.put(
        "/api/v1/automation",
        json={"enabled": True},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_run_requires_jobs_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/automation/run",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


@requires_db
def test_automation_lifecycle(restore_settings):
    defaults = client.get("/api/v1/automation").json()
    assert set(defaults) == {
        "enabled",
        "interval_minutes",
        "auto_dino",
        "auto_qwen",
        "last_tick",
        "updated_at",
    }
    assert defaults["enabled"] is False

    updated = client.put(
        "/api/v1/automation",
        json={
            "enabled": True,
            "interval_minutes": 30,
            "auto_dino": False,
            "auto_qwen": False,
        },
    ).json()
    assert updated["enabled"] is True
    assert updated["interval_minutes"] == 30
    assert updated["auto_qwen"] is False

    # With both sources disabled a forced tick enqueues nothing.
    result = client.post("/api/v1/automation/run?force=true").json()
    assert result.get("dino_batch_id") is None
    assert result.get("qwen_jobs") == 0


@requires_db
def test_disabled_tick_is_skipped(restore_settings):
    client.put("/api/v1/automation", json={"enabled": False})
    result = client.post("/api/v1/automation/run").json()
    assert result == {"skipped": "disabled"}

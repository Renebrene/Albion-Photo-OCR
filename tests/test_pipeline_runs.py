"""
Resumable pipeline supervisor (schema/031).

DB-free tests cover the pure helpers, the frozen-file filter and the API
routes (with the supervisor stubbed). The state-machine tests need PostgreSQL
and skip without INGEST_DB_*.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api import routes as api_routes
from app.api.main import app
from app.ingest import pipeline as ingest_pipeline
from app.supervisor import runs as pipeline_runs

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.pipeline_runs')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="schema/031 (pipeline_runs) is not applied / no PostgreSQL",
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_stage_order_is_fixed():
    assert pipeline_runs.STAGES == ("INGEST", "PREVIEW", "DINO", "HYBRID", "QWEN")
    assert pipeline_runs._next_stage("INGEST") == "PREVIEW"
    assert pipeline_runs._next_stage("HYBRID") == "QWEN"
    assert pipeline_runs._next_stage("QWEN") is None


def test_cutoff_reads_manifest():
    assert pipeline_runs._cutoff({"manifest": {"photo_cutoff": "2026-10-16 10:00:00"}}) == (
        "2026-10-16 10:00:00"
    )
    assert pipeline_runs._cutoff({"manifest": {}}) is None


# ---------------------------------------------------------------------------
# Frozen file snapshot (INGEST filter)
# ---------------------------------------------------------------------------


def _make_jpeg(path):
    Image.new("RGB", (8, 8), (10, 20, 30)).save(path, format="JPEG")


def test_only_files_restricts_the_scan(tmp_path):
    _make_jpeg(tmp_path / "a.jpg")
    _make_jpeg(tmp_path / "b.jpg")

    full = ingest_pipeline.run(tmp_path, workers=1)
    assert full.discovered == 2

    scoped = ingest_pipeline.run(tmp_path, workers=1, only_files={"a.jpg"})
    assert scoped.discovered == 1
    assert {item.filename for item in scoped.results} == {"a.jpg"}


def test_only_files_with_no_match_processes_nothing(tmp_path):
    _make_jpeg(tmp_path / "a.jpg")

    result = ingest_pipeline.run(tmp_path, workers=1, only_files={"gone.jpg"})
    assert result.discovered == 0
    assert result.results == []


# ---------------------------------------------------------------------------
# API routes (supervisor stubbed)
# ---------------------------------------------------------------------------


def test_start_returns_409_when_busy(monkeypatch):
    def busy(**_kwargs):
        raise pipeline_runs.PipelineBusy("pipeline run already active")

    monkeypatch.setattr(pipeline_runs, "create_run", busy)
    monkeypatch.setattr(api_routes.sources, "current_folder", lambda: "")

    response = client.post("/api/v1/pipeline/start", json={"folder": None})
    assert response.status_code == 409


def test_start_accepts_and_returns_run(monkeypatch):
    monkeypatch.setattr(
        pipeline_runs, "create_run",
        lambda **_kwargs: {"run_id": 5, "status": "RUNNING", "stage": "INGEST", "stages": []},
    )
    monkeypatch.setattr(api_routes.sources, "current_folder", lambda: "")

    response = client.post("/api/v1/pipeline/start", json={})
    assert response.status_code == 202
    assert response.json()["run_id"] == 5


def test_current_returns_null_when_no_runs(monkeypatch):
    monkeypatch.setattr(pipeline_runs, "active_run", lambda: None)
    monkeypatch.setattr(pipeline_runs, "latest_run", lambda: None)

    response = client.get("/api/v1/pipeline/current")
    assert response.status_code == 200
    assert response.json() == {"run": None}


def test_stop_unknown_run_is_409(monkeypatch):
    monkeypatch.setattr(pipeline_runs, "request_stop", lambda _run_id: False)
    response = client.post("/api/v1/pipeline/999999/stop")
    assert response.status_code == 409


def test_resume_busy_is_409(monkeypatch):
    def busy(_run_id):
        raise pipeline_runs.PipelineBusy("another pipeline run is active")

    monkeypatch.setattr(pipeline_runs, "resume_run", busy)
    response = client.post("/api/v1/pipeline/3/resume")
    assert response.status_code == 409


def test_pipeline_read_endpoints_require_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:jobs:write")
    response = client.get(
        "/api/v1/pipeline/current",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_pipeline_start_requires_jobs_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/pipeline/start",
        json={},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# State machine (PostgreSQL)
# ---------------------------------------------------------------------------


@requires_db
def test_run_lifecycle_stop_and_resume(tmp_path):
    from app.ingest.database import get_connection

    # Clean any leftover runs so the single-active index is free.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.pipeline_runs")

    run = pipeline_runs.create_run(mode="manual", folder=str(tmp_path))
    run_id = run["run_id"]
    assert run["stage"] == "INGEST"
    assert [s["stage"] for s in run["stages"]] == list(pipeline_runs.STAGES)

    # A second active run is refused.
    with pytest.raises(pipeline_runs.PipelineBusy):
        pipeline_runs.create_run(mode="manual", folder=str(tmp_path))

    # Stop before any work started flips it to STOPPED immediately.
    assert pipeline_runs.request_stop(run_id) is True
    assert pipeline_runs.get_run(run_id)["status"] == "STOPPED"

    # Resume continues from the same stage and manifest.
    assert pipeline_runs.resume_run(run_id) is True
    assert pipeline_runs.get_run(run_id)["status"] == "RUNNING"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.pipeline_runs WHERE run_id = %s", (run_id,))


@requires_db
def test_tick_on_empty_folder_skips_ingest(tmp_path):
    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.pipeline_runs")

    run = pipeline_runs.create_run(mode="manual", folder=None)
    run_id = run["run_id"]

    # No folder -> INGEST is skipped and the run advances to the next stage.
    first = pipeline_runs.tick(run_id)
    assert first["outcome"] in {"ADVANCED", "DONE"}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.pipeline_runs WHERE run_id = %s", (run_id,))

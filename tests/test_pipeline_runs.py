"""
Resumable pipeline supervisor (schema/031).

DB-free tests cover the pure helpers, the frozen-file filter and the API
routes (with the supervisor stubbed). The state-machine tests need PostgreSQL
and skip without INGEST_DB_*.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api import routes as api_routes
from app.api.main import app
from app.ingest import pipeline as ingest_pipeline
from app.runs import coordination
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


def test_run_reports_done_over_total_progress(tmp_path):
    _make_jpeg(tmp_path / "a.jpg")
    _make_jpeg(tmp_path / "b.jpg")

    seen = []
    ingest_pipeline.run(
        tmp_path, workers=1,
        progress=lambda done, total: seen.append((done, total)),
    )

    assert seen[0] == (1, 2)
    assert seen[-1] == (2, 2)
    assert all(total == 2 for _, total in seen)


# ---------------------------------------------------------------------------
# API routes (supervisor stubbed)
# ---------------------------------------------------------------------------


def _noop_launch_gate(monkeypatch):
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(coordination, "launch_guard", guard)
    monkeypatch.setattr(coordination, "active_operation", lambda: None)


def test_start_returns_409_when_busy(monkeypatch):
    def busy(**_kwargs):
        raise pipeline_runs.PipelineBusy("pipeline run already active")

    _noop_launch_gate(monkeypatch)
    monkeypatch.setattr(pipeline_runs, "create_run", busy)
    monkeypatch.setattr(api_routes.sources, "current_folder", lambda: "")

    response = client.post("/api/v1/pipeline/start", json={"folder": None})
    assert response.status_code == 409


def test_start_accepts_and_returns_run(monkeypatch):
    _noop_launch_gate(monkeypatch)
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
    # Маршрут передаёт ещё и имя пользователя для журнала.
    monkeypatch.setattr(
        pipeline_runs, "request_stop", lambda _run_id, **_kwargs: False
    )
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


def _skip_if_pipeline_is_active():
    if pipeline_runs.active_run() is not None:
        pytest.skip("a real pipeline run is active; refusing to disturb it")


def _cleanup_pipeline_test_run(run_id: int) -> None:
    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.run_history')")
            if cur.fetchone()[0] is not None:
                cur.execute(
                    "DELETE FROM public.run_history "
                    "WHERE kind = 'pipeline' AND source_id = %s",
                    (str(run_id),),
                )
            cur.execute(
                "DELETE FROM public.pipeline_runs WHERE run_id = %s",
                (run_id,),
            )


@requires_db
def test_run_lifecycle_stop_and_resume(tmp_path):
    _skip_if_pipeline_is_active()

    run = pipeline_runs.create_run(mode="manual", folder=str(tmp_path))
    run_id = run["run_id"]

    try:
        assert run["stage"] == "INGEST"
        assert [s["stage"] for s in run["stages"]] == list(pipeline_runs.STAGES)

        # A second active run is refused.
        with pytest.raises(pipeline_runs.PipelineBusy):
            pipeline_runs.create_run(mode="manual", folder=str(tmp_path))

        # Stop before any work started flips it to STOPPED immediately, and the
        # log says who paused the run.
        assert pipeline_runs.request_stop(run_id, stopped_by="Тестер") is True
        stopped = pipeline_runs.get_run(run_id)
        assert stopped["status"] == "STOPPED"
        assert "Тестер" in (stopped["message"] or "")


        # Resume continues from the same stage and manifest.
        assert pipeline_runs.resume_run(run_id) is True
        assert pipeline_runs.get_run(run_id)["status"] == "RUNNING"
    finally:
        _cleanup_pipeline_test_run(run_id)


@requires_db
def test_tick_on_empty_folder_skips_ingest(tmp_path, monkeypatch):
    _skip_if_pipeline_is_active()

    # The tick must not enqueue real preview jobs while this test runs.
    monkeypatch.setattr(
        pipeline_runs, "enqueue_missing_previews", lambda **_kwargs: {"queued": 0}
    )

    run = pipeline_runs.create_run(mode="manual", folder=None)
    run_id = run["run_id"]

    try:
        # No folder -> INGEST is skipped and the run advances to the next stage.
        first = pipeline_runs.tick(run_id)
        assert first["outcome"] in {"ADVANCED", "DONE"}
    finally:
        _cleanup_pipeline_test_run(run_id)


# ---------------------------------------------------------------------------
# DINO stage: вход только у фото с превью, живые счётчики, сообщения
# ---------------------------------------------------------------------------


def test_dino_message_lists_files_and_skipped_photos():
    assert pipeline_runs._dino_message("нет фото без DINO", 0, 0) == (
        "нет фото без DINO"
    )
    assert pipeline_runs._dino_message(None, 0, 0) is None
    assert pipeline_runs._dino_message(None, 2, 1) == (
        "не удалось распознать файлов: 2; без превью (в DINO не ставим): 1"
    )


@requires_db
def test_dino_selector_needs_a_middle_preview(tmp_path):
    """Фото без превью в батч не попадает, но остаётся в счётчике пропуска."""

    import hashlib

    from PIL import Image as _Image

    from app.dino import database as dino_db
    from app.ingest import database as ingest_db
    from app.ingest.register import PhotoRecord

    ready_id = "PH_" + "1" * 24
    broken_id = "PH_" + "2" * 24
    ids = [ready_id, broken_id]

    records = []
    for photo_id in ids:
        image_path = tmp_path / f"{photo_id}.JPG"
        _Image.new("RGB", (16, 12), (5, 6, 7)).save(image_path, format="JPEG")
        records.append(
            PhotoRecord(
                photo_id=photo_id,
                source_path=str(image_path),
                filename=image_path.name,
                sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
                container_format="JPEG",
                frame_count=1,
                width=16,
                height=12,
            )
        )

    try:
        for record in records:
            ingest_db.insert_photo(record)

        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.photo_previews (
                        photo_id, small_path, middle_path,
                        small_width, small_height, middle_width, middle_height
                    )
                    VALUES (%s, %s, %s, 32, 24, 128, 96)
                    """,
                    (ready_id, "/tmp/small.webp", "/tmp/middle.webp"),
                )

        selected = pipeline_runs._photos_without_dino(None)

        assert ready_id in selected
        assert broken_id not in selected
        assert pipeline_runs._photos_without_preview(None) >= 1
    finally:
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT batch_id FROM public.dino_runs "
                    "WHERE photo_id = ANY(%s)",
                    (ids,),
                )
                batch_ids = [row[0] for row in cur.fetchall()]
                cur.execute(
                    "DELETE FROM public.dino_runs WHERE photo_id = ANY(%s)", (ids,)
                )
                for batch_id in batch_ids:
                    cur.execute(
                        "DELETE FROM public.dino_batches WHERE batch_id = %s",
                        (batch_id,),
                    )
                cur.execute(
                    "DELETE FROM public.photo_previews WHERE photo_id = ANY(%s)",
                    (ids,),
                )
                cur.execute(
                    "DELETE FROM public.photos WHERE photo_id = ANY(%s)", (ids,)
                )

    # Батч из одного фото: счётчики читаются из dino_runs, а не из строки
    # батча, поэтому прогресс виден во время работы.
    batch = dino_db.create_batch("FORCE_RERUN", [ready_id])
    try:
        assert pipeline_runs._batch_run_counts(batch.batch_id) == {
            "done": 0,
            "failed": 0,
        }

        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.dino_runs SET status = 'DONE', "
                    "finished_at = CURRENT_TIMESTAMP WHERE batch_id = %s",
                    (batch.batch_id,),
                )

        assert pipeline_runs._batch_run_counts(batch.batch_id) == {
            "done": 1,
            "failed": 0,
        }
    finally:
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.dino_runs WHERE batch_id = %s",
                    (batch.batch_id,),
                )
                cur.execute(
                    "DELETE FROM public.dino_batches WHERE batch_id = %s",
                    (batch.batch_id,),
                )


# ---------------------------------------------------------------------------
# Стадия PREVIEW: очередь наполняется, пока превью не хватает
# ---------------------------------------------------------------------------


def _preview_env(monkeypatch, *, total, done, active, ref=None):
    queued = []

    monkeypatch.setattr(pipeline_runs, "_cutoff", lambda run: None)
    monkeypatch.setattr(pipeline_runs, "_photos_total", lambda cutoff: total)
    monkeypatch.setattr(
        pipeline_runs, "_preview_ready_count", lambda cutoff: done
    )
    monkeypatch.setattr(
        pipeline_runs, "_active_type_count", lambda job_type: active
    )
    monkeypatch.setattr(
        pipeline_runs,
        "enqueue_missing_previews",
        lambda **kwargs: queued.append(kwargs) or {"queued": 0},
    )
    monkeypatch.setattr(pipeline_runs, "_set_stage", lambda *a, **k: None)

    return queued


def test_preview_stage_keeps_filling_the_queue(monkeypatch):
    """Одна страница превью не закрывает стадию, пока корпус не покрыт."""

    queued = _preview_env(monkeypatch, total=56_870, done=2_000, active=0)

    result = pipeline_runs._stage_preview(  # noqa: SLF001
        {"run_id": 1}, {"status": "RUNNING", "ref": {}}
    )

    assert result["outcome"] == "WAIT"
    assert queued and queued[0]["limit"] == pipeline_runs.PREVIEW_ENQUEUE_PAGE
    assert result["done_count"] == 2_000
    assert result["total_count"] == 56_870


def test_preview_stage_finishes_when_every_photo_has_a_preview(monkeypatch):
    queued = _preview_env(monkeypatch, total=100, done=100, active=0)

    result = pipeline_runs._stage_preview(  # noqa: SLF001
        {"run_id": 1}, {"status": "RUNNING", "ref": {}}
    )

    assert result["outcome"] == "DONE"
    assert queued == []


def test_preview_stage_gives_up_on_unreadable_files(monkeypatch):
    """Битые исходники превью не дадут: стадия завершается по сторожу."""

    _preview_env(monkeypatch, total=100, done=95, active=1)

    result = pipeline_runs._stage_preview(  # noqa: SLF001
        {"run_id": 1},
        {
            "status": "RUNNING",
            "ref": {"last_done": 95, "stall": pipeline_runs.PREVIEW_STALL_TICKS - 1},
        },
    )

    assert result["outcome"] == "DONE"
    assert result["failed_count"] == 5
    assert "нечитаемые" in result["message"]


def test_preview_refill_does_not_reset_the_stall_counter(monkeypatch):
    """Битые исходники: долив очереди не должен крутить стадию вечно."""

    queued = _preview_env(monkeypatch, total=56_870, done=56_868, active=0)

    result = pipeline_runs._stage_preview(  # noqa: SLF001
        {"run_id": 1},
        {
            "status": "RUNNING",
            "ref": {"last_done": 56_868, "stall": pipeline_runs.PREVIEW_STALL_TICKS - 1},
        },
    )

    assert queued, "очередь всё равно доливается"
    assert result["outcome"] == "DONE"
    assert result["failed_count"] == 2


def test_preview_stage_resets_the_stall_counter_on_progress(monkeypatch):
    _preview_env(monkeypatch, total=100, done=96, active=1)

    result = pipeline_runs._stage_preview(  # noqa: SLF001
        {"run_id": 1},
        {
            "status": "RUNNING",
            "ref": {"last_done": 95, "stall": pipeline_runs.PREVIEW_STALL_TICKS - 1},
        },
    )

    assert result["outcome"] == "WAIT"

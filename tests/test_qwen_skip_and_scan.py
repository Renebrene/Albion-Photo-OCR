"""
Skip QWEN in a pipeline run and enqueue it later for one period.

Pure tests: the stage handler and the request schema, no database.
"""

from __future__ import annotations

import pytest

from app.api.schemas import QwenPeriodScanRequest
from app.supervisor import runs


def test_qwen_stage_is_skipped_by_manifest_flag():
    result = runs._stage_qwen(  # noqa: SLF001
        {"manifest": {"skip_qwen": True}},
        {"status": "PENDING"},
    )

    assert result["outcome"] == "SKIPPED"
    assert result["total_count"] == 0
    assert "за период" in result["message"]


def test_early_qwen_is_not_enqueued_when_skipped(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        runs.jobs_db, "enqueue_qwen", lambda *a, **k: calls.append("x")
    )
    monkeypatch.setattr(runs, "_auto_qwen_enabled", lambda: True)

    runs._enqueue_early_qwen(  # noqa: SLF001
        {"run_id": 1, "manifest": {"skip_qwen": True}},
        {"skip_qwen": True, "photo_cutoff": None},
    )

    assert calls == []


def test_period_scan_defaults_to_capture_dates():
    request = QwenPeriodScanRequest(
        date_from="2026-10-01",
        date_to="2026-10-23",
    )

    assert request.date_mode == "capture"
    assert request.limit == 1000


def test_period_scan_rejects_reversed_dates():
    with pytest.raises(ValueError):
        QwenPeriodScanRequest(
            date_from="2026-10-23",
            date_to="2026-10-01",
        )


def test_period_scan_rejects_unknown_mode():
    with pytest.raises(ValueError):
        QwenPeriodScanRequest(
            date_from="2026-10-01",
            date_to="2026-10-23",
            date_mode="mtime",
        )


def test_qwen_stage_is_skipped_when_disabled_in_settings(monkeypatch):
    monkeypatch.setattr(runs, "_qwen_in_pipeline", lambda: False)

    result = runs._stage_qwen(  # noqa: SLF001
        {"manifest": {}},
        {"status": "PENDING"},
    )

    assert result["outcome"] == "SKIPPED"
    assert "за период" in result["message"]


def test_qwen_stage_runs_when_the_setting_is_on(monkeypatch):
    monkeypatch.setattr(runs, "_qwen_in_pipeline", lambda: True)
    monkeypatch.setattr(runs, "_photos_without_qwen", lambda cutoff: [])
    monkeypatch.setattr(runs, "_set_stage", lambda *a, **k: None)
    monkeypatch.setattr(runs, "_active_type_count", lambda job_type: 0)
    monkeypatch.setattr(runs, "_qwen_count", lambda cutoff, status: 2)
    monkeypatch.setattr(runs, "_photos_total", lambda cutoff: 2)

    result = runs._stage_qwen(  # noqa: SLF001
        {"run_id": 1, "manifest": {}},
        {"status": "PENDING"},
    )

    assert result["outcome"] == "DONE"
    assert result["done_count"] == 2


def test_early_qwen_respects_the_pipeline_setting(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        runs.jobs_db, "enqueue_qwen", lambda *a, **k: calls.append("x")
    )
    monkeypatch.setattr(runs, "_auto_qwen_enabled", lambda: True)
    monkeypatch.setattr(runs, "_qwen_in_pipeline", lambda: False)

    runs._enqueue_early_qwen(  # noqa: SLF001
        {"run_id": 1, "manifest": {}},
        {"photo_cutoff": None},
    )

    assert calls == []


# ---------------------------------------------------------------------------
# «Уточнение» последним этапом прогона
# ---------------------------------------------------------------------------


def _refine_env(monkeypatch, *, enabled=True, available=True):
    from app.refine import config as refine_config

    monkeypatch.setattr(refine_config, "enabled", lambda: enabled)
    monkeypatch.setattr(refine_config, "available", lambda: available)
    return refine_config


def test_refine_step_is_skipped_when_the_stage_is_off(monkeypatch):
    _refine_env(monkeypatch, enabled=False)
    monkeypatch.setattr(
        runs.jobs_db, "enqueue_refine", lambda *a, **k: pytest.fail("не должен ставить")
    )

    assert runs._refine_after_qwen(  # noqa: SLF001
        {"run_id": 1}, {"ref": {}}
    ) is None


def test_refine_step_is_skipped_without_qwen(monkeypatch):
    _refine_env(monkeypatch, available=False)
    monkeypatch.setattr(
        runs.jobs_db, "enqueue_refine", lambda *a, **k: pytest.fail("не должен ставить")
    )

    assert runs._refine_after_qwen(  # noqa: SLF001
        {"run_id": 1}, {"ref": {}}
    ) is None


def test_refine_step_enqueues_and_waits(monkeypatch):
    _refine_env(monkeypatch)

    saved = {}
    monkeypatch.setattr(runs.jobs_db, "active_refine_job", lambda: None)
    monkeypatch.setattr(runs.jobs_db, "enqueue_refine", lambda: 77)
    monkeypatch.setattr(
        runs, "_set_stage", lambda run_id, stage, **fields: saved.update(fields)
    )

    result = runs._refine_after_qwen(  # noqa: SLF001
        {"run_id": 5}, {"ref": {"qwen_started": True}}
    )

    assert result["outcome"] == "WAIT"
    assert "поставлено" in result["message"]
    assert saved["ref"] == {"qwen_started": True, "refine_job_id": 77}


def test_refine_step_waits_for_the_queued_job(monkeypatch):
    _refine_env(monkeypatch)
    monkeypatch.setattr(
        runs.jobs_db, "get_job", lambda job_id: {"status": "RUNNING"}
    )

    result = runs._refine_after_qwen(  # noqa: SLF001
        {"run_id": 5}, {"ref": {"refine_job_id": 77}}
    )

    assert result["outcome"] == "WAIT"


def test_refine_step_finishes_the_stage(monkeypatch):
    _refine_env(monkeypatch)
    monkeypatch.setattr(
        runs.jobs_db,
        "get_job",
        lambda job_id: {"status": "DONE", "result": {"photos_changed": 12}},
    )

    result = runs._refine_after_qwen(  # noqa: SLF001
        {"run_id": 5}, {"ref": {"refine_job_id": 77}}
    )

    assert result["outcome"] == "DONE"
    assert "12" in result["message"]


def test_refine_error_does_not_fail_the_run(monkeypatch):
    _refine_env(monkeypatch)
    monkeypatch.setattr(
        runs.jobs_db,
        "get_job",
        lambda job_id: {"status": "FAILED", "error_message": "boom"},
    )

    result = runs._refine_after_qwen(  # noqa: SLF001
        {"run_id": 5}, {"ref": {"refine_job_id": 77}}
    )

    assert result["outcome"] == "DONE"
    assert "ошибка" in result["message"]


def test_qwen_stage_waits_for_refine_before_finishing(monkeypatch):
    _refine_env(monkeypatch)
    monkeypatch.setattr(runs, "_qwen_in_pipeline", lambda: True)
    monkeypatch.setattr(runs, "_photos_without_qwen", lambda cutoff: [])
    monkeypatch.setattr(runs, "_set_stage", lambda *a, **k: None)
    monkeypatch.setattr(runs, "_active_type_count", lambda job_type: 0)
    monkeypatch.setattr(runs, "_qwen_count", lambda cutoff, status: 5)
    monkeypatch.setattr(runs, "_photos_total", lambda cutoff: 5)
    monkeypatch.setattr(runs.jobs_db, "active_refine_job", lambda: None)
    monkeypatch.setattr(runs.jobs_db, "enqueue_refine", lambda: 91)

    result = runs._stage_qwen(  # noqa: SLF001
        {"run_id": 1, "manifest": {}},
        {"status": "RUNNING", "ref": {}},
    )

    assert result["outcome"] == "WAIT"
    assert "уточнение" in result["message"]

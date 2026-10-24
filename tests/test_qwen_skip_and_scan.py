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

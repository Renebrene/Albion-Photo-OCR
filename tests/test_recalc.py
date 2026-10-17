"""One full recalculation is queued after a fingerprint change, never two."""

from __future__ import annotations

from types import SimpleNamespace

from app.dino import recalc


class _Cursor:
    def __init__(self, active_job=None):
        self.active_job = active_job
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql = " ".join(str(sql).split())

    def fetchone(self):
        if "pg_advisory_xact_lock" in self.sql:
            return (None,)
        if "FROM public.job_queue" in self.sql:
            return self.active_job
        return None

    def fetchall(self):
        return [("PH_a",), ("PH_b",)]


class _Connection:
    def __init__(self, active_job=None):
        self.cursor_obj = _Cursor(active_job)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self.cursor_obj


def _install(monkeypatch, active_job=None):
    calls = {"batch": [], "enqueue": [], "history": [], "jobs": []}

    monkeypatch.setattr(
        recalc, "get_connection", lambda: _Connection(active_job)
    )
    monkeypatch.setattr(
        recalc.dino_db,
        "create_batch",
        lambda run_type, ids: (
            calls["batch"].append((run_type, list(ids)))
            or SimpleNamespace(batch_id=10, total_count=len(ids))
        ),
    )
    monkeypatch.setattr(
        recalc.jobs_db,
        "enqueue",
        lambda *args, **kwargs: (
            calls["enqueue"].append((args, kwargs)) or 20
        ),
    )
    monkeypatch.setattr(
        recalc.run_history,
        "create_run",
        lambda **kwargs: (
            calls["history"].append(kwargs) or 30
        ),
    )
    monkeypatch.setattr(
        recalc.run_history,
        "add_jobs",
        lambda *args: calls["jobs"].append(("add", args)),
    )
    monkeypatch.setattr(
        recalc.run_history,
        "finish_enqueue",
        lambda *args, **kwargs: calls["jobs"].append(("finish", args, kwargs)),
    )

    return calls


def test_one_full_force_rerun_is_queued(monkeypatch):
    calls = _install(monkeypatch)

    result = recalc.enqueue_recalculation(
        reason="замены", fingerprint_id="78_v33"
    )

    assert result == {
        "batch_id": 10,
        "job_id": 20,
        "total": 2,
        "run_id": 30,
    }
    assert calls["batch"] == [("FORCE_RERUN", ["PH_a", "PH_b"])]
    args, kwargs = calls["enqueue"][0]
    assert args[0] == "DINO_BATCH"
    assert args[1] == {
        "batch_id": 10,
        "auto_hybrid": True,
        "recalc": True,
    }
    assert kwargs["run_history_id"] == 30
    assert calls["history"][0]["mode"] == "outofqueue"
    assert "78_v33" in calls["history"][0]["title"]


def test_no_second_pass_while_one_is_active(monkeypatch):
    calls = _install(monkeypatch, active_job=(5,))

    result = recalc.enqueue_recalculation(
        reason="скрытия", fingerprint_id="90_v33"
    )

    assert result is None
    assert calls["batch"] == []
    assert calls["enqueue"] == []

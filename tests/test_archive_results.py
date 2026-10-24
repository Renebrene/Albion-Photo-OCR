"""Архивация результатов: порядок переноса, счётчики, защита от гонки."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "archive_results", ROOT / "scripts" / "archive_results.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Cursor:
    def __init__(
        self,
        counts=None,
        rowcounts=None,
        sequence="public.dino_runs_run_id_seq",
        exists=None,
    ):
        self.counts = list(counts or [])
        self.rowcounts = list(rowcounts or [])
        self.sequence = sequence
        self.exists = list(exists or [])
        self.calls: list[tuple[str, object]] = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))

        if "pg_get_serial_sequence" in sql:
            return

        upper = sql.strip().upper()

        if upper.startswith(("INSERT", "DELETE", "UPDATE")):
            self.rowcount = self.rowcounts.pop(0) if self.rowcounts else 0

    def fetchone(self):
        last = self.calls[-1][0] if self.calls else ""

        if "pg_get_serial_sequence" in last:
            return (self.sequence,)

        if "to_regclass" in last:
            value = self.exists.pop(0) if self.exists else "public.x"
            return (value,)

        return (self.counts.pop(0) if self.counts else 0,)

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_architecture_pairs_cover_results_with_archives():
    module = _load()

    sources = [source for source, _a, _k in module.ARCHIVE_PAIRS]
    archives = [archive for _s, archive, _k in module.ARCHIVE_PAIRS]

    assert sources[:3] == ["dino_candidates", "dino_runs", "dino_batches"]
    assert all(name.endswith("_archive") for name in archives)
    # Слепки, фото и видео в архивацию не входят.
    assert "fingerprints" not in sources
    assert "photos" not in sources
    assert "video_assets" not in sources


def test_cancel_queued_jobs_takes_pending_running_and_paused():
    module = _load()
    cur = Cursor(rowcounts=[17_952])

    cancelled = module.cancel_queued_jobs(cur)

    sql, params = cur.calls[0]
    assert "status = 'CANCELLED'" in sql
    assert params[0] == ["PENDING", "RUNNING", "PAUSED"]
    assert "BILLBOARD_DETECT" in params[1]
    assert cancelled == 17_952


def test_archive_tables_moves_rows_then_clears_and_resets_counter():
    module = _load()
    # 8 пар: insert + delete на каждую.
    rowcounts = []
    for index in range(len(module.ARCHIVE_PAIRS)):
        rowcounts.extend([100 + index, 100 + index])
    cur = Cursor(rowcounts=rowcounts)

    moved = module.archive_tables(cur)

    inserts = [sql for sql, _ in cur.calls if sql.startswith("INSERT")]
    deletes = [sql for sql, _ in cur.calls if sql.startswith("DELETE")]

    assert inserts[0].startswith(
        "INSERT INTO public.dino_candidates_archive "
        "SELECT * FROM public.dino_candidates"
    )
    assert deletes == [
        f"DELETE FROM public.{source}"
        for source, _archive, _key in module.ARCHIVE_PAIRS
    ]
    assert moved["dino_runs"] == {"archived": 101, "cleared": 101}
    assert any(
        sql.startswith("ALTER SEQUENCE") and "RESTART WITH 1" in sql
        for sql, _ in cur.calls
    )


def test_archive_keeps_photos_and_fingerprints_untouched():
    module = _load()
    cur = Cursor(rowcounts=[0] * 40)

    module.archive_tables(cur)

    assert not any("public.photos" in sql for sql, _ in cur.calls)
    assert not any("fingerprints" in sql for sql, _ in cur.calls)


def test_reset_sequence_ignores_tables_without_one():
    module = _load()
    cur = Cursor(sequence=None)

    module._reset_sequence(cur, "photo_qwen_history", None)

    assert cur.calls == []


def test_plan_flags_a_missing_archive_table():
    module = _load()
    # Одна из проверок to_regclass отвечает None — миграция не применена.
    exists = ["public.dino_candidates_archive", None]
    cur = Cursor(counts=[0] * 40, exists=exists)

    report = module.plan(cur)

    assert report["missing_archive"] == ["dino_runs_archive"]


def test_main_refuses_while_jobs_are_running(monkeypatch, capsys):
    module = _load()
    cur = Cursor(counts=[0, 3])

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return cur

    monkeypatch.setattr(module, "get_connection", lambda: Conn())

    assert module.main(["--confirm"]) == 2
    assert not [sql for sql, _ in cur.calls if sql.startswith("DELETE")]
    assert "выполняющихся заданий" in capsys.readouterr().err

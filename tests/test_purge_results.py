"""Очистка результатов: SQL, защита от запуска во время прогона, файлы."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "purge_results", ROOT / "scripts" / "purge_results.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Cursor:
    """Курсор-заглушка: помнит запросы, отдаёт счётчики и rowcount."""

    def __init__(self, counts=None, rowcounts=None):
        self.counts = list(counts or [])
        self.rowcounts = list(rowcounts or [])
        self.calls: list[tuple[str, object]] = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))
        if sql.strip().upper().startswith("DELETE"):
            self.rowcount = self.rowcounts.pop(0) if self.rowcounts else 0

    def fetchone(self):
        value = self.counts.pop(0) if self.counts else 0
        return (value,)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_plan_counts_every_result_table():
    module = _load()
    cur = Cursor(counts=[7] * 20)

    report = module.plan(cur, previews=True, crops=True)

    assert set(report["tables"]) >= {
        "dino_candidates", "dino_runs", "dino_batches",
        "hybrid_results", "hybrid_runs", "photo_qwen", "photo_regions",
        "photo_previews",
    }
    assert report["tables"]["dino_runs"] == 7
    assert report["tables"]["photo_previews"] == 7
    # Регистрации фото остаются: они только считаются для отчёта.
    assert report["photos"] == 7


def test_previews_are_kept_unless_asked():
    module = _load()
    cur = Cursor(counts=[1] * 20)

    report = module.plan(cur, previews=False, crops=True)

    assert "photo_previews" not in report["tables"]


def test_purge_deletes_children_before_batches_and_keeps_photos():
    module = _load()
    cur = Cursor(rowcounts=[0, 1518, 23938, 3, 5, 28927])

    removed = module.purge(cur, previews=False, crops=True)

    deletes = [sql for sql, _ in cur.calls if sql.startswith("DELETE")]
    assert deletes == [
        "DELETE FROM public.photo_qwen_history",
        "DELETE FROM public.photo_qwen",
        "DELETE FROM public.hybrid_results",
        "DELETE FROM public.hybrid_runs",
        "DELETE FROM public.dino_batches",
        "DELETE FROM public.photo_regions",
    ]
    assert removed["photo_qwen"] == 1518
    assert removed["dino_batches"] == 5
    # Регистрации фото и слепки не трогаем.
    assert not any("public.photos" == sql.split()[-1] for sql in deletes)
    assert not any("fingerprints" in sql for sql in deletes)


def test_purge_can_drop_previews(monkeypatch):
    module = _load()
    cur = Cursor(counts=[100], rowcounts=[1, 1, 1, 1, 1, 1, 33_000])

    removed = module.purge(cur, previews=True, crops=False)

    assert removed["photo_previews"] == 33_000
    assert any(
        sql.startswith("DELETE FROM public.photo_previews") for sql, _ in cur.calls
    )


def test_main_refuses_while_a_run_is_active(monkeypatch, capsys):
    module = _load()
    cur = Cursor(counts=[1, 0])

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
    assert "активный прогон" in capsys.readouterr().err


def test_main_dry_run_writes_nothing(monkeypatch, capsys):
    module = _load()
    cur = Cursor(counts=[0, 0] + [5] * 20)

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return cur

    monkeypatch.setattr(module, "get_connection", lambda: Conn())
    monkeypatch.setattr(module, "_crops_root", lambda: Path("/нет/такого"))
    monkeypatch.setattr(module, "_preview_root", lambda: Path("/нет/такого"))

    assert module.main([]) == 0
    assert not [sql for sql, _ in cur.calls if sql.startswith("DELETE")]
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "--confirm" in out


def test_wipe_dir_removes_files_but_keeps_the_root(tmp_path):
    module = _load()
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "crop.webp").write_bytes(b"x" * 10)
    (tmp_path / "b.webp").write_bytes(b"y" * 5)

    report = module._wipe_dir(tmp_path)

    assert report["files"] == 2
    assert report["bytes"] == 15
    assert tmp_path.is_dir()
    assert list(tmp_path.iterdir()) == []


def test_wipe_dir_tolerates_a_missing_root(tmp_path):
    module = _load()

    report = module._wipe_dir(tmp_path / "нет")

    assert report["files"] == 0


def test_guard_lists_pipeline_job_types_including_refine():
    module = _load()

    assert "REFINE" in module.ACTIVE_JOB_TYPES
    assert "QWEN_PHOTO" in module.ACTIVE_JOB_TYPES


@pytest.mark.parametrize("table", ["photo_qwen", "dino_batches", "hybrid_runs"])
def test_result_tables_cover_the_recognition_results(table):
    module = _load()

    assert table in module.RESULT_TABLES

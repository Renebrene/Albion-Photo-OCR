"""Перенос корня источников: SQL и защитные проверки (без записи в БД)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "remap_source_root", ROOT / "scripts/remap_source_root.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Cursor:
    """Минимальный курсор: помнит запросы и отдаёт заранее заданные строки."""

    def __init__(self, counts=(), samples=(), rowcounts=()):
        self.counts = list(counts)
        self.samples = list(samples)
        self.rowcounts = list(rowcounts)
        self.calls = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if "UPDATE" in sql:
            self.rowcount = self.rowcounts.pop(0) if self.rowcounts else 0

    def fetchone(self):
        return (self.counts.pop(0),) if self.counts else (0,)

    def fetchall(self):
        return self.samples.pop(0) if self.samples else []


def test_prefix_drops_trailing_slash():
    module = _load()

    assert module._prefix("/media/БАЗАФОТО/") == "/media/БАЗАФОТО"
    assert module._prefix("/media/БАЗАФОТО") == "/media/БАЗАФОТО"


def test_plan_queries_only_the_old_root_and_shows_new_paths():
    module = _load()
    cur = Cursor(
        counts=[3, 0],
        samples=[[("PH_a", "/old/БАЗАФОТО/папка/a.JPG")], []],
    )

    report = module.plan(cur, "/old/БАЗАФОТО", "/new/БАЗАФОТО")

    assert report["tables"][0] == {
        "table": "photos",
        "rows": 3,
        "samples": [
            {
                "id": "PH_a",
                "from": "/old/БАЗАФОТО/папка/a.JPG",
                "to": "/new/БАЗАФОТО/папка/a.JPG",
            }
        ],
    }
    assert report["tables"][1]["rows"] == 0

    count_sql, params = cur.calls[0]
    assert "SELECT count(*) FROM public.photos" in count_sql
    assert params == ("/old/БАЗАФОТО/%",)


def test_apply_replaces_the_prefix_by_position_not_by_string_replace():
    module = _load()
    cur = Cursor(rowcounts=[27378, 27])

    changed = module.apply(cur, "/old/БАЗАФОТО", "/new/БАЗАФОТО")

    assert changed == {"photos": 27378, "video_assets": 27}

    sql, params = cur.calls[0]
    assert "UPDATE public.photos" in sql
    assert "SET source_path = %s || substr(source_path, %s)" in sql
    assert "WHERE source_path LIKE %s" in sql
    # substr начинается сразу после старого префикса, поэтому имя файла
    # с таким же текстом внутри не пострадает.
    assert params == (
        "/new/БАЗАФОТО",
        len("/old/БАЗАФОТО") + 1,
        "/old/БАЗАФОТО/%",
    )


def test_main_refuses_same_root_and_missing_target():
    module = _load()

    with pytest.raises(SystemExit):
        module.main(["--from", "/same", "--to", "/same"])

    with pytest.raises(SystemExit):
        module.main(["--from", "/old", "--to", "/нет/такого/пути"])


def test_main_requires_both_roots():
    module = _load()

    with pytest.raises(SystemExit):
        module.main(["--from", "/old"])

"""
Deleting a fingerprint: registry row, address link, files, safety guards.

A fake connection records the statements; the files live in a temp root.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from app.api import fingerprints as fp


class _Cursor:
    def __init__(self, captured, *, exists=True, active_jobs=0):
        self.captured = captured
        self.exists = exists
        self.active_jobs = active_jobs
        self.rowcount = 0
        self._last = ""

    def execute(self, sql, params=None):
        text = " ".join(sql.split())
        self.captured.append((text, params))
        self._last = text
        self.rowcount = 1

    def fetchone(self):
        if "count(*)" in self._last:
            return (self.active_jobs,)
        if "SELECT fingerprint_id" in self._last:
            return ("67_v33",) if self.exists else None
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _fake_connection(monkeypatch, captured, *, exists=True, active_jobs=0):
    class Connection:
        def cursor(self):
            return _Cursor(captured, exists=exists, active_jobs=active_jobs)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    @contextmanager
    def fake():
        yield Connection()

    monkeypatch.setattr(fp, "get_connection", fake)


def test_delete_removes_address_link_row_and_files(tmp_path, monkeypatch):
    root = tmp_path / "fingerprints"
    target = root / "67_v33"
    target.mkdir(parents=True)
    (target / "faiss.index").write_bytes(b"index")
    (target / "metadata.json").write_text("{}")

    captured = []
    _fake_connection(monkeypatch, captured)
    monkeypatch.setattr(fp, "FINGERPRINTS_ROOT", root)

    result = fp.delete_fingerprint("67_v33")

    assert result == {
        "fingerprint_id": "67_v33",
        "files_removed": 2,
        "files_total": 2,
        "error": None,
    }
    assert not target.exists()

    statements = [sql for sql, _ in captured]
    assert any("DELETE FROM public.address_fingerprints" in sql for sql in statements)
    assert any("DELETE FROM public.fingerprints" in sql for sql in statements)


def test_unknown_fingerprint_returns_none(tmp_path, monkeypatch):
    captured = []
    _fake_connection(monkeypatch, captured, exists=False)
    monkeypatch.setattr(fp, "FINGERPRINTS_ROOT", tmp_path)

    assert fp.delete_fingerprint("67_v33") is None


def test_active_recognition_blocks_deletion(tmp_path, monkeypatch):
    captured = []
    _fake_connection(monkeypatch, captured, active_jobs=1)
    monkeypatch.setattr(fp, "FINGERPRINTS_ROOT", tmp_path)

    with pytest.raises(fp.FingerprintError):
        fp.delete_fingerprint("67_v33")


def test_path_outside_the_root_is_rejected(tmp_path, monkeypatch):
    captured = []
    _fake_connection(monkeypatch, captured)
    monkeypatch.setattr(fp, "FINGERPRINTS_ROOT", tmp_path / "fingerprints")

    with pytest.raises(fp.FingerprintError):
        fp.delete_fingerprint("../etc")

from __future__ import annotations

import os
from pathlib import Path

from app.runs import log_store


def test_log_append_redacts_paths_and_credentials_and_is_private(tmp_path, monkeypatch):
    root = tmp_path / "logs"
    monkeypatch.setattr(log_store, "LOG_ROOT", root)
    monkeypatch.setattr(log_store, "MAX_LOG_BYTES", 4096)
    monkeypatch.setattr(log_store, "redact_absolute_paths", lambda value: value.replace("/secret/root", "[PATH]"))

    relative = log_store.append_lines(
        41,
        "QWEN",
        ["file /secret/root/photo.jpg: Authorization: Bearer abc123 api_key=xyz"],
    )

    assert relative == "41-qwen.log"
    content = log_store.read_log(relative)
    assert "[PATH]/photo.jpg" in content
    assert "Bearer [REDACTED]" in content
    assert "api_key=[REDACTED]" in content
    assert "/secret/root" not in content
    assert os.stat(root / relative).st_mode & 0o777 == 0o600


def test_log_is_bounded_and_rejects_escape_paths(tmp_path, monkeypatch):
    root = tmp_path / "logs"
    monkeypatch.setattr(log_store, "LOG_ROOT", root)
    monkeypatch.setattr(log_store, "MAX_LOG_BYTES", 64)

    relative = log_store.append_lines(5, "ingest", ["x" * 256])
    assert len(log_store.read_log(relative).encode("utf-8")) <= 64
    assert log_store.read_log("../outside.log") is None
    assert log_store.read_log(str(Path(relative).resolve())) is None


def test_read_log_rejects_symlink_escape(tmp_path, monkeypatch):
    root = tmp_path / "logs"
    root.mkdir()
    outside = tmp_path / "outside.log"
    outside.write_text("private", encoding="utf-8")
    (root / "7-qwen.log").symlink_to(outside)
    monkeypatch.setattr(log_store, "LOG_ROOT", root)

    assert log_store.read_log("7-qwen.log") is None

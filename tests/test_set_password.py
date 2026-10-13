"""
Tests for the set_password helper (scripts/set_password.py).

Only the env-file loader is exercised: no database, no prompts.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "set_password_script", REPO_ROOT / "scripts" / "set_password.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


script = _load_script()


def test_load_env_file_sets_missing_keys(monkeypatch, tmp_path):
    env_file = tmp_path / "scene.env"
    env_file.write_text(
        "# comment\n"
        "INGEST_DB_HOST=127.0.0.1\n"
        'INGEST_DB_PASSWORD="secret"\n'
        "EMPTY=\n"
        "garbage line\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("INGEST_DB_HOST", raising=False)
    monkeypatch.delenv("INGEST_DB_PASSWORD", raising=False)

    loaded = script.load_env_file(env_file)

    assert "INGEST_DB_HOST" in loaded
    assert "INGEST_DB_PASSWORD" in loaded
    assert script.os.environ["INGEST_DB_HOST"] == "127.0.0.1"
    # Quotes are stripped.
    assert script.os.environ["INGEST_DB_PASSWORD"] == "secret"


def test_load_env_file_does_not_override(monkeypatch, tmp_path):
    env_file = tmp_path / "scene.env"
    env_file.write_text("INGEST_DB_HOST=from-file\n", encoding="utf-8")

    monkeypatch.setenv("INGEST_DB_HOST", "from-shell")

    loaded = script.load_env_file(env_file)

    assert "INGEST_DB_HOST" not in loaded
    assert script.os.environ["INGEST_DB_HOST"] == "from-shell"


def test_load_env_file_missing_path(tmp_path):
    assert script.load_env_file(tmp_path / "nope.env") == []

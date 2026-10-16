"""
Tests for the schema migration runner (scripts/migrate.py).

Pure logic only: no PostgreSQL, no writes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_migrate():
    spec = importlib.util.spec_from_file_location(
        "migrate_script", REPO_ROOT / "scripts" / "migrate.py"
    )
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve the module namespace.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


migrate = _load_migrate()


def _write(directory: Path, name: str, body: str = "SELECT 1;") -> None:
    (directory / name).write_text(body, encoding="utf-8")


def test_discover_orders_and_skips_bootstrap(tmp_path):
    _write(tmp_path, "000_bootstrap.sql")
    _write(tmp_path, "002_b.sql")
    _write(tmp_path, "001_a.sql")

    migrations = migrate.discover_migrations(tmp_path)

    assert [m.version for m in migrations] == ["001_a", "002_b"]


def test_discover_checksum_is_content_based(tmp_path):
    _write(tmp_path, "001_a.sql", "SELECT 1;")
    first = migrate.discover_migrations(tmp_path)[0]

    _write(tmp_path, "001_a.sql", "SELECT 2;")
    second = migrate.discover_migrations(tmp_path)[0]

    assert first.checksum != second.checksum


def test_plan_splits_pending_and_drift(tmp_path):
    _write(tmp_path, "001_a.sql", "SELECT 1;")
    _write(tmp_path, "002_b.sql", "SELECT 2;")

    migrations = migrate.discover_migrations(tmp_path)
    applied = {migrations[0].version: migrations[0].checksum}

    pending, drift = migrate.plan(applied, migrations)

    assert [m.version for m in pending] == ["002_b"]
    assert drift == []


def test_plan_detects_checksum_drift(tmp_path):
    _write(tmp_path, "001_a.sql", "SELECT 1;")
    migrations = migrate.discover_migrations(tmp_path)

    applied = {migrations[0].version: "deadbeef"}

    pending, drift = migrate.plan(applied, migrations)

    assert pending == []
    assert [m.version for m in drift] == ["001_a"]


def test_repo_schema_files_are_discoverable():
    migrations = migrate.discover_migrations(REPO_ROOT / "schema")

    versions = [m.version for m in migrations]

    assert versions[0] == "001_ingest"
    assert "017_job_dedup" in versions
    assert "026_video_assets" in versions
    assert "027_video_playback_tickets" in versions
    assert "028_video_transcodes" in versions
    assert "029_photo_preview_jobs" in versions
    assert "030_video_trim" in versions
    # 000 is the superuser bootstrap step, never a migration.
    assert not any(v.startswith("000_") for v in versions)
    # Every file has a 64-char sha256 checksum.
    assert all(len(m.checksum) == 64 for m in migrations)


def test_video_trim_migration_preserves_job_types_and_operation_uniqueness():
    sql = (REPO_ROOT / "schema/030_video_trim.sql").read_text(encoding="utf-8")
    assert "DROP CONSTRAINT IF EXISTS video_derivatives_video_id_profile_source_sha256_key" in sql
    assert "CREATE UNIQUE INDEX ix_video_derivatives_operation" in sql
    assert "CREATE UNIQUE INDEX ix_video_trim_active_dedup" in sql
    assert "CREATE UNIQUE INDEX ix_video_storyboard_active_dedup" in sql
    for job_type in (
        "DINO_BATCH", "HYBRID_RUN", "QWEN_PHOTO", "NL_SEARCH", "INGEST_DIR",
        "MEDIA_SEARCH", "FINGERPRINT_BUILD", "VIDEO_TRANSCODE", "PHOTO_PREVIEW",
        "VIDEO_TRIM", "VIDEO_STORYBOARD",
    ):
        assert f"'{job_type}'" in sql

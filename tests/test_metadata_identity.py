"""
Metadata-v1 INGEST path: scheme switch, fast check and record construction.

No database: the registration SQL is exercised by the DB integration tests
when SCENE_TEST_DB is enabled; here the rules around it are pinned.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.ingest import metadata_pipeline
from app.ingest.identity_v2 import (
    IDENTITY_SCHEME,
    LEGACY_SCHEME,
    active_scheme,
    create_metadata_identity,
)
from app.ingest.metadata_integrity import check_file_metadata
from app.ingest.metadata_register import _same_content
from app.ingest.register import register_photo_metadata


def _jpeg(path: Path) -> Path:
    Image.new("RGB", (64, 48), (10, 20, 30)).save(path, format="JPEG")
    return path


# ---- scheme selection ------------------------------------------------------


def test_scheme_defaults_to_legacy(monkeypatch):
    monkeypatch.delenv("SCENE_IDENTITY_SCHEME", raising=False)
    assert active_scheme() == LEGACY_SCHEME


@pytest.mark.parametrize("value", ["metadata", "metadata-v1", "METADATA-V1"])
def test_scheme_can_be_switched(monkeypatch, value):
    monkeypatch.setenv("SCENE_IDENTITY_SCHEME", value)
    assert active_scheme() == IDENTITY_SCHEME


def test_unknown_scheme_is_rejected(monkeypatch):
    monkeypatch.setenv("SCENE_IDENTITY_SCHEME", "metadata-v2")

    with pytest.raises(ValueError):
        active_scheme()


# ---- fast check ------------------------------------------------------------


def test_fast_check_reads_header_without_hashing(tmp_path):
    path = _jpeg(tmp_path / "a.JPG")
    result = check_file_metadata(path)

    assert result["integrity_status"] == "VALID"
    assert result["sha256"] is None
    assert result["decoded"] is False
    assert result["width"] == 64 and result["height"] == 48
    assert result["size_bytes"] == path.stat().st_size


def test_fast_check_rejects_a_non_image(tmp_path):
    path = tmp_path / "a.JPG"
    path.write_bytes(b"not a jpeg")

    result = check_file_metadata(path)

    assert result["integrity_status"] == "INVALID"
    assert result["error"]


# ---- record ----------------------------------------------------------------


def test_metadata_record_has_no_content_hash(tmp_path):
    path = _jpeg(tmp_path / "a.JPG")
    identity = create_metadata_identity("123", "2025-01-01 10:00:00", "42", 100)

    record = register_photo_metadata(
        photo_id=identity.photo_id,
        source_path=str(path),
        filename=path.name,
        identity_hash=identity.identity_hash,
        container_format="JPEG",
        frame_count=1,
        width=64,
        height=48,
        size_bytes=100,
        taken_at="2025-01-01 10:00:00",
    )

    assert record.photo_id == identity.photo_id
    assert record.sha256 is None
    assert record.identity_hash == identity.identity_hash
    assert record.identity_scheme == IDENTITY_SCHEME


def test_metadata_record_rejects_a_bad_hash(tmp_path):
    path = _jpeg(tmp_path / "a.JPG")

    with pytest.raises(ValueError):
        register_photo_metadata(
            photo_id="PH_" + "a" * 24,
            source_path=str(path),
            filename=path.name,
            identity_hash="not-a-hash",
            container_format="JPEG",
            frame_count=1,
            width=64,
            height=48,
        )


# ---- pipeline branch -------------------------------------------------------


def test_complete_exif_uses_metadata_identity(tmp_path, monkeypatch):
    path = _jpeg(tmp_path / "a.JPG")
    integrity = check_file_metadata(path)
    integrity.update(
        {
            "taken_at": "2025-12-18 11:09:27",
            "exif_serial": "328055000461",
            "exif_subsec": "17",
        }
    )
    monkeypatch.setattr(
        metadata_pipeline, "check_file_metadata", lambda _path: integrity
    )

    record = metadata_pipeline.process_file_metadata(path)

    assert record.identity_scheme == IDENTITY_SCHEME
    assert record.sha256 is None
    assert record.identity_hash == create_metadata_identity(
        "328055000461", "2025-12-18 11:09:27", "17", integrity["size_bytes"]
    ).identity_hash


def test_incomplete_exif_falls_back_to_content_sha(tmp_path, monkeypatch):
    path = _jpeg(tmp_path / "a.JPG")
    integrity = check_file_metadata(path)
    integrity.update({"taken_at": None, "exif_serial": None, "exif_subsec": None})
    monkeypatch.setattr(
        metadata_pipeline, "check_file_metadata", lambda _path: integrity
    )

    record = metadata_pipeline.process_file_metadata(path)

    assert record.identity_scheme == LEGACY_SCHEME
    assert record.identity_hash is None
    assert record.sha256 is not None and len(record.sha256) == 64


# ---- collision guard -------------------------------------------------------


def test_same_content_guard_compares_both_files(tmp_path):
    left = tmp_path / "left.JPG"
    right = tmp_path / "right.JPG"
    left.write_bytes(b"same")
    right.write_bytes(b"same")
    other = tmp_path / "other.JPG"
    other.write_bytes(b"different")

    assert _same_content(str(left), str(right)) is True
    assert _same_content(str(left), str(other)) is False
    # A moved original cannot be compared; the identity match is accepted.
    assert _same_content(str(left), str(tmp_path / "missing.JPG")) is True

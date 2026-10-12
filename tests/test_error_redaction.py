"""
Error messages must not leak absolute local paths.

IngestFileResult.error and PreviewFileResult.error are user-facing; the
directory part of a path is server-local and should be stripped, while the
file name is kept for context.
"""

from __future__ import annotations

import hashlib

from app.core.errors import redact_paths
from app.ingest.integrity import check_file
from app.ingest.pipeline import run as ingest_run
from app.ingest.register import PhotoRecord
from app.preview.generator import generate_previews


def test_redact_paths_replaces_known_paths():
    text = "No such file or directory: '/data/photos/a.jpg'"
    assert redact_paths(text, "/data/photos/a.jpg") == (
        "No such file or directory: 'a.jpg'"
    )


def test_redact_paths_ignores_empty_and_unknown():
    assert redact_paths("boom", "", None) == "boom"
    assert redact_paths("boom", "/nope") == "boom"


def test_integrity_error_has_no_directory(tmp_path):
    path = tmp_path / "broken.JPG"
    path.write_bytes(b"not an image at all")

    result = check_file(path)

    assert result["integrity_status"] == "INVALID"
    assert str(tmp_path) not in result["error"]
    assert "broken.JPG" in result["error"]


def test_ingest_result_error_has_no_directory(tmp_path):
    bad = tmp_path / "broken.JPG"
    bad.write_bytes(b"not an image at all")

    result = ingest_run(tmp_path, workers=1)

    assert result.counters["INVALID"] == 1
    invalid = [r for r in result.results if r.status == "INVALID"][0]
    assert str(tmp_path) not in invalid.error
    assert "broken.JPG" in invalid.error


def test_preview_error_has_no_directory(tmp_path):
    record = PhotoRecord(
        photo_id="PH_" + "3" * 24,
        source_path=str(tmp_path / "missing.JPG"),
        filename="missing.JPG",
        sha256=hashlib.sha256(b"x").hexdigest(),
        container_format="JPEG",
        frame_count=1,
        width=64,
        height=48,
    )

    result = generate_previews(
        record=record,
        preview_root=tmp_path / "preview",
        small_size=32,
        middle_size=64,
    )

    assert result.small.action == "ERROR"
    assert str(tmp_path) not in result.small.error

"""
Unit tests for app.ingest.integrity.

Only .jpg/.jpeg with JPEG/MPO containers are accepted.
The source file is read-only; these tests never modify inputs.
"""

from pathlib import Path

from PIL import Image

from app.ingest.integrity import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_FORMATS,
    calculate_sha256,
    check_file,
    discover_files,
)


def test_valid_jpeg_reports_full_integrity(make_jpeg, sha256_of):
    path = make_jpeg("shot.JPG", size=(20, 10))

    result = check_file(path)

    assert result["integrity_status"] == "VALID"
    assert result["error"] is None
    assert result["decoded"] is True
    assert result["extension_valid"] is True
    assert result["container_format"] == "JPEG"
    assert (result["width"], result["height"]) == (20, 10)
    assert result["frame_count"] == 1
    assert result["size_bytes"] == path.stat().st_size
    assert result["sha256"] == sha256_of(path) == calculate_sha256(path)
    assert result["source_path"] == str(path)
    assert result["filename"] == "shot.JPG"


def test_missing_file_is_invalid(tmp_path):
    result = check_file(tmp_path / "missing.JPG")

    assert result["integrity_status"] == "INVALID"
    assert result["error"] is not None
    assert result["sha256"] is None


def test_unsupported_extension_is_invalid(tmp_path):
    path = tmp_path / "photo.png"
    Image.new("RGB", (4, 4)).save(path, format="PNG")

    result = check_file(path)

    assert result["extension_valid"] is False
    assert result["integrity_status"] == "INVALID"
    assert "Unsupported extension" in result["error"]


def test_wrong_container_behind_jpg_extension_is_invalid(tmp_path):
    # A real PNG file that only pretends to be a .jpg.
    path = tmp_path / "fake.JPG"
    Image.new("RGB", (4, 4)).save(path, format="PNG")

    result = check_file(path)

    assert result["integrity_status"] == "INVALID"
    assert result["sha256"] is not None  # hashing happened before decode
    assert result["error"] is not None


def test_corrupt_jpeg_is_invalid(tmp_path):
    path = tmp_path / "broken.JPG"
    path.write_bytes(b"this is definitely not a JPEG")

    result = check_file(path)

    assert result["integrity_status"] == "INVALID"
    assert result["decoded"] is False
    assert result["error"] is not None


def test_discover_files_is_non_recursive_and_case_insensitive(tmp_path):
    (tmp_path / "a.JPG").write_bytes(b"x")
    (tmp_path / "b.jpeg").write_bytes(b"x")
    (tmp_path / "c.png").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")

    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "d.JPG").write_bytes(b"x")

    discovered = discover_files(tmp_path)

    assert discovered == sorted([tmp_path / "a.JPG", tmp_path / "b.jpeg"])


def test_supported_constants_are_jpeg_only():
    assert SUPPORTED_EXTENSIONS == {".jpg", ".jpeg"}
    assert SUPPORTED_FORMATS == {"JPEG", "MPO"}
    assert ".png" not in SUPPORTED_EXTENSIONS

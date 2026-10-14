"""
ZIP download of a selection (app/api/archive.py, POST /v1/photos/archive).

Building an archive is a pure operation and is tested with real files in a
temporary folder; the endpoint's guards are checked without touching the
database.
"""

from __future__ import annotations

import zipfile

import pytest
from fastapi.testclient import TestClient

from app.api import archive
from app.api import routes
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---- names ----


def test_safe_archive_name_never_keeps_a_path():
    assert archive.safe_archive_name("../../etc/passwd", "x.jpg") == "passwd"
    assert archive.safe_archive_name("C:\\win\\photo.jpg", "x.jpg") == "photo.jpg"
    # Only the last segment survives, whatever separators were used.
    assert archive.safe_archive_name("/tmp/", "fallback.jpg") == "tmp"
    # Nothing usable left -> the fallback.
    assert archive.safe_archive_name("...", "fallback.jpg") == "fallback.jpg"
    assert archive.safe_archive_name(None, "fallback.jpg") == "fallback.jpg"


def test_safe_archive_name_shortens_but_keeps_the_extension():
    result = archive.safe_archive_name("a" * 300 + ".jpg", "x.jpg")

    assert len(result) <= archive.MAX_NAME_LENGTH
    assert result.endswith(".jpg")


def test_unique_name_settles_collisions():
    used: set[str] = set()

    assert archive.unique_name("a.jpg", used) == "a.jpg"
    assert archive.unique_name("a.jpg", used) == "a (2).jpg"
    assert archive.unique_name("a.jpg", used) == "a (3).jpg"

    # A name without an extension keeps being readable.
    plain: set[str] = set()

    assert archive.unique_name("a", plain) == "a"
    assert archive.unique_name("a", plain) == "a (2)"


# ---- building ----


def test_build_archive_packs_the_files(tmp_path):
    first = tmp_path / "one.jpg"
    second = tmp_path / "two.jpg"

    first.write_bytes(b"first")
    second.write_bytes(b"second")

    buffer, total = archive.build_archive(
        [(first, "один.jpg"), (second, "один.jpg")]
    )

    try:
        assert total == 11

        with zipfile.ZipFile(buffer) as packed:
            assert sorted(packed.namelist()) == ["один (2).jpg", "один.jpg"]
            assert packed.read("один.jpg") == b"first"
    finally:
        buffer.close()


def test_build_archive_refuses_an_empty_selection():
    with pytest.raises(archive.ArchiveError):
        archive.build_archive([])


def test_build_archive_reports_a_missing_file(tmp_path):
    with pytest.raises(archive.ArchiveError):
        archive.build_archive([(tmp_path / "nope.jpg", "nope.jpg")])


# ---- endpoint ----


def test_archive_needs_a_selection():
    response = client.post("/api/v1/photos/archive", json={"items": []})

    assert response.status_code == 400


def test_archive_refuses_an_oversized_selection():
    """The request schema caps the list; the route checks again as a backstop."""

    items = [
        {"photo_id": f"PH_{index:024x}"}
        for index in range(archive.MAX_ITEMS + 1)
    ]

    response = client.post("/api/v1/photos/archive", json={"items": items})

    assert response.status_code == 422


def test_archive_needs_configured_originals(monkeypatch):
    monkeypatch.setattr(routes, "ORIGINALS_ROOTS", [])

    response = client.post(
        "/api/v1/photos/archive",
        json={"items": [{"photo_id": "PH_" + "a" * 24}]},
    )

    assert response.status_code == 503

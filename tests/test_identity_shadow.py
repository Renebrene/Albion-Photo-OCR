"""
Metadata identity (metadata-v1) and its shadow log.

No database and no real photos: the identity is a pure function, and the log
writer is driven through environment variables and a temporary file.
"""

from __future__ import annotations

import json

from app.ingest.identity_v2 import (
    create_metadata_identity,
    metadata_identity_hash,
)
from app.ingest.integrity import read_identity_metadata
from app.ingest.shadow import record_shadow, shadow_enabled

INTEGRITY = {
    "filename": "81_041.JPG",
    "size_bytes": 7_624_268,
    "taken_at": "2025-12-18 11:09:27",
    "exif_serial": "328055000461",
    "exif_subsec": "17",
}


# ---- metadata identity -----------------------------------------------------


def test_identity_is_deterministic_and_well_formed():
    first = create_metadata_identity("328055000461", "2025-12-18 11:09:27", "17", 7_624_268)
    second = create_metadata_identity("328055000461", "2025-12-18 11:09:27", "17", 7_624_268)

    assert first == second
    assert first.photo_id.startswith("PH_")
    assert len(first.photo_id) == 3 + 24
    assert first.complete is True


def test_file_name_and_path_are_not_part_of_the_key():
    # The function receives no name at all: two copies share the identity.
    assert metadata_identity_hash(
        "328055000461", "2025-12-18 11:09:27", "17", 7_624_268
    ) == metadata_identity_hash(
        "328055000461", "2025-12-18 11:09:27", "17", 7_624_268
    )


def test_every_part_of_the_key_changes_the_id():
    base = create_metadata_identity(
        "328055000461", "2025-12-18 11:09:27", "17", 7_624_268
    ).photo_id

    variants = [
        ("328055000462", "2025-12-18 11:09:27", "17", 7_624_268),
        ("328055000461", "2025-12-18 11:09:28", "17", 7_624_268),
        ("328055000461", "2025-12-18 11:09:27", "18", 7_624_268),
        # Size is required: without it the corpus already had a real
        # collision with different content.
        ("328055000461", "2025-12-18 11:09:27", "17", 7_624_269),
    ]

    ids = {create_metadata_identity(*values).photo_id for values in variants}

    assert base not in ids
    assert len(ids) == len(variants)


def test_missing_metadata_is_incomplete_but_deterministic():
    identity = create_metadata_identity(None, None, None, 123)

    assert identity.complete is False
    assert identity.photo_id == create_metadata_identity("", "", "", 123).photo_id


# ---- EXIF extraction -------------------------------------------------------


class _FakeExif:
    def __init__(self, values):
        self.values = values

    def get(self, key):
        return self.values.get(key)

    def get_ifd(self, key):
        return self.values.get("sub") or {}


class _FakeImage:
    def __init__(self, values):
        self.exif = _FakeExif(values)

    def getexif(self):
        return self.exif


def test_identity_metadata_reads_serial_and_subseconds():
    image = _FakeImage(
        {
            "sub": {
                0xA431: "328055000461",
                0x9291: "17",
            }
        }
    )

    assert read_identity_metadata(image) == {
        "exif_serial": "328055000461",
        "exif_subsec": "17",
    }


def test_identity_metadata_is_best_effort():
    assert read_identity_metadata(_FakeImage({})) == {
        "exif_serial": None,
        "exif_subsec": None,
    }


# ---- shadow log ------------------------------------------------------------


def test_shadow_is_off_by_default(monkeypatch, tmp_path):
    log = tmp_path / "shadow.jsonl"
    monkeypatch.delenv("SCENE_IDENTITY_SHADOW", raising=False)
    monkeypatch.setenv("SCENE_IDENTITY_SHADOW_LOG", str(log))

    assert shadow_enabled() is False
    assert record_shadow("a.JPG", "a" * 64, "PH_" + "a" * 24, INTEGRITY) is False
    assert not log.exists()


def test_shadow_appends_both_ids(monkeypatch, tmp_path):
    log = tmp_path / "logs" / "shadow.jsonl"
    monkeypatch.setenv("SCENE_IDENTITY_SHADOW", "1")
    monkeypatch.setenv("SCENE_IDENTITY_SHADOW_LOG", str(log))

    assert record_shadow(
        "/photos/81_041.JPG", "a" * 64, "PH_" + "a" * 24, INTEGRITY
    ) is True
    assert record_shadow(
        "/photos/82_061.JPG", "b" * 64, "PH_" + "b" * 24, INTEGRITY
    ) is True

    lines = [json.loads(line) for line in log.read_text().splitlines()]

    assert len(lines) == 2
    first = lines[0]
    assert first["sha_photo_id"] == "PH_" + "a" * 24
    assert first["v2_photo_id"] == create_metadata_identity(
        "328055000461", "2025-12-18 11:09:27", "17", 7_624_268
    ).photo_id
    assert first["scheme"] == "metadata-v1"
    assert first["complete"] is True
    assert first["serial"] == "328055000461"
    assert first["size_bytes"] == 7_624_268


def test_shadow_never_fails_ingest(monkeypatch, tmp_path):
    # A directory cannot be opened for append: the writer must report False.
    monkeypatch.setenv("SCENE_IDENTITY_SHADOW", "1")
    monkeypatch.setenv("SCENE_IDENTITY_SHADOW_LOG", str(tmp_path))

    assert record_shadow("a.JPG", "a" * 64, "PH_" + "a" * 24, INTEGRITY) is False

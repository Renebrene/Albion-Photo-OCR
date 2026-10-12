"""
Unit tests for app.ingest.register.

PhotoRecord is an immutable record assembled from validated
INGEST stages. Validation must reject missing/invalid fields.
"""

import dataclasses

import pytest

from app.ingest.register import PhotoRecord, register_photo

VALID = {
    "photo_id": "PH_c4a49077cb428c56ad682a36",
    "source_path": "/read/only/source.jpg",
    "filename": "source.jpg",
    "sha256": "c4a49077cb428c56ad682a36fcbd4c6d17e271a5af05fd990481bd33ce1520a6",
    "container_format": "JPEG",
    "frame_count": 1,
    "width": 4032,
    "height": 3024,
}


def test_register_photo_builds_record():
    record = register_photo(**VALID)

    assert isinstance(record, PhotoRecord)
    assert record.photo_id == VALID["photo_id"]
    assert record.sha256 == VALID["sha256"]
    assert record.container_format == "JPEG"


def test_photo_record_is_frozen():
    record = register_photo(**VALID)

    with pytest.raises(dataclasses.FrozenInstanceError):
        record.width = 1


def test_mpo_container_is_accepted():
    record = register_photo(**{**VALID, "container_format": "MPO", "frame_count": 2})
    assert record.container_format == "MPO"
    assert record.frame_count == 2


@pytest.mark.parametrize("field", ["photo_id", "source_path", "filename", "sha256"])
def test_missing_required_string_is_rejected(field):
    with pytest.raises(ValueError):
        register_photo(**{**VALID, field: ""})


@pytest.mark.parametrize("container_format", ["PNG", "GIF", "jpeg", "", "HEIC"])
def test_unsupported_container_format_is_rejected(container_format):
    with pytest.raises(ValueError):
        register_photo(**{**VALID, "container_format": container_format})


@pytest.mark.parametrize(
    "overrides",
    [
        {"frame_count": 0},
        {"frame_count": -1},
        {"width": 0},
        {"height": 0},
        {"width": -5},
        {"height": -5},
    ],
)
def test_invalid_dimensions_and_frames_are_rejected(overrides):
    with pytest.raises(ValueError):
        register_photo(**{**VALID, **overrides})

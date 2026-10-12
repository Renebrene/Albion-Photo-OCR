"""
Unit tests for app.ingest.identity.

photo_id must depend only on the physical SHA-256:
PH_ + first 24 lowercase hex characters.
"""

import pytest

from app.ingest.identity import (
    PHOTO_ID_HASH_LENGTH,
    create_identity,
    photo_id_from_sha256,
    validate_sha256,
)

VALID_SHA = "c4a49077cb428c56ad682a36fcbd4c6d17e271a5af05fd990481bd33ce1520a6"


def test_photo_id_uses_first_24_hex_characters():
    assert photo_id_from_sha256(VALID_SHA) == "PH_c4a49077cb428c56ad682a36"
    assert len(photo_id_from_sha256(VALID_SHA)) == len("PH_") + 24
    assert PHOTO_ID_HASH_LENGTH == 24


def test_validate_sha256_normalizes_case_and_whitespace():
    assert validate_sha256("  " + VALID_SHA.upper() + "\n") == VALID_SHA


def test_create_identity_keeps_full_digest():
    identity = create_identity(VALID_SHA.upper())

    assert identity.photo_id == "PH_c4a49077cb428c56ad682a36"
    assert identity.sha256 == VALID_SHA


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "abc",
        "z" * 64,          # not hexadecimal
        "a" * 63,          # too short
        "a" * 65,          # too long
        "g" * 64,          # invalid hex character
    ],
)
def test_invalid_sha256_is_rejected(bad):
    with pytest.raises(ValueError):
        validate_sha256(bad)

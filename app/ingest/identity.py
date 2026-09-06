from __future__ import annotations

import re
from dataclasses import dataclass


PHOTO_ID_PREFIX = "PH"
PHOTO_ID_HASH_LENGTH = 24

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PhotoIdentity:
    photo_id: str
    sha256: str


def validate_sha256(sha256: str) -> str:
    value = sha256.strip().lower()

    if not SHA256_RE.fullmatch(value):
        raise ValueError(
            "Invalid SHA-256: expected 64 hexadecimal characters"
        )

    return value


def photo_id_from_sha256(sha256: str) -> str:
    """
    Create a deterministic photo_id from the SHA-256
    of the original physical source file.
    """
    sha256 = validate_sha256(sha256)

    return f"{PHOTO_ID_PREFIX}_{sha256[:PHOTO_ID_HASH_LENGTH]}"


def create_identity(sha256: str) -> PhotoIdentity:
    sha256 = validate_sha256(sha256)

    return PhotoIdentity(
        photo_id=photo_id_from_sha256(sha256),
        sha256=sha256,
    )

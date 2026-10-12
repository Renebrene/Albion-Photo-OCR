"""
Shared pytest configuration.

These tests exercise pure logic only: no PostgreSQL, no model loading,
no network, and no writes outside pytest's temporary directories.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from PIL import Image

# Make the application package importable when pytest is run
# directly from the repository root without an editable install.
ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def make_jpeg(tmp_path):
    """
    Create a small valid JPEG file and return its path.

    The bytes are deterministic, so the SHA-256 can be
    recomputed by the test using the same hashlib routine.
    """

    def _make(name: str = "photo.JPG", size=(16, 12)) -> Path:
        path = tmp_path / name
        image = Image.new("RGB", size, color=(120, 60, 30))
        image.save(path, format="JPEG")
        return path

    return _make


@pytest.fixture
def sha256_of():
    """Return the lowercase SHA-256 hex digest of a file, 1 MiB chunks."""

    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return _digest

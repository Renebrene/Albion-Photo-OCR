"""
Shared pytest configuration.

Most tests exercise pure logic only: no PostgreSQL, no model loading, no
network, and no writes outside pytest's temporary directories. The few
fixtures that do touch PostgreSQL (`probe_fingerprints`) are opt-in and clean
up after themselves.
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


@pytest.fixture(autouse=True)
def _open_api_for_tests(monkeypatch):
    """
    Keep the API open for the test session.

    Authentication is fail-closed by default in production; tests opt into the
    old open behaviour explicitly, and individual tests can still enable auth
    by setting SCENE_API_TOKENS or removing SCENE_AUTH_REQUIRED.
    """

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")


@pytest.fixture
def probe_fingerprints():
    """
    Two throwaway registry rows for tests that write human fields.

    `set_address()`/`update_address()`/`update_fingerprint()` and the address
    import all rewrite `fingerprints.display_name` and delete
    `address_fingerprints` rows, so such a test MUST work on its own row. While
    they picked the first registry entry, every run wiped the name and the
    address of the real `76_v33`. The rows are removed afterwards (the mapping
    goes with them by CASCADE).
    """

    from app.ingest.database import get_connection

    ids = ["998_v33", "999_v33"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.fingerprints WHERE fingerprint_id = ANY(%s)",
                (ids,),
            )

            for fingerprint_id in ids:
                cur.execute(
                    "INSERT INTO public.fingerprints (fingerprint_id, display_name) "
                    "VALUES (%s, '')",
                    (fingerprint_id,),
                )

    yield ids

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.fingerprints WHERE fingerprint_id = ANY(%s)",
                (ids,),
            )


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

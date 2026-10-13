"""
Tests for the original-file endpoint containment (fail-closed allowed roots).

Needs PostgreSQL for the probe photo; path checks and the scope check do not.
"""

from __future__ import annotations

import hashlib
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api import routes as api_routes
from app.api.main import app
from app.ingest.database import get_connection

client = TestClient(app, raise_server_exceptions=False)

PROBE_ID = "PH_" + "7" * 24


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photos')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="ingest DB not available (INGEST_DB_*)",
)


def _cleanup() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.photos WHERE photo_id = %s", (PROBE_ID,))


def test_no_roots_configured_refuses(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:originals")
    monkeypatch.setattr(api_routes, "ORIGINALS_ROOTS", [])

    response = client.get(
        f"/api/v1/photos/{PROBE_ID}/original",
        headers={"Authorization": "Bearer tok"},
    )
    # Refused before any DB access: originals are not configured.
    assert response.status_code == 503


@requires_db
def test_original_only_within_allowed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:originals")
    headers = {"Authorization": "Bearer tok"}

    _cleanup()

    inside = tmp_path / "inside"
    outside = tmp_path / "outside"
    inside.mkdir()
    outside.mkdir()

    allowed_file = inside / "ok.jpg"
    Image.new("RGB", (8, 8), (10, 120, 60)).save(allowed_file, format="JPEG")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.photos (
                        photo_id, source_path, filename, sha256,
                        container_format, frame_count, width, height
                    )
                    VALUES (%s, %s, 'ok.jpg', %s, 'JPEG', 1, 8, 8)
                    """,
                    (
                        PROBE_ID,
                        str(allowed_file),
                        hashlib.sha256(PROBE_ID.encode()).hexdigest(),
                    ),
                )

        # A root that contains the file -> served.
        monkeypatch.setattr(api_routes, "ORIGINALS_ROOTS", [inside])
        ok = client.get(f"/api/v1/photos/{PROBE_ID}/original", headers=headers)
        assert ok.status_code == 200
        assert ok.headers["content-type"].startswith("image/jpeg")

        # A root that does NOT contain the file -> refused (404).
        monkeypatch.setattr(api_routes, "ORIGINALS_ROOTS", [outside])
        blocked = client.get(
            f"/api/v1/photos/{PROBE_ID}/original", headers=headers
        )
        assert blocked.status_code == 404
    finally:
        _cleanup()


@requires_db
def test_original_symlink_escape_is_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:originals")
    headers = {"Authorization": "Bearer tok"}

    _cleanup()

    root = tmp_path / "volume"
    root.mkdir()
    secret = tmp_path / "secret.jpg"
    Image.new("RGB", (8, 8), (1, 2, 3)).save(secret, format="JPEG")

    link = root / "escape.jpg"
    link.symlink_to(secret)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.photos (
                        photo_id, source_path, filename, sha256,
                        container_format, frame_count, width, height
                    )
                    VALUES (%s, %s, 'escape.jpg', %s, 'JPEG', 1, 8, 8)
                    """,
                    (
                        PROBE_ID,
                        str(link),
                        hashlib.sha256(PROBE_ID.encode()).hexdigest(),
                    ),
                )

        monkeypatch.setattr(api_routes, "ORIGINALS_ROOTS", [root])

        response = client.get(
            f"/api/v1/photos/{PROBE_ID}/original", headers=headers
        )
        # Resolved path escapes the allowed root -> refused.
        assert response.status_code == 404
    finally:
        _cleanup()

"""
Tests for the read-only web API (app.api).

Health and input validation run everywhere; endpoints that need PostgreSQL
skip unless INGEST_DB_* is configured.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photos')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="integration PostgreSQL is not configured (INGEST_DB_*)",
)

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_photo_id_returns_404():
    assert client.get("/api/v1/photos/not-an-id").status_code == 404


def test_invalid_preview_id_returns_404():
    response = client.get("/api/v1/photos/PH_zzz/previews/small")
    assert response.status_code == 404


def test_unknown_preview_size_returns_404():
    response = client.get(
        "/api/v1/photos/PH_" + "0" * 24 + "/previews/large"
    )
    assert response.status_code == 404


def test_limit_is_bounded():
    response = client.get("/api/v1/photos?limit=999")
    assert response.status_code == 422


@requires_db
def test_list_photos_returns_page():
    response = client.get("/api/v1/photos?limit=5")
    assert response.status_code == 200

    body = response.json()
    assert "items" in body and "next_cursor" in body
    assert len(body["items"]) <= 5

    for item in body["items"]:
        assert item["photo_id"].startswith("PH_")
        assert item["container_format"] in {"JPEG", "MPO"}


@requires_db
def test_cursor_pagination_is_stable():
    first = client.get("/api/v1/photos?limit=3").json()
    if not first["next_cursor"]:
        pytest.skip("corpus too small for pagination")

    second = client.get(
        f"/api/v1/photos?limit=3&cursor={first['next_cursor']}"
    ).json()

    first_ids = {item["photo_id"] for item in first["items"]}
    second_ids = {item["photo_id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


@requires_db
def test_list_dino_batches():
    response = client.get("/api/v1/batches/dino?limit=5")
    assert response.status_code == 200

    body = response.json()
    assert "items" in body and "next_cursor" in body
    for item in body["items"]:
        assert item["status"] in {"PENDING", "RUNNING", "DONE", "FAILED"}
        assert item["run_type"] in {"NORMAL", "FORCE_RERUN"}


@requires_db
def test_unknown_dino_batch_returns_404():
    assert client.get("/api/v1/batches/dino/999999").status_code == 404


@requires_db
def test_unknown_dino_batch_runs_returns_404():
    assert (
        client.get("/api/v1/batches/dino/999999/runs").status_code == 404
    )


@requires_db
def test_list_hybrid_runs():
    response = client.get("/api/v1/hybrid/runs?limit=5")
    assert response.status_code == 200
    assert "items" in response.json()


@requires_db
def test_address_comes_from_recognition():
    """Photo address is the DINO/HYBRID result, not QWEN metadata."""

    import datetime
    import hashlib

    from app.ingest.database import get_connection

    photo_id = "PH_" + "7" * 24
    filename = "TESTADDR_01.JPG"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photos (
                    photo_id, source_path, filename, sha256,
                    container_format, frame_count, width, height
                )
                VALUES (%s, %s, %s, %s, 'JPEG', 1, 10, 10)
                """,
                (
                    photo_id,
                    f"/tmp/{filename}",
                    filename,
                    hashlib.sha256(photo_id.encode()).hexdigest(),
                ),
            )
            cur.execute(
                """
                INSERT INTO public.dino_batches (
                    run_type, status, total_count, completed_count, failed_count
                )
                VALUES ('FORCE_RERUN', 'DONE', 1, 1, 0)
                RETURNING batch_id
                """
            )
            batch_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO public.dino_runs (
                    batch_id, photo_id, run_type, status,
                    dino_best_id, finished_at
                )
                VALUES (%s, %s, 'FORCE_RERUN', 'DONE', '78_v33', CURRENT_TIMESTAMP)
                """,
                (batch_id, photo_id),
            )

    try:
        body = client.get(f"/api/v1/photos?q={filename}").json()
        assert body["items"], "photo not returned"
        assert body["items"][0]["address"] == "78_v33"
        assert body["items"][0]["client"] is None
    finally:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.dino_batches WHERE batch_id = %s",
                    (batch_id,),
                )
                cur.execute(
                    "DELETE FROM public.photos WHERE photo_id = %s",
                    (photo_id,),
                )

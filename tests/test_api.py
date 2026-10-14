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


def test_invalid_photo_details_id_returns_404():
    assert client.get("/api/v1/photos/not-an-id/details").status_code == 404


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
def test_address_and_client_facets():
    addresses = client.get("/api/v1/addresses").json()
    clients = client.get("/api/v1/clients").json()

    assert "items" in addresses
    assert "items" in clients

    for item in addresses["items"]:
        # The recognised id is what the filter sends; `name` is what the panel
        # shows (the alias of the fingerprint's address, or the id).
        assert set(item) == {"address", "name", "count"}
    for item in clients["items"]:
        assert set(item) == {"client", "count"}


@requires_db
def test_address_filter_is_built_from_the_fingerprints():
    """
    The «Адреса» panel lists fingerprints by name, not raw verdict ids: every
    active fingerprint is present (even one without recognised photos) and the
    list is ordered by the displayed name.
    """

    addresses = client.get("/api/v1/addresses").json()["items"]
    registry = client.get("/api/v1/fingerprints/registry").json()["items"]

    if not registry:
        pytest.skip("the fingerprint registry is empty")

    listed = {item["address"] for item in addresses}

    for item in registry:
        if item["active"]:
            assert item["fingerprint_id"] in listed

    for item in addresses:
        assert item["name"]
        assert item["count"] >= 0

    names = [item["name"].casefold() for item in addresses]
    assert names == sorted(names)


@requires_db
def test_stats_for_the_status_bar():
    """Counts for the footer: photos, addresses, clients, last upload."""

    response = client.get("/api/v1/stats")

    assert response.status_code == 200

    body = response.json()

    assert set(body) == {"photos", "addresses", "clients", "last_photo_at"}
    assert body["photos"] >= 1
    assert body["addresses"] >= 0
    assert body["clients"] >= 0
    # The corpus has photos, so there is a date of the last one.
    assert body["last_photo_at"]


@requires_db
def test_photos_date_filter():
    all_time = client.get(
        "/api/v1/photos?date_from=2000-01-01&date_to=2099-12-31&limit=5"
    ).json()
    assert len(all_time["items"]) >= 1

    future = client.get("/api/v1/photos?date_from=2099-01-01").json()
    assert future["items"] == []


@requires_db
def test_search_matches_filename_substring():
    """Multi-field `q` still matches on the filename."""

    first = client.get("/api/v1/photos?limit=1").json()
    if not first["items"]:
        pytest.skip("corpus is empty")

    filename = first["items"][0]["filename"]
    needle = filename.split(".")[0][:8]
    if len(needle) < 3:
        pytest.skip("filename too short to search")

    body = client.get(f"/api/v1/photos?q={needle}").json()
    assert any(item["photo_id"] == first["items"][0]["photo_id"] for item in body["items"])


@requires_db
def test_multiple_addresses_filter_or_semantics():
    """Several `address` params combine with OR (multi-select panels)."""

    # The panel lists every fingerprint, including ones the corpus has no
    # recognised photo for; this test needs two that actually have photos.
    with_photos = [
        item
        for item in client.get("/api/v1/addresses").json()["items"]
        if item["count"] > 0
    ]

    if len(with_photos) < 2:
        pytest.skip("fewer than two addresses with photos in the corpus")

    first, second = with_photos[0]["address"], with_photos[1]["address"]
    body = client.get(
        f"/api/v1/photos?address={first}&address={second}&limit=100"
    ).json()

    assert body["items"], "no photos returned"
    for item in body["items"]:
        value = item["address"] or ""
        assert first in value or second in value


@requires_db
def test_photo_details_shape():
    first = client.get("/api/v1/photos?limit=1").json()
    if not first["items"]:
        pytest.skip("corpus is empty")

    photo_id = first["items"][0]["photo_id"]
    body = client.get(f"/api/v1/photos/{photo_id}/details").json()

    assert body["photo"]["photo_id"] == photo_id
    assert "qwen" in body  # may be null when QWEN has not run


@requires_db
def test_photo_details_unknown_photo_returns_404():
    response = client.get("/api/v1/photos/PH_" + "0" * 24 + "/details")
    assert response.status_code == 404


def test_system_info():
    data = client.get("/api/v1/system").json()
    assert data["cpu_count"] >= 1
    assert data["memory"]["total"] > 0
    assert "uptime_sec" in data
    assert "network" in data
    assert isinstance(data["temperatures"], list)


def test_fingerprints_endpoint():
    data = client.get("/api/v1/fingerprints").json()
    assert "items" in data
    for item in data["items"]:
        assert set(item) == {"id", "images", "dimension", "version", "model"}


@requires_db
def test_data_storage_stats():
    data = client.get("/api/v1/data/storage").json()
    assert set(data) == {
        "rows",
        "database_bytes",
        "previews",
        "fingerprints",
    }
    assert data["rows"]["photos"] >= 1
    assert data["database_bytes"] > 0


@requires_db
def test_data_export_json_has_no_paths():
    body = client.get("/api/v1/data/export?format=json").json()
    assert body["count"] == len(body["items"])

    for item in body["items"]:
        assert set(item) == {
            "photo_id",
            "filename",
            "width",
            "height",
            "container_format",
            "created_at",
            "address",
            "client",
            "brand",
            "category",
            "description",
            "tags",
        }
        assert "/" not in (item["filename"] or "")


@requires_db
def test_data_export_csv():
    response = client.get("/api/v1/data/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines()[0].startswith("photo_id,")


def test_data_export_rejects_unknown_format():
    assert client.get("/api/v1/data/export?format=xml").status_code == 422


@requires_db
def test_qwen_stats_shape():
    data = client.get("/api/v1/qwen/stats").json()
    assert "counts" in data and "failed_photo_ids" in data
    assert isinstance(data["failed_photo_ids"], list)
    for status, count in data["counts"].items():
        assert status in {"PENDING", "RUNNING", "DONE", "FAILED"}
        assert count >= 0


def test_qwen_only_failed_with_none_enqueues_nothing(monkeypatch):
    from app.api import repository

    monkeypatch.setattr(
        repository, "photo_ids_with_qwen_status", lambda status: []
    )
    response = client.post("/api/v1/jobs/qwen", json={"only_failed": True})
    assert response.status_code == 422


@requires_db
def test_last_run():
    data = client.get("/api/v1/runs/last").json()
    assert "jobs" in data
    assert "dino_batch" in data
    assert "hybrid_run" in data


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

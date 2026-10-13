"""
Tests for client alias normalization (schema 016, /v1/client-aliases).

Scope checks run everywhere; the lifecycle test needs PostgreSQL and creates a
throwaway photo + photo_qwen row it removes afterwards.
"""

from __future__ import annotations

import hashlib
import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.ingest.database import get_connection

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.client_aliases')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="client_aliases not available (INGEST_DB_* / schema 016)",
)

PROBE_ID = "PH_" + "9" * 24
PROBE_RAW = "__alias_probe_raw__"
PROBE_CANON = "__alias_probe_canonical__"


def _cleanup() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.client_aliases WHERE alias LIKE %s",
                ("__alias_probe%",),
            )
            cur.execute(
                "DELETE FROM public.photo_qwen WHERE photo_id = %s", (PROBE_ID,)
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = %s", (PROBE_ID,)
            )


def test_upsert_requires_collections_write(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.put(
        "/api/v1/client-aliases",
        json={"alias": "a", "canonical": "b"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_upsert_validates_body():
    assert (
        client.put("/api/v1/client-aliases", json={"alias": ""}).status_code
        == 422
    )


@requires_db
def test_alias_folds_clients_and_lifecycle():
    _cleanup()

    try:
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
                        PROBE_ID,
                        f"/tmp/{PROBE_RAW}.jpg",
                        f"{PROBE_RAW}.jpg",
                        hashlib.sha256(PROBE_ID.encode()).hexdigest(),
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO public.photo_qwen (photo_id, status, client)
                    VALUES (%s, 'DONE', %s)
                    """,
                    (PROBE_ID, PROBE_RAW),
                )

        # Before aliasing, the raw client is its own facet.
        raw_clients = [c["client"] for c in client.get("/api/v1/clients").json()["items"]]
        assert PROBE_RAW in raw_clients
        assert PROBE_CANON not in raw_clients

        created = client.put(
            "/api/v1/client-aliases",
            json={"alias": PROBE_RAW, "canonical": PROBE_CANON},
        )
        assert created.status_code == 200

        aliases = client.get("/api/v1/client-aliases").json()["items"]
        assert {"alias": PROBE_RAW, "canonical": PROBE_CANON} in aliases

        folded = client.get("/api/v1/clients").json()["items"]
        names = [c["client"] for c in folded]
        assert PROBE_CANON in names
        assert PROBE_RAW not in names

        # Filtering by the canonical client also matches the aliased row.
        filtered = client.get(
            f"/api/v1/photos?client={PROBE_CANON}"
        ).json()["items"]
        assert PROBE_ID in {item["photo_id"] for item in filtered}

        assert (
            client.delete(
                "/api/v1/client-aliases", params={"alias": PROBE_RAW}
            ).status_code
            == 200
        )
        assert (
            client.delete(
                "/api/v1/client-aliases", params={"alias": PROBE_RAW}
            ).status_code
            == 404
        )
    finally:
        _cleanup()

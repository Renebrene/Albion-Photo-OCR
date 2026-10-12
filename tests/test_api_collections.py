"""
Tests for collections / bookmarks (schema 009).

Scope checks run everywhere; lifecycle tests need PostgreSQL.
"""

from __future__ import annotations

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
                cur.execute("select to_regclass('public.collections')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="collections not available (INGEST_DB_* / schema 009)",
)


@pytest.fixture
def cleanup_collections():
    created: list[int] = []
    yield created

    if created:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.collections "
                    "WHERE collection_id = ANY(%s)",
                    (created,),
                )


def test_create_requires_collections_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/collections",
        json={"name": "x"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


@requires_db
def test_collection_lifecycle(cleanup_collections):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select photo_id from public.photos order by photo_id limit 2"
            )
            ids = [row[0] for row in cur.fetchall()]

    if len(ids) < 2:
        pytest.skip("not enough photos")

    created = client.post(
        "/api/v1/collections",
        json={"name": "Тест-подборка", "kind": "Моя", "scope": "photos"},
    )
    assert created.status_code == 201

    collection_id = created.json()["collection_id"]
    cleanup_collections.append(collection_id)

    added = client.post(
        f"/api/v1/collections/{collection_id}/members",
        json={"member_type": "photo", "values": ids},
    )
    assert added.status_code == 200
    assert added.json()["added"] == len(ids)

    items = client.get("/api/v1/collections").json()["items"]
    assert any(
        item["collection_id"] == collection_id and item["members"] == len(ids)
        for item in items
    )

    members = client.get(
        f"/api/v1/collections/{collection_id}/members"
    ).json()["items"]
    assert sorted(members) == sorted(ids)

    filtered = client.get(
        f"/api/v1/photos?collection_id={collection_id}"
    ).json()["items"]
    assert {item["photo_id"] for item in filtered} == set(ids)

    removed = client.post(
        f"/api/v1/collections/{collection_id}/members/remove",
        json={"member_type": "photo", "values": ids},
    )
    assert removed.json()["removed"] == len(ids)

    assert (
        client.delete(f"/api/v1/collections/{collection_id}").status_code == 200
    )
    assert (
        client.delete(f"/api/v1/collections/{collection_id}").status_code == 404
    )
    cleanup_collections.remove(collection_id)

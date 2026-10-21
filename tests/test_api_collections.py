"""
Tests for collections / bookmarks (schema 009).

Scope checks run everywhere; lifecycle tests need PostgreSQL.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api import repository
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


def _drop_test_users(names: list[str]) -> None:
    """Remove throwaway users together with their collections/searches."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.collections WHERE user_id IN "
                "(SELECT user_id::text FROM public.users WHERE name = ANY(%s))",
                (names,),
            )
            cur.execute(
                "DELETE FROM public.saved_searches WHERE user_id IN "
                "(SELECT user_id::text FROM public.users WHERE name = ANY(%s))",
                (names,),
            )
            cur.execute(
                "DELETE FROM public.users WHERE name = ANY(%s)", (names,)
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

    # The probe photos may not have a HYBRID verdict, so query the repository
    # without the grid's recognized_only filter.
    filtered, _ = repository.list_photos(
        limit=100,
        collection_id=collection_id,
        recognized_only=False,
    )
    assert {item.photo_id for item in filtered} == set(ids)

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


@requires_db
def test_collections_are_isolated_per_user(monkeypatch):
    """A bookmark belongs to its owner: others neither see nor delete it."""

    # Enforce scopes here so the guest's write attempt really is rejected.
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "1")

    from app.users import database as users_db

    names = ["__col_owner__", "__col_other__", "__col_guest__"]
    _drop_test_users(names)

    try:
        owner = users_db.create_user(name=names[0], role="Менеджер")
        other = users_db.create_user(name=names[1], role="Менеджер")
        guest = users_db.create_user(name=names[2], role="Гость")

        owner_h = {
            "Authorization": f"Bearer {users_db.create_session(owner['user_id'])}"
        }
        other_h = {
            "Authorization": f"Bearer {users_db.create_session(other['user_id'])}"
        }
        guest_h = {
            "Authorization": f"Bearer {users_db.create_session(guest['user_id'])}"
        }

        created = client.post(
            "/api/v1/collections",
            json={"name": "Личная подборка", "kind": "Моя"},
            headers=owner_h,
        )
        assert created.status_code == 201
        collection_id = created.json()["collection_id"]

        owner_items = client.get("/api/v1/collections", headers=owner_h).json()[
            "items"
        ]
        assert any(
            item["collection_id"] == collection_id for item in owner_items
        )

        # Another manager does not see it and cannot touch it.
        other_items = client.get("/api/v1/collections", headers=other_h).json()[
            "items"
        ]
        assert all(
            item["collection_id"] != collection_id for item in other_items
        )
        assert (
            client.get(
                f"/api/v1/collections/{collection_id}/members", headers=other_h
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/collections/{collection_id}", headers=other_h
            ).status_code
            == 404
        )

        # A guest (read only) sees an empty bookmark list and cannot create.
        assert (
            client.get("/api/v1/collections", headers=guest_h).json()["items"]
            == []
        )
        assert (
            client.post(
                "/api/v1/collections", json={"name": "nope"}, headers=guest_h
            ).status_code
            == 403
        )

        # Filtering the grid by somebody else's collection yields nothing.
        filtered = client.get(
            f"/api/v1/photos?collection_id={collection_id}", headers=other_h
        ).json()["items"]
        assert filtered == []

        assert (
            client.delete(
                f"/api/v1/collections/{collection_id}", headers=owner_h
            ).status_code
            == 200
        )
    finally:
        _drop_test_users(names)

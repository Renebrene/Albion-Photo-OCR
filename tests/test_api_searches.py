"""
Tests for saved searches / bookmarked filters (schema 011).

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
                cur.execute("select to_regclass('public.saved_searches')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="saved_searches not available (INGEST_DB_* / schema 011)",
)


@pytest.fixture
def cleanup_searches():
    created: list[int] = []
    yield created

    if created:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.saved_searches "
                    "WHERE search_id = ANY(%s)",
                    (created,),
                )


def test_create_requires_searches_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/searches",
        json={"name": "x", "filters": {}},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_create_rejects_empty_name():
    response = client.post("/api/v1/searches", json={"name": "", "filters": {}})
    assert response.status_code == 422


@requires_db
def test_saved_search_lifecycle(cleanup_searches):
    filters = {
        "q": "test",
        "addresses": ["78_v33"],
        "date_from": "2026-01-01",
        "collection_id": None,
    }

    created = client.post(
        "/api/v1/searches",
        json={"name": "Тестовый поиск", "filters": filters},
    )
    assert created.status_code == 201

    body = created.json()
    search_id = body["search_id"]
    cleanup_searches.append(search_id)

    assert body["name"] == "Тестовый поиск"
    assert body["filters"]["addresses"] == ["78_v33"]

    items = client.get("/api/v1/searches").json()["items"]
    assert any(item["search_id"] == search_id for item in items)

    assert client.delete(f"/api/v1/searches/{search_id}").status_code == 200
    assert client.delete(f"/api/v1/searches/{search_id}").status_code == 404
    cleanup_searches.remove(search_id)


@requires_db
def test_saved_searches_are_isolated_per_user():
    """A bookmarked filter belongs to its owner only."""

    from app.users import database as users_db

    names = ["__srch_owner__", "__srch_other__"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.saved_searches WHERE user_id IN "
                "(SELECT user_id::text FROM public.users WHERE name = ANY(%s))",
                (names,),
            )
            cur.execute(
                "DELETE FROM public.users WHERE name = ANY(%s)", (names,)
            )

    try:
        owner = users_db.create_user(name=names[0], role="Менеджер")
        other = users_db.create_user(name=names[1], role="Менеджер")

        owner_h = {
            "Authorization": f"Bearer {users_db.create_session(owner['user_id'])}"
        }
        other_h = {
            "Authorization": f"Bearer {users_db.create_session(other['user_id'])}"
        }

        created = client.post(
            "/api/v1/searches",
            json={"name": "Личный фильтр", "filters": {"q": "test"}},
            headers=owner_h,
        )
        assert created.status_code == 201
        search_id = created.json()["search_id"]

        owner_names = [
            item["name"]
            for item in client.get("/api/v1/searches", headers=owner_h).json()[
                "items"
            ]
        ]
        other_names = [
            item["name"]
            for item in client.get("/api/v1/searches", headers=other_h).json()[
                "items"
            ]
        ]
        assert "Личный фильтр" in owner_names
        assert "Личный фильтр" not in other_names

        # Someone else cannot delete it; the owner can.
        assert (
            client.delete(f"/api/v1/searches/{search_id}", headers=other_h)
            .status_code
            == 404
        )
        assert (
            client.delete(f"/api/v1/searches/{search_id}", headers=owner_h)
            .status_code
            == 200
        )
    finally:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.saved_searches WHERE user_id IN "
                    "(SELECT user_id::text FROM public.users "
                    " WHERE name = ANY(%s))",
                    (names,),
                )
                cur.execute(
                    "DELETE FROM public.users WHERE name = ANY(%s)", (names,)
                )

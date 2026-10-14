"""
Tests for per-manager UI state (schema 015, /v1/selection).

Auth checks run everywhere; the lifecycle test needs PostgreSQL.
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
                cur.execute("select to_regclass('public.manager_selections')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="manager_selections not available (INGEST_DB_* / schema 015)",
)


def _cleanup_user(name: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.manager_selections "
                "WHERE user_id IN (SELECT user_id::text FROM public.users "
                "                  WHERE name = %s)",
                (name,),
            )
            cur.execute("DELETE FROM public.users WHERE name = %s", (name,))


def test_selection_requires_authentication():
    # Open mode (no tokens): no principal -> 401, not a DB error.
    assert client.get("/api/v1/selection").status_code == 401
    assert (
        client.put("/api/v1/selection", json={"state": {}}).status_code == 401
    )


@requires_db
def test_selection_lifecycle():
    from app.users import database as users_db

    name = "__sel_test__"
    _cleanup_user(name)

    try:
        user = users_db.create_user(name=name, role="Менеджер")
        token = users_db.create_session(user["user_id"])
        headers = {"Authorization": f"Bearer {token}"}

        empty = client.get("/api/v1/selection", headers=headers).json()
        assert empty["state"] == {}

        payload = {
            "state": {
                "selected": ["PH_a", "PH_b"],
                "filters": {"q": "Luvio"},
            }
        }
        saved = client.put(
            "/api/v1/selection", json=payload, headers=headers
        ).json()
        assert saved["state"]["selected"] == ["PH_a", "PH_b"]

        got = client.get("/api/v1/selection", headers=headers).json()
        assert got["state"]["filters"] == {"q": "Luvio"}

        # A partial save (the grid sends only its selection, the display
        # settings only theirs) must not drop the other keys.
        client.put(
            "/api/v1/selection",
            json={"state": {"selected": ["PH_c"]}},
            headers=headers,
        )
        merged = client.get("/api/v1/selection", headers=headers).json()

        assert merged["state"]["selected"] == ["PH_c"]
        assert merged["state"]["filters"] == {"q": "Luvio"}
    finally:
        _cleanup_user(name)

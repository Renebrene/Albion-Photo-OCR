"""
Login is fail-closed: an account without a password cannot authenticate.

Requires PostgreSQL (users/sessions tables).
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
                cur.execute("select to_regclass('public.users')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="users table not available (INGEST_DB_* / schema 010)",
)

NAME = "__login_test__"


def _cleanup() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.manager_selections WHERE user_id IN "
                "(SELECT user_id::text FROM public.users WHERE name = %s)",
                (NAME,),
            )
            cur.execute("DELETE FROM public.users WHERE name = %s", (NAME,))


@requires_db
def test_passwordless_account_cannot_login_then_works_after_set():
    from app.users import database as users_db

    _cleanup()

    try:
        users_db.create_user(name=NAME, role="Администратор")

        blocked = client.post(
            "/api/v1/auth/login",
            json={"name": NAME, "password": ""},
        )
        assert blocked.status_code == 403
        assert "password" in blocked.json()["detail"].lower()

        # Wrong password is still rejected once a password exists.
        user = users_db.get_user_by_name(NAME)
        users_db.set_password(user["user_id"], "s3cret")

        wrong = client.post(
            "/api/v1/auth/login",
            json={"name": NAME, "password": "nope"},
        )
        assert wrong.status_code == 401

        ok = client.post(
            "/api/v1/auth/login",
            json={"name": NAME, "password": "s3cret"},
        )
        assert ok.status_code == 200
        assert ok.json()["token"]
    finally:
        _cleanup()

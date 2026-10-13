"""
Connection pooling behaviour (app.ingest.database).

Requires PostgreSQL: the pool must return working connections with the same
commit-on-exit semantics as a fresh connect().
"""

from __future__ import annotations

import os

import pytest

from app import settings_store
from app.ingest import database as ingest_db


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.app_settings')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="app_settings not available (INGEST_DB_* / schema 008)",
)


@requires_db
def test_pool_commits_and_reuses():
    key = "__pool_probe__"
    original = settings_store.get(key)

    try:
        # Write through a pool connection...
        settings_store.set_value(key, "value-1")

        # ...and read it back (possibly on a different pooled connection).
        assert settings_store.get(key) == "value-1"

        # A second write works too (connection reuse does not leak state).
        settings_store.set_value(key, "value-2")
        assert settings_store.get(key) == "value-2"
    finally:
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.app_settings WHERE key = %s", (key,)
                )

        if original is not None:
            settings_store.set_value(key, original)


@requires_db
def test_pool_rolls_back_on_error():
    key = "__pool_rollback_probe__"

    with ingest_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.app_settings WHERE key = %s", (key,))

    from psycopg.types.json import Json

    with pytest.raises(RuntimeError):
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO public.app_settings (key, value) "
                    "VALUES (%s, %s)",
                    (key, Json("should-not-persist")),
                )
            raise RuntimeError("boom")

    assert settings_store.get(key) is None


def test_pool_can_be_disabled(monkeypatch):
    monkeypatch.setenv("SCENE_DB_POOL", "0")
    assert ingest_db._pool_enabled() is False

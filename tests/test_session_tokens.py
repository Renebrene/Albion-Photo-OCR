"""
Сессионные токены: в базе только хэш, сам токен — у клиента.

Проверки с базой пропускаются, если она не сконфигурирована (нет
INGEST_DB_PASSWORD): обработка хэша проверяется и без неё.
"""

from __future__ import annotations

import hashlib
import os

import pytest

from app.users import database as users_db


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with users_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.sessions')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(), reason="PostgreSQL не сконфигурирован"
)


# ---- хэш (чистая функция) --------------------------------------------------


def test_hash_is_sha256_of_the_token():
    token = "abc-123"

    expected = hashlib.sha256(b"abc-123").hexdigest()

    assert users_db.hash_session_token(token) == expected
    assert len(users_db.hash_session_token(token)) == 64


def test_hash_is_stable_and_distinct():
    assert users_db.hash_session_token("a") == users_db.hash_session_token("a")
    assert users_db.hash_session_token("a") != users_db.hash_session_token("b")


def test_hash_never_returns_the_token():
    token = "секретный-токен"

    assert token not in users_db.hash_session_token(token)


# ---- работа с базой --------------------------------------------------------


@pytest.fixture()
def user_id():
    """Отдельный пользователь на время теста: сессии удаляются каскадом."""

    name = f"pytest-session-{os.getpid()}"

    with users_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO public.users (name, role, active, password_hash)
                   VALUES (%s, 'Гость', FALSE, 'x')
                   ON CONFLICT (name) DO UPDATE SET active = FALSE
                   RETURNING user_id""",
                (name,),
            )
            created = cur.fetchone()[0]

    yield int(created)

    with users_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.users WHERE user_id = %s", (created,))


@requires_db
def test_session_is_stored_as_a_hash(user_id):
    token = users_db.create_session(user_id)

    with users_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT token_hash FROM public.sessions WHERE user_id = %s",
                (user_id,),
            )
            stored = cur.fetchone()[0]

    assert stored == users_db.hash_session_token(token)
    # Самое важное: в базе нет самого токена.
    assert stored != token
    assert token not in stored


@requires_db
def test_column_with_the_plaintext_token_is_gone():
    with users_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_name = 'sessions'""",
            )
            columns = {row[0] for row in cur.fetchall()}

    assert "token_hash" in columns
    assert "session_id" not in columns


@requires_db
def test_lookup_by_the_presented_token(user_id):
    token = users_db.create_session(user_id)

    assert users_db.get_session(token) is None  # пользователь выключен (active=false)
    assert users_db.get_session("подделка") is None
    assert users_db.get_session("") is None

    # Включённый пользователь находится по тому же токену.
    with users_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET active = TRUE WHERE user_id = %s",
                (user_id,),
            )

    found = users_db.get_session(token)

    assert found is not None
    assert found["user_id"] == user_id


@requires_db
def test_logout_removes_the_session_by_token(user_id):
    with users_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET active = TRUE WHERE user_id = %s",
                (user_id,),
            )

    token = users_db.create_session(user_id)

    assert users_db.get_session(token) is not None
    assert users_db.delete_session(token) is True
    assert users_db.get_session(token) is None
    # Повторный выход по тому же токену ничего не находит.
    assert users_db.delete_session(token) is False

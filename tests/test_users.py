"""
Tests for users, password hashing and sessions (schema 010).

Password/security tests run everywhere; database and API tests need PostgreSQL.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.users import database as users_db
from app.users.security import has_password, hash_password, verify_password

client = TestClient(app, raise_server_exceptions=False)


def test_hash_and_verify_roundtrip():
    stored = hash_password("s3cret")

    assert stored.startswith("scrypt$")
    assert verify_password("s3cret", stored) is True
    assert verify_password("wrong", stored) is False


def test_no_password_is_fail_closed():
    # An account without a password hash can never authenticate.
    assert verify_password("anything", None) is False
    assert verify_password("anything", "") is False
    assert has_password(None) is False
    assert has_password("scrypt$a$b") is True


def test_garbage_hash_is_rejected():
    assert verify_password("x", "not-a-hash") is False
    assert verify_password("x", "md5$aa$bb") is False


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with users_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.users')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="users not available (INGEST_DB_* / schema 010)",
)


@pytest.fixture
def temp_user():
    created: list[int] = []
    yield created

    if created:
        with users_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.users WHERE user_id = ANY(%s)",
                    (created,),
                )


def test_create_user_requires_users_manage(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/users",
        json={"name": "Тест-Менеджер"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


@requires_db
def test_seeded_accounts_cannot_be_archived():
    """
    Администратор and Гость are the accounts the installation keeps working:
    the API refuses to archive them, and the window disables the button.
    """

    from fastapi import HTTPException

    from app.api import routes
    from app.api.schemas import UserUpdate

    seeded = [
        user
        for user in users_db.list_users(active_only=False)
        if user["name"] in ("Администратор", "Гость")
    ]

    if len(seeded) < 2:
        pytest.skip("the seeded accounts are not present")

    for user in seeded:
        with pytest.raises(HTTPException) as failure:
            routes.update_user(user["user_id"], UserUpdate(active=False))

        assert failure.value.status_code == 400
        assert "нельзя архивировать" in failure.value.detail

    # Editing them otherwise still works (the rule only blocks archiving).
    # The values are written back unchanged, so the row is left as it was.
    edited = routes.update_user(
        seeded[0]["user_id"],
        UserUpdate(name=seeded[0]["name"], color=seeded[0].get("color")),
    )

    assert edited["active"] is True


@requires_db
def test_login_and_me(temp_user):
    user = users_db.create_user(
        name="Тест Логин",
        role="Администратор",
        password="p@ss",
    )
    temp_user.append(user["user_id"])

    bad = client.post(
        "/api/v1/auth/login",
        json={"name": "Тест Логин", "password": "nope"},
    )
    assert bad.status_code == 401

    ok = client.post(
        "/api/v1/auth/login",
        json={"name": "Тест Логин", "password": "p@ss"},
    )
    assert ok.status_code == 200

    token = ok.json()["token"]
    assert "password_hash" not in ok.json()["user"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert me["user"]["name"] == "Тест Логин"

    # The session token works as a credential for admin scope.
    created = client.post(
        "/api/v1/users",
        json={"name": "Тест Ребёнок", "role": "Гость"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    temp_user.append(created.json()["user_id"])

    logged_out = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logged_out.json()["logged_out"] is True

    after = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert after["user"] is None

@requires_db
def test_create_user_name_collision_case_insensitive(temp_user):
    """
    Имя пользователя регистронезависимо: «иван» и «Иван» — одно имя.
    Повторное создание в другом регистре кидает ValueError с понятным
    сообщением, а не падает на constraint БД (владелец, 20.11.2026).
    """

    user = users_db.create_user(name="Тест Коллизия", role="Менеджер")
    temp_user.append(user["user_id"])

    with pytest.raises(ValueError) as collision:
        users_db.create_user(name="тест коллизия", role="Менеджер")

    assert "name already taken" in str(collision.value)

    # Кириллица: регистр сведён корректно и в верхнем варианте.
    with pytest.raises(ValueError) as cyrillic:
        users_db.create_user(name="ТЕСТ КОЛЛИЗИЯ", role="Менеджер")

    assert "name already taken" in str(cyrillic.value)


@requires_db
def test_create_user_keeps_the_entered_casing(temp_user):
    """Регистронезависимость — при сравнении, а не при записи: имя хранится
    так, как ввёл администратор."""

    user = users_db.create_user(name="ПрЕдСаВиТеЛь Отдела", role="Менеджер")
    temp_user.append(user["user_id"])

    # Имя сохраняется с исходным регистром — сравнение с зарегистрированным
    # регистронезависимое, а запись хранит вариант администратора.
    assert user["name"] == "ПрЕдСаВиТеЛь Отдела"


@requires_db
def test_archived_user_name_can_be_taken_again(temp_user):
    """Имя архивированного пользователя свободно: вход для него закрыт,
    поэтому новый сотрудник может получить то же имя (владелец, 20.11.2026)."""

    old = users_db.create_user(name="Тест Архив", role="Менеджер")
    temp_user.append(old["user_id"])

    users_db.update_user(old["user_id"], active=False)

    fresh = users_db.create_user(name="тест архив", role="Менеджер")
    temp_user.append(fresh["user_id"])

    assert fresh["user_id"] != old["user_id"]
    assert fresh["active"] is True


@requires_db
def test_update_user_name_collision_case_insensitive(temp_user):
    """Переименование не должно занимать чужое имя в другом регистре,
    а своё собственное — можно (тот же user_id не коллизия)."""

    first = users_db.create_user(name="Первый Коллизия", role="Менеджер")
    second = users_db.create_user(name="Второй Коллизия", role="Менеджер")
    temp_user.extend([first["user_id"], second["user_id"]])

    with pytest.raises(ValueError) as collision:
        users_db.update_user(
            second["user_id"],
            name="первый коллизия",
        )

    assert "name already taken" in str(collision.value)

    # Переименование самого себя в свой же регистр — разрешено.
    same = users_db.update_user(
        first["user_id"],
        name="ПЕРВЫЙ КОЛЛИЗИЯ",
    )

    assert same["name"] == "ПЕРВЫЙ КОЛЛИЗИЯ"

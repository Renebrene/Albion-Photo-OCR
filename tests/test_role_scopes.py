"""
Role -> scope policy (app.api.auth.ROLE_SCOPES) and its enforcement.

These tests are DB-free: they drive the scope dependency directly and stub the
session lookup, so the policy is pinned without PostgreSQL. The owner's roadmap
is the source of truth here:

* Гость — read-only: filters and the photo/video grid, no downloads, no edit
  dialogs, no collections, no technical section.
* Менеджер — working user: everything Администратор has except the technical
  section, including running pipeline jobs and downloading media.
* Администратор — wildcard.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import auth
from app.users import database as users_db

ROLES = ("Администратор", "Менеджер", "Гость")


def _resolve(monkeypatch, role: str):
    """Resolve a session principal for *role* without touching PostgreSQL."""

    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "1")
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setattr(
        users_db,
        "get_session",
        lambda token: (
            {"user_id": 1, "name": "tester", "role": role}
            if token == "sess"
            else None
        ),
    )
    return auth.resolve_principal("Bearer sess")


def test_guest_is_read_only(monkeypatch):
    principal = _resolve(monkeypatch, "Гость")
    scopes = principal["scopes"]

    assert scopes == {"read"}
    for denied in (
        "jobs:write",
        "jobs:read",
        "originals",
        "collections:write",
        "searches:write",
        "upload:write",
        "photos:write",
        "addresses:write",
        "videos:write",
        "videos:download",
        "users:manage",
        "settings:write",
    ):
        assert denied not in scopes, f"Гость не должен иметь {denied}"


def test_manager_runs_jobs(monkeypatch):
    scopes = _resolve(monkeypatch, "Менеджер")["scopes"]

    for allowed in (
        "read",
        "jobs:read",
        "jobs:write",
        "photos:write",
        "addresses:write",
        "videos:read",
        "videos:write",
        "videos:download",
    ):
        assert allowed in scopes, f"Менеджер должен иметь {allowed}"

    # The technical section (user administration) stays administrator-only.
    assert "users:manage" not in scopes
    # QWEN provider credentials/model are administration, not a working job.
    assert "settings:write" not in scopes
    assert "*" not in scopes


def test_guest_gets_no_download_scopes(monkeypatch):
    """Скачивание — граница между Гостем и рабочими ролями (решение 2026-10-16)."""

    manager = _resolve(monkeypatch, "Менеджер")["scopes"]
    guest = _resolve(monkeypatch, "Гость")["scopes"]

    assert "originals" in manager
    assert {"videos:read", "videos:write", "videos:download"} <= manager

    for scope in ("originals", "videos:read", "videos:write", "videos:download"):
        assert scope not in guest


def test_administrator_has_everything(monkeypatch):
    assert _resolve(monkeypatch, "Администратор")["scopes"] == {"*"}


def test_unknown_role_falls_back_to_read_only(monkeypatch):
    scopes = _resolve(monkeypatch, "НеизвестнаяРоль")["scopes"]
    assert scopes == {"read"}


def test_require_scope_denies_and_allows_by_role(monkeypatch):
    """The dependency raises 403 for a missing scope and returns a principal."""

    # A scope Гость lacks is denied...
    monkeypatch.setattr(
        users_db,
        "get_session",
        lambda token: {"user_id": 1, "name": "g", "role": "Гость"},
    )
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "1")
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)

    dependency = auth.require_scope("jobs:write")
    with pytest.raises(HTTPException) as denied:
        dependency(authorization="Bearer sess")
    assert denied.value.status_code == 403

    # ...while the same scope is granted to Менеджер.
    monkeypatch.setattr(
        users_db,
        "get_session",
        lambda token: {"user_id": 2, "name": "m", "role": "Менеджер"},
    )
    principal = auth.require_scope("jobs:write")(authorization="Bearer sess")
    assert principal["kind"] == "user"
    assert "jobs:write" in principal["scopes"]


def test_require_scope_is_401_without_any_credential(monkeypatch):
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "1")
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)

    with pytest.raises(HTTPException) as exc:
        auth.require_scope("read")(authorization=None)
    assert exc.value.status_code == 401


def test_role_scopes_cover_only_known_roles():
    assert set(auth.ROLE_SCOPES) == set(ROLES)

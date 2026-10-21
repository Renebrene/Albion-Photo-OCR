"""
Input limits and access tightening (audit items 9/10/12).

These run without PostgreSQL: they are rejected (or forbidden) before any DB
write, except where noted.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.nl_search import MAX_PER_TERM
from app.core.errors import redact_absolute_paths

client = TestClient(app, raise_server_exceptions=False)


# --- item 10: array limits ---------------------------------------------------


def test_qwen_photo_ids_item_limit():
    response = client.post(
        "/api/v1/jobs/qwen",
        json={"photo_ids": ["PH_" + "0" * 24] * 5001},
    )
    assert response.status_code == 422


def test_qwen_photo_ids_format_validated():
    response = client.post(
        "/api/v1/jobs/qwen",
        json={"photo_ids": ["not-a-photo-id"]},
    )
    assert response.status_code == 422
    assert "invalid photo_id" in response.json()["detail"]


def test_collection_members_item_limit():
    response = client.post(
        "/api/v1/collections/1/members",
        json={"member_type": "photo", "values": ["x"] * 5001},
    )
    assert response.status_code == 422


# --- item 12: user directory is administrator-only --------------------------


def test_users_list_needs_users_manage(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


# --- item 11: path redaction ------------------------------------------------


def test_redact_absolute_paths():
    assert (
        redact_absolute_paths("failed to open /home/user/photos/a.jpg")
        == "failed to open a.jpg"
    )
    assert (
        redact_absolute_paths("PIL error in /mnt/data/x/y.JPG: broken")
        == "PIL error in y.JPG: broken"
    )
    # URLs are not mangled.
    assert (
        redact_absolute_paths("GET https://api.example.com/v1/models failed")
        == "GET https://api.example.com/v1/models failed"
    )


# --- item 9: NL search bounds ------------------------------------------------


def test_nl_search_reports_truncation(monkeypatch):
    from app.api import nl_search, repository

    class _Item:
        def __init__(self, photo_id):
            self.photo_id = photo_id

    monkeypatch.setattr(
        nl_search,
        "build_filters",
        lambda query: {key: None for key in nl_search._OUTPUT_KEYS},
    )

    def fake_list_photos(*, limit, query=None, addresses=None, **kwargs):
        # A non-null cursor means "there are more rows than this page".
        return [_Item("PH_x")], "PH_x"

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)

    result = nl_search.run("запрос")

    assert result["truncated"] is True
    assert result["count"] == 1
    assert MAX_PER_TERM >= 100

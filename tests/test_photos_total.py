"""Счётчик «За период N фото» в ответе /v1/photos."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import repository
from app.api.main import app
from app.api.schemas import PhotoSummary

client = TestClient(app, raise_server_exceptions=False)


def _photo() -> PhotoSummary:
    return PhotoSummary(
        photo_id="PH_" + "a" * 24,
        filename="photo.jpg",
        width=16,
        height=12,
        container_format="JPEG",
    )


def test_the_first_page_carries_the_filtered_total(monkeypatch):
    calls = {}

    def fake_list_photos(**kwargs):
        calls["list"] = kwargs
        return [_photo()], "next-cursor"

    def fake_count_photos(**kwargs):
        calls["count"] = kwargs
        return 42

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)
    monkeypatch.setattr(repository, "count_photos", fake_count_photos)

    response = client.get(
        "/api/v1/photos",
        params={"date_from": "2026-10-01", "date_to": "2026-10-31",
                "date_mode": "capture"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 42
    # The count must use exactly the same filters as the page.
    assert calls["count"]["date_from"] == "2026-10-01"
    assert calls["count"]["date_to"] == "2026-10-31"
    assert calls["count"]["date_mode"] == "capture"


def test_a_continuation_page_does_not_recount(monkeypatch):
    calls = []

    monkeypatch.setattr(
        repository, "list_photos", lambda **kwargs: ([_photo()], "next-cursor")
    )

    def fake_count_photos(**kwargs):
        calls.append(kwargs)
        return 42

    monkeypatch.setattr(repository, "count_photos", fake_count_photos)

    response = client.get(
        "/api/v1/photos",
        params={"cursor": "PH_" + "b" * 24},
    )

    assert response.status_code == 200
    assert response.json()["total"] is None
    assert calls == []

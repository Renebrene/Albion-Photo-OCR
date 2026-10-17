"""Search-bar suggestions API (values + keyboard-layout hint)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes
from app.api.main import app

client = TestClient(app)


def test_short_query_returns_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes.repository, "suggest_terms",
        lambda term, limit=8: calls.append(term) or [],
    )

    response = client.get("/api/v1/search/suggestions?q=я")

    assert response.status_code == 200
    assert response.json() == {"items": [], "layout": None}
    assert calls == []


def test_direct_matches_are_returned_without_layout_hint(monkeypatch):
    items = [
        {"value": "Рязанка", "kind": "brand", "uses": 3},
        {"value": "Рязанская область", "kind": "tag", "uses": 1},
        {"value": "Рязань", "kind": "address", "uses": 2},
    ]
    monkeypatch.setattr(
        routes.repository, "suggest_terms",
        lambda term, limit=8: items,
    )

    response = client.get("/api/v1/search/suggestions?q=ряз")

    assert response.status_code == 200
    assert response.json() == {"items": items, "layout": None}


def test_wrong_layout_offers_the_converted_query(monkeypatch):
    calls = []

    def fake_suggest(term, limit=8):
        calls.append(term)
        if term == "rjvfhjdf":
            return []
        return [{"value": "Комарова 13", "kind": "address", "uses": 7}]

    monkeypatch.setattr(routes.repository, "suggest_terms", fake_suggest)

    response = client.get("/api/v1/search/suggestions?q=rjvfhjdf")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["layout"]["query"] == "комарова"
    assert body["layout"]["items"][0]["value"] == "Комарова 13"
    assert calls == ["rjvfhjdf", "комарова"]


def test_layout_fallback_only_when_direct_matches_are_few(monkeypatch):
    items = [
        {"value": f"Тег {index}", "kind": "tag", "uses": 1}
        for index in range(3)
    ]

    def fake_suggest(term, limit=8):
        if term == "комарова":
            return items
        return items

    monkeypatch.setattr(routes.repository, "suggest_terms", fake_suggest)

    body = client.get("/api/v1/search/suggestions?q=комарова").json()

    # Прямых совпадений достаточно — раскладку не проверяем.
    assert body["layout"] is None

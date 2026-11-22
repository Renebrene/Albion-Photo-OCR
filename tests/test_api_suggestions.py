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
        lambda term, limit=8, group=None: calls.append(term) or [],
    )

    response = client.get("/api/v1/search/suggestions?q=я")

    assert response.status_code == 200
    assert response.json() == {"items": [], "layout": None}
    assert calls == []


def test_group_is_forwarded_to_suggestions(monkeypatch):
    """Активная группа адресов сужает подсказки-адреса на сервере."""

    seen = []

    def fake_suggest(term, limit=8, group=None):
        seen.append(group)
        return []

    monkeypatch.setattr(routes.repository, "suggest_terms", fake_suggest)

    response = client.get("/api/v1/search/suggestions?q=ряз&group=screens")

    assert response.status_code == 200
    assert seen and all(value == "screens" for value in seen)


def test_direct_matches_are_returned_without_layout_hint(monkeypatch):
    items = [
        {"value": "Рязанка", "kind": "brand", "uses": 3},
        {"value": "Рязанская область", "kind": "tag", "uses": 1},
        {"value": "Рязань", "kind": "address", "uses": 2},
    ]

    def fake_suggest(term, limit=8, group=None):
        # Конвертированный запрос «hzp» ничего не находит — раскладка
        # вычисляется, но подсказок по ней нет.
        return items if term == "ряз" else []

    monkeypatch.setattr(routes.repository, "suggest_terms", fake_suggest)

    response = client.get("/api/v1/search/suggestions?q=ряз")

    assert response.status_code == 200
    assert response.json() == {"items": items, "layout": None}


def test_wrong_layout_offers_the_converted_query(monkeypatch):
    calls = []

    def fake_suggest(term, limit=8, group=None):
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


def test_layout_is_computed_alongside_direct_matches(monkeypatch):
    """Конвертация раскладки — параллельно прямым находкам (20.11.2026).

    Русский запрос находит русские теги, а перевёрнутый (латинский) запрос
    в это же время находит латинские бренды — обе выдачи едут в ответе
    вместе, прямой прогон ничего не блокирует.
    """

    def fake_suggest(term, limit=8, group=None):
        if term == "комарова":
            return [{"value": f"Тег {index}", "kind": "tag", "uses": 1}
                    for index in range(3)]
        return [{"value": "ORION", "kind": "brand", "uses": 15}]

    monkeypatch.setattr(routes.repository, "suggest_terms", fake_suggest)

    body = client.get("/api/v1/search/suggestions?q=комарова").json()

    assert [item["value"] for item in body["items"]] == [
        "Тег 0", "Тег 1", "Тег 2",
    ]
    assert body["layout"]["query"] == "rjvfhjdf"
    assert body["layout"]["items"][0]["value"] == "ORION"

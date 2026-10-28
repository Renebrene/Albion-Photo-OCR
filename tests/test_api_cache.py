"""
Короткий кэш дорогих ответов (аудит 28.10.2026).

Панели адресов и клиентов, подвал и счётчик фото считаются по всему корпусу
(1-5 с) и зависят только от параметров фильтра. Проверяем сам механизм и то,
что он не подменяет разные фильтры одним ответом.
"""

from __future__ import annotations

import pytest

from app.api import cache, routes
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_the_second_call_uses_the_cached_value(monkeypatch):
    calls = []

    def producer():
        calls.append(1)
        return {"items": [1, 2, 3]}

    first = cache.cached(("key", 1), producer)
    second = cache.cached(("key", 1), producer)

    assert first == second == {"items": [1, 2, 3]}
    assert len(calls) == 1
    assert cache.stats()["hits"] == 1


def test_a_different_key_is_a_different_entry():
    calls = []

    cache.cached(("key", 1), lambda: calls.append(1) or "первый")
    value = cache.cached(("key", 2), lambda: calls.append(2) or "второй")

    assert value == "второй"
    assert calls == [1, 2]


def test_ttl_zero_disables_the_cache(monkeypatch):
    monkeypatch.setenv("SCENE_API_CACHE_TTL", "0")
    calls = []

    def producer():
        calls.append(1)
        return "значение"

    assert cache.cached(("key", 1), producer) == "значение"
    assert cache.cached(("key", 1), producer) == "значение"
    assert len(calls) == 2
    assert cache.stats()["size"] == 0


def test_an_error_is_not_cached():
    calls = []

    def failing():
        calls.append(1)
        raise RuntimeError("база недоступна")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cache.cached(("key", 1), failing)

    assert len(calls) == 2
    assert cache.stats()["size"] == 0


def test_expired_entry_is_recalculated(monkeypatch):
    calls = []
    monkeypatch.setenv("SCENE_API_CACHE_TTL", "0.01")

    def producer():
        calls.append(1)
        return len(calls)

    assert cache.cached(("key", 1), producer) == 1

    import time

    time.sleep(0.05)

    assert cache.cached(("key", 1), producer) == 2


def test_panel_route_asks_the_repository_once(monkeypatch):
    """Второй запрос панели с теми же параметрами не идёт в базу."""

    calls = []

    def fake_list(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(routes.repository, "list_addresses", fake_list)

    for _ in range(3):
        assert client.get("/api/v1/addresses?group=screens").status_code == 200

    assert len(calls) == 1


def test_panel_route_distinguishes_groups(monkeypatch):
    calls = []

    def fake_list(**kwargs):
        calls.append(kwargs.get("group"))
        return []

    monkeypatch.setattr(routes.repository, "list_addresses", fake_list)

    client.get("/api/v1/addresses?group=screens")
    client.get("/api/v1/addresses?group=roads")

    assert calls == ["screens", "roads"]


def test_clients_route_caches_only_the_first_page(monkeypatch):
    calls = []

    def fake_list(**kwargs):
        calls.append(kwargs.get("cursor"))
        return [], "next"

    monkeypatch.setattr(routes.repository, "list_clients", fake_list)

    client.get("/api/v1/clients?limit=10")
    client.get("/api/v1/clients?limit=10")
    # Продолжение списка запрашивается курсором и кэшу не подлежит.
    client.get("/api/v1/clients?limit=10&cursor=next")

    assert calls == [None, "next"]


def test_stats_route_is_cached(monkeypatch):
    calls = []

    def fake_stats(**kwargs):
        calls.append(kwargs)
        return {"photos": 1}

    monkeypatch.setattr(routes.repository, "stats", fake_stats)

    first = client.get("/api/v1/stats?date_mode=upload")
    second = client.get("/api/v1/stats?date_mode=upload")

    assert first.json() == second.json() == {"photos": 1}
    assert len(calls) == 1


def test_the_count_of_the_grid_is_cached(monkeypatch):
    from app.api.schemas import PhotoSummary

    calls = []

    def fake_photos(**_kwargs):
        return [
            PhotoSummary(
                photo_id="PH_" + "a" * 24,
                filename="photo.jpg",
                width=16,
                height=12,
                container_format="JPEG",
            )
        ], None

    def fake_count(**kwargs):
        calls.append(kwargs)
        return 42

    monkeypatch.setattr(routes.repository, "list_photos", fake_photos)
    monkeypatch.setattr(routes.repository, "count_photos", fake_count)
    # Группы — без обращения к базе: у каждой свой список адресов.
    monkeypatch.setattr(
        routes.directory_mod,
        "address_ids_for_tab",
        lambda tab: [1] if tab == "screens" else [2],
    )

    first = client.get("/api/v1/photos?group=screens&limit=10")
    second = client.get("/api/v1/photos?group=screens&limit=10")

    assert first.json()["total"] == second.json()["total"] == 42
    assert len(calls) == 1

    # Другой набор адресов — другой счёт: кэш не склеивает фильтры.
    client.get("/api/v1/photos?group=roads&limit=10")

    assert len(calls) == 2
    assert calls[0]["addresses"] != calls[1]["addresses"]

"""
Список адресов грузится в составе активной подборки (задание, 28.10.2026).

Адресная подборка оставляет в панели свои адреса, клиентская — адреса, где
есть её клиенты. База не нужна: репозиторий подменяется.
"""

from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.api import repository, routes
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _item(address_id: int, legal: str, **extra) -> dict:
    item = {
        "address": f"addr:{address_id}",
        "address_id": address_id,
        "legal_address": legal,
        "simple_address": legal,
        "format": "Щит",
        "city": "Ростов-на-Дону",
        "scope": "other",
        "fingerprints": [],
        "count": 1,
        "period_count": 1,
    }
    item.update(extra)
    return item


# ---- панель адресов ----


def test_panel_shows_only_the_collection_addresses(monkeypatch):
    monkeypatch.setattr(
        routes.repository, "collection_panel_filter", lambda _ids: ({"addr:1"}, [])
    )
    monkeypatch.setattr(
        routes.repository,
        "list_addresses",
        lambda **_kwargs: [
            _item(1, "Комарова 13"),
            _item(2, "Ленина 5"),
            # Служебная строка панели: она не адрес и остаётся всегда.
            {"review": True, "name": "Требуют проверки", "count": 3},
        ],
    )

    items = client.get("/api/v1/addresses?collection_id=5").json()["items"]
    names = [item["name"] for item in items]

    # Служебная строка идёт первой (её дописывают до сведения сторон).
    assert names[0] == "Требуют проверки"
    assert "Комарова 13" in names
    assert "Ленина 5" not in names


def test_a_legacy_fingerprint_member_still_matches(monkeypatch):
    """Старые подборки хранят id слепка, а не `addr:<id>`."""

    monkeypatch.setattr(
        routes.repository, "collection_panel_filter", lambda _ids: ({"80_v33"}, [])
    )
    monkeypatch.setattr(
        routes.repository,
        "list_addresses",
        lambda **_kwargs: [
            _item(1, "Комарова 13", fingerprints=["80_v33"]),
            _item(2, "Ленина 5", fingerprints=["81_v33"]),
        ],
    )

    items = client.get("/api/v1/addresses?collection_id=5").json()["items"]

    assert [item["name"] for item in items] == ["Комарова 13"]


def test_client_collection_narrows_through_its_clients(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(
        routes.repository,
        "collection_panel_filter",
        lambda _ids: (None, ["Клиент А"]),
    )

    def fake_list(**kwargs):
        seen.update(kwargs)
        return [_item(1, "Комарова 13")]

    monkeypatch.setattr(routes.repository, "list_addresses", fake_list)

    client.get("/api/v1/addresses?collection_id=9")

    # Клиенты подборки объединяются с клиентами запроса, а не заменяют их.
    assert seen["clients"] == ["Клиент А"]

    client.get("/api/v1/addresses?collection_id=9&client=Клиент%20Б")

    assert seen["clients"] == ["Клиент Б", "Клиент А"]


def test_without_collections_the_panel_is_complete(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(
        routes.repository, "collection_panel_filter", lambda _ids: (None, [])
    )

    def fake_list(**kwargs):
        calls.append(kwargs)
        return [_item(1, "Комарова 13"), _item(2, "Ленина 5")]

    monkeypatch.setattr(routes.repository, "list_addresses", fake_list)

    items = client.get("/api/v1/addresses").json()["items"]

    assert len(items) == 2
    assert calls[0]["clients"] is None


# ---- разбор состава подборок ----


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.queries: list[str] = []

    def execute(self, sql, params=None):
        self.queries.append(sql)

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _patch_connection(monkeypatch, rows):
    cursor = _Cursor(rows)

    @contextmanager
    def fake_connection():
        yield type("Conn", (), {"cursor": lambda _self: cursor})()

    monkeypatch.setattr(repository, "get_connection", fake_connection)
    return cursor


def test_collection_filter_splits_addresses_and_clients(monkeypatch):
    cursor = _patch_connection(
        monkeypatch,
        [
            ("address", "addr:1"),
            ("address", "addr:2"),
            ("client", "Клиент А"),
            ("client", "Клиент А"),
            # Подборка фотографий панель адресов не сужает.
            ("photo", "PH_" + "a" * 24),
        ],
    )

    addresses, clients = repository.collection_panel_filter([5, 6])

    assert addresses == {"addr:1", "addr:2"}
    assert clients == ["Клиент А"]
    assert len(cursor.queries) == 1


def test_collection_filter_without_ids_does_not_touch_the_database(monkeypatch):
    def explode():
        raise AssertionError("без подборок запрос в базу не нужен")

    monkeypatch.setattr(repository, "get_connection", explode)

    assert repository.collection_panel_filter(None) == (None, [])
    assert repository.collection_panel_filter([]) == (None, [])
    # Прямой вызов обработчика приносит объект FastAPI-значения по умолчанию.
    assert repository.collection_panel_filter(routes.list_addresses.__defaults__[0]) == (None, [])


def test_direct_route_call_keeps_the_panel_complete(monkeypatch):
    """Маршрут вызывают напрямую (тесты, скрипты): без подборки база не нужна."""

    monkeypatch.setattr(routes.repository, "list_addresses", lambda **_kwargs: [])

    def explode():
        raise AssertionError("без номера подборки запрос в базу не нужен")

    monkeypatch.setattr(routes.repository, "get_connection", explode)

    assert routes.list_addresses(
        limit=100,
        date_from=None,
        date_to=None,
        date_mode="upload",
        client=None,
        group=None,
    ) == {"items": []}


def test_collection_filter_without_address_collections_keeps_the_panel(monkeypatch):
    _patch_connection(monkeypatch, [("client", "Клиент А")])

    addresses, clients = repository.collection_panel_filter([9])

    assert addresses is None
    assert clients == ["Клиент А"]


def test_union_values_skips_empties_and_duplicates():
    assert routes._union_values(None, []) is None
    assert routes._union_values(["a"], ["a", "b", ""]) == ["a", "b"]


def test_address_in_values_accepts_legacy_fingerprint_ids():
    assert routes._address_in_values({"address": "addr:1"}, {"addr:1"}) is True
    assert routes._address_in_values(
        {"address": "addr:1", "fingerprints": ["80_v33"]}, {"80_v33"}
    ) is True
    assert routes._address_in_values({"address": "addr:1"}, {"addr:2"}) is False

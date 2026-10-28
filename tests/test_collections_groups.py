"""
Подборки адресов и группы верхней панели (задание, п. 7, пункт «е»).

Подборка хранит значения `addr:<id>`; группы вычисляются по этим адресам.
База не нужна: репозиторий подменяется.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _collection(collection_id, scope, name="Подборка"):
    return {
        "collection_id": collection_id,
        "name": name,
        "kind": "manual",
        "scope": scope,
        "members": 1,
    }


def test_address_collection_knows_its_groups(monkeypatch):
    monkeypatch.setattr(
        routes.repository,
        "list_collections",
        lambda _user=None: [
            _collection(1, "addresses", "Ростов"),
            _collection(2, "addresses", "Таганрог"),
            _collection(3, "clients", "Клиенты"),
        ],
    )
    monkeypatch.setattr(
        routes.repository,
        "collection_address_members",
        lambda: {1: ["addr:10"], 2: ["addr:20"]},
    )
    monkeypatch.setattr(
        routes.directory_mod,
        "list_address_rows",
        lambda: [
            {"address_id": 10, "scope": "other", "city": "Ростов-на-Дону", "format": "Щит"},
            {"address_id": 20, "scope": "other", "city": "Таганрог", "format": "Щит"},
        ],
    )

    items = client.get("/api/v1/collections").json()["items"]
    by_name = {item["name"]: item for item in items}

    assert by_name["Ростов"]["groups"] == ["rostov"]
    assert by_name["Таганрог"]["groups"] == ["cities"]
    # Клиентские подборки групп не имеют — видны в любом режиме.
    assert "groups" not in by_name["Клиенты"]


def test_an_unknown_address_gives_no_groups(monkeypatch):
    monkeypatch.setattr(
        routes.repository,
        "list_collections",
        lambda _user=None: [_collection(1, "addresses")],
    )
    monkeypatch.setattr(
        routes.repository,
        "collection_address_members",
        lambda: {1: ["addr:999", "80_v33"]},
    )
    monkeypatch.setattr(routes.directory_mod, "list_address_rows", lambda: [])

    items = client.get("/api/v1/collections").json()["items"]

    assert items[0]["groups"] == []

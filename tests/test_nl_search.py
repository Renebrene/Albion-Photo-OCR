"""
Tests for natural-language search (app.api.nl_search).

The QWEN call is never made: JSON parsing is tested directly and run() is
exercised with build_filters and repository.list_photos stubbed out.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import nl_search
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


class _Item:
    def __init__(self, photo_id):
        self.photo_id = photo_id


def test_extract_json_plain():
    assert nl_search._extract_json('{"q": "щит"}') == {"q": "щит"}


def test_extract_json_strips_think_block():
    content = '<think>plan</think>{"client": "Маркет"}'
    assert nl_search._extract_json(content) == {"client": "Маркет"}


def test_extract_json_wraps_prose():
    content = 'Sure! {"brand": "Luvio"} is the answer'
    assert nl_search._extract_json(content) == {"brand": "Luvio"}


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        nl_search._extract_json("no json here")


def test_run_merges_terms(monkeypatch):
    monkeypatch.setattr(
        nl_search,
        "build_filters",
        lambda query: {
            "q": None,
            "client": "Маркет",
            "brand": "Luvio",
            "category": None,
            "address": None,
        },
    )

    calls = {}

    def fake_list_photos(*, limit, query=None, addresses=None, **kwargs):
        calls[query] = True
        if query == "Маркет":
            return [_Item("PH_a"), _Item("PH_b")], None
        if query == "Luvio":
            return [_Item("PH_b"), _Item("PH_c")], None
        return [], None

    from app.api import repository

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)

    result = nl_search.run("найди вывески Luvio для Маркета")

    assert set(result["photo_ids"]) == {"PH_a", "PH_b", "PH_c"}
    assert result["count"] == 3
    assert calls == {"Маркет": True, "Luvio": True}


def test_run_falls_back_to_raw_query(monkeypatch):
    monkeypatch.setattr(
        nl_search,
        "build_filters",
        lambda query: {key: None for key in nl_search._OUTPUT_KEYS},
    )

    seen = {}

    def fake_list_photos(*, limit, query=None, addresses=None, **kwargs):
        seen["query"] = query
        return [_Item("PH_x")], None

    from app.api import repository

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)

    result = nl_search.run("сумбурный запрос")

    assert seen["query"] == "сумбурный запрос"
    assert result["photo_ids"] == ["PH_x"]


def test_enqueue_requires_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:originals")
    response = client.post(
        "/api/v1/jobs/nl-search",
        json={"query": "вывески"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_run_does_not_pass_a_human_address_as_a_fingerprint_filter(monkeypatch):
    """QWEN отдаёт «Комарова 13», а фильтр `addresses` ждёт id слепка.

    Раньше адрес передавался в addresses и обнулял все термины запроса.
    """

    monkeypatch.setattr(
        nl_search,
        "build_filters",
        lambda query: {
            "q": None,
            "client": "Яндекс.Еда",
            "brand": None,
            "category": None,
            "address": "Комарова 13",
        },
    )

    seen = []

    def fake_list_photos(*, limit, query=None, addresses=None, **kwargs):
        seen.append((query, addresses))
        return [_Item("PH_a")], None

    from app.api import repository

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)

    result = nl_search.run("вывеска Яндекс.Еды на Комаровой")

    assert seen == [("Яндекс.Еда", None), ("Комарова 13", None)]
    assert result["photo_ids"] == ["PH_a"]

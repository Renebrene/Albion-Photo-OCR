"""
Закладка кнопки верхней панели у адреса (schema/056, задание 28.10.2026).

Списки адресов меняются редко, поэтому закладка считается при разборе XLS и
хранится в `address_directory.panel_group`; панель и грид фильтруют по ней в
SQL, до всякого ограничения длины. База здесь не нужна: соединение подменяется.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from app.api import directory as directory_mod
from app.api import repository, routes


class _Cursor:
    """Курсор-запись: отдаёт заготовленные ответы и запоминает SQL с параметрами."""

    def __init__(self, responses: list | None = None):
        self.responses = list(responses or [])
        self.queries: list[tuple[str, object]] = []
        self.current = None

    def execute(self, sql, params=None):
        self.queries.append((" ".join(sql.split()), params))
        self.current = self.responses.pop(0) if self.responses else None

    def executemany(self, sql, params_seq):
        params = list(params_seq)
        self.queries.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.current

    def fetchall(self):
        return self.current or []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _patch(monkeypatch, module, cursor: _Cursor):
    @contextmanager
    def fake():
        yield type("Conn", (), {"cursor": lambda _self: cursor})()

    monkeypatch.setattr(module, "get_connection", fake)
    return cursor


# ---- правило ----


@pytest.mark.parametrize(
    ("scope", "city", "format_name", "expected"),
    [
        ("screens", "", "Видеоэкран", "screens"),
        ("other", "Ростов-на-Дону", "Щит", "rostov"),
        ("other", "Ростов-на-Дону", "Сити-формат", "small"),
        ("other", "Таганрог", "Щит", "cities"),
        ("other", "АЗОВСКИЙ РАЙОН", "Щит", "roads"),
        ("other", "ТРАССА М-4", "Щит", "roads"),
        ("other", "Ростов-на-Дону", "", "unknown"),
    ],
)
def test_the_same_rule_covers_every_button(scope, city, format_name, expected):
    assert directory_mod.address_tab(scope, city, format_name) == expected


# ---- пересчёт ----


def test_recompute_writes_only_changed_rows(monkeypatch):
    cursor = _patch(
        monkeypatch,
        directory_mod,
        _Cursor(
            responses=[
                [
                    (1, "screens", "", "Видеоэкран", "screens"),
                    (2, "other", "Ростов-на-Дону", "Щит", None),
                    (3, "other", "Таганрог", "Щит", "rostov"),
                ]
            ]
        ),
    )

    result = directory_mod.recompute_panel_groups()

    assert result["total"] == 3
    assert result["changed"] == 2
    assert result["counts"]["screens"] == 1
    assert result["counts"]["rostov"] == 1
    assert result["counts"]["cities"] == 1

    written = [query for query in cursor.queries if "SET panel_group" in query[0]]
    assert len(written) == 1
    assert written[0][1] == [("rostov", 2), ("cities", 3)]


def test_recompute_dry_run_does_not_write(monkeypatch):
    cursor = _patch(
        monkeypatch,
        directory_mod,
        _Cursor(responses=[[(1, "other", "Таганрог", "Щит", None)]]),
    )

    result = directory_mod.recompute_panel_groups(dry_run=True)

    assert result["changed"] == 1
    assert result["dry_run"] is True
    assert not [query for query in cursor.queries if "panel_group = %s" in query[0]]


# ---- запись при разборе XLS ----


def _import_cursor(existing=None):
    return _Cursor(responses=[existing] if existing is not None else [])


def test_import_writes_the_group_for_a_new_address(monkeypatch):
    cursor = _patch(monkeypatch, directory_mod, _import_cursor())

    directory_mod.import_addresses(
        [
            {
                "legal_address": "ООО «Тест»",
                "simple_address": "Тест",
                "format": "Щит",
                "city": "Ростов-на-Дону",
            }
        ]
    )

    insert = next(query for query in cursor.queries if "INSERT INTO public.address_directory" in query[0])
    assert "panel_group" in insert[0]
    # Щит в Ростове — «Р-н-Д 6х3».
    assert insert[1][-1] == "rostov"


def test_import_recomputes_the_group_of_an_existing_address(monkeypatch):
    cursor = _patch(
        monkeypatch,
        directory_mod,
        _import_cursor(existing=(5, "", "ООО «Тест»", "", "", "other", "cities")),
    )

    directory_mod.import_addresses(
        [
            {
                "legal_address": "ООО «Тест»",
                "format": "Щит",
                "city": "Ростов-на-Дону",
            }
        ]
    )

    written = [query for query in cursor.queries if "SET panel_group" in query[0]]
    assert written and written[0][1] == ("rostov", 5)


def test_import_does_not_rewrite_an_equal_group(monkeypatch):
    cursor = _patch(
        monkeypatch,
        directory_mod,
        _import_cursor(existing=(5, "", "ООО «Тест»", "Щит", "Таганрог", "other", "cities")),
    )

    directory_mod.import_addresses([{"legal_address": "ООО «Тест»"}])

    assert not [query for query in cursor.queries if "SET panel_group" in query[0]]


# ---- фильтр в SQL ----


def test_panel_filters_by_group_before_any_limit(monkeypatch):
    cursor = _patch(monkeypatch, repository, _Cursor(responses=[[], (0, 0), []]))

    repository.list_addresses(group="roads")

    sql, params = cursor.queries[0]
    assert "d.panel_group = %s" in sql
    # Список адресов отдаётся целиком: усечение прятало адреса от панели.
    # (LIMIT внутри CTE с последним вердиктом не считается — он про другое.)
    assert "LIMIT %s" not in sql
    assert params == ["roads"]


def test_panel_keeps_the_parameters_in_query_order(monkeypatch):
    cursor = _patch(monkeypatch, repository, _Cursor(responses=[[], (0, 0), []]))

    repository.list_addresses(
        group="roads",
        clients=["Клиент"],
        date_from="2026-10-01",
        limit=10,
    )

    sql, params = cursor.queries[0]
    # Плейсхолдеры идут по тексту: клиенты → период → закладка → предел.
    assert sql.index("ca.canonical") < sql.index("e.created_at")
    assert sql.index("e.created_at") < sql.index("d.panel_group")
    assert sql.index("d.panel_group") < sql.rindex("LIMIT %s")
    assert params == ["Клиент", "Клиент", "2026-10-01", "roads", 10]


def test_ids_for_tab_are_taken_from_the_stored_group(monkeypatch):
    cursor = _patch(monkeypatch, directory_mod, _Cursor(responses=[[(7,), (9,)]]))

    assert directory_mod.address_ids_for_tab("rows") == [7, 9]
    sql, params = cursor.queries[0]
    assert "WHERE active AND panel_group = %s" in sql
    assert params == ("rows",)


def test_the_panel_route_asks_for_the_group(monkeypatch):
    seen: dict = {}

    def fake_list(**kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(routes.repository, "list_addresses", fake_list)
    monkeypatch.setattr(routes.repository, "collection_panel_filter", lambda _ids: (None, []))

    assert routes.list_addresses(
        limit=None,
        date_from=None,
        date_to=None,
        date_mode="upload",
        client=None,
        group="small",
    ) == {"items": []}

    assert seen["group"] == "small"
    assert seen["limit"] is None

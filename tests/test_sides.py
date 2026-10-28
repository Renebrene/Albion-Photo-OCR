"""
Стороны и поверхности: правила перенесены из проекта «Сайт».

Проверяется то, о чём договорились с владельцем (28.10.2026): поверхности
сводятся к стороне везде, кроме щитов и видеоэкранов.
"""

from __future__ import annotations

from app.api import sides


def test_splits_the_side_from_the_legal_address():
    base, side = sides.split_legal_side("339 Стрелковой Дивизии, 7/ Содружества ул., A1")

    assert base == "339 Стрелковой Дивизии, 7/ Содружества ул."
    assert side == "A1"


def test_tolerates_marks_after_the_side():
    assert sides.split_legal_side("Комарова б-р 20В / Добровольского 9А п. 3, B***") == (
        "Комарова б-р 20В / Добровольского 9А п. 3",
        "B",
    )


def test_an_address_without_a_side_stays_whole():
    assert sides.split_legal_side("ООО «Ромашка», ул. Мира, 1") == (
        "ООО «Ромашка», ул. Мира, 1",
        "",
    )


def test_bare_numbers_collapse_outside_shields_and_screens():
    """Вне щита и экрана «A1» — поверхность стороны A."""

    assert sides.parent_side("A1", "Сити-формат") == "A"
    assert sides.parent_side("A2", "Призматрон") == "A"


def test_surface_index_collapses_on_any_format():
    assert sides.parent_side("A(1)", "Призматрон") == "A"
    assert sides.parent_side("A1(2)", "Сити-формат") == "A1"
    assert sides.parent_side("A(3)", "Видеоэкран") == "A"


def test_a_shield_keeps_its_labels_as_separate_sides():
    """У щита A1 и A2 — разные стороны, их не сводим (задание, п. г)."""

    assert sides.parent_side("A1", "Щит") == "A1"
    assert sides.parent_side("A2", "Щит") == "A2"
    assert sides.parent_side("A(1)", "Щит") == "A(1)"


def test_a_screen_keeps_a_bare_number_as_a_side():
    assert sides.parent_side("A1", "Видеоэкран") == "A1"
    # Индекс в скобках у экрана — уже поверхность.
    assert sides.parent_side("A(1)", "Видеоэкран") == "A"


def test_groups_surfaces_into_sides():
    rows = [
        {"legal_address": "40 Лет Победы 232, A(1)", "format": "Призматрон", "city": "Ростов-на-Дону", "scope": "other", "address_id": 1},
        {"legal_address": "40 Лет Победы 232, A(2)", "format": "Призматрон", "city": "Ростов-на-Дону", "scope": "other", "address_id": 2},
        {"legal_address": "40 Лет Победы 232, A(3)", "format": "Призматрон", "city": "Ростов-на-Дону", "scope": "other", "address_id": 3},
    ]

    groups = sides.group_surfaces(rows)

    assert len(groups) == 1
    assert groups[0]["side"] == "A"
    assert groups[0]["count"] == 3
    assert [item["side"] for item in groups[0]["surfaces"]] == ["A(1)", "A(2)", "A(3)"]


def test_a_shield_keeps_a1_and_a2_as_two_sides():
    rows = [
        {"legal_address": "339 Стрелковой Дивизии, 7/ Содружества ул., A1", "format": "Щит", "scope": "other", "address_id": 1},
        {"legal_address": "339 Стрелковой Дивизии, 7/ Содружества ул., A2", "format": "Щит", "scope": "other", "address_id": 2},
    ]

    groups = sides.group_surfaces(rows)

    assert [group["side"] for group in groups] == ["A1", "A2"]
    assert all(group["count"] == 1 for group in groups)


def _registry_row(address_id, legal, simple, format_name, city, scope):
    """Строка в порядке _REGISTRY_SELECT (индексы 11..18)."""
    return (
        "78_v33", "", "", "3.3", "dinov2", 768, 19, "", True, None, None,
        address_id, legal, simple, format_name, city, scope, 19, None,
    )


def test_fingerprint_tab_follows_its_address():
    from app.api import fingerprints

    screens = fingerprints._row_to_fingerprint(
        _registry_row(1, "Комарова 13, A", "Комарова", "Видеоэкран", "Ростов-на-Дону", "screens")
    )
    city = fingerprints._row_to_fingerprint(
        _registry_row(2, "Таганрогская ул. 157/2, A", "", "Щит", "Таганрог", "other")
    )

    assert screens["tab"] == "screens"
    assert screens["address"]["format"] == "Видеоэкран"
    assert city["tab"] == "cities"
    assert city["address"]["city"] == "Таганрог"


def test_fingerprint_without_an_address_has_no_tab():
    from app.api import fingerprints

    item = fingerprints._row_to_fingerprint(
        _registry_row(None, None, None, None, None, None)
    )

    assert item["address"] is None
    assert item["tab"] == ""


def test_different_formats_on_one_base_do_not_merge():
    """Щит и призматрон по одному адресу — разные блоки, как на сайте."""

    rows = [
        {"legal_address": "40 Лет Победы 113, A", "format": "Щит", "scope": "other", "address_id": 1},
        {"legal_address": "40 Лет Победы 113, A", "format": "Призматрон", "scope": "other", "address_id": 2},
    ]

    groups = sides.group_surfaces(rows)

    assert len(groups) == 2
    assert {group["format"] for group in groups} == {"Щит", "Призматрон"}


def _panel_row(address_id, legal, format_name, count, period_count, fingerprints=None):
    return {
        "address": f"addr:{address_id}",
        "address_id": address_id,
        "name": legal,
        "simple_address": "",
        "legal_address": legal,
        "format": format_name,
        "city": "Ростов-на-Дону",
        "scope": "other",
        "fingerprints": list(fingerprints or []),
        "count": count,
        "period_count": period_count,
        "review": False,
    }


def test_panel_merges_surfaces_into_one_side(monkeypatch):
    """Левая панель отдаёт сторону, а не три поверхности призматрона."""

    from app.api import routes

    rows = [
        _panel_row(1, "40 Лет Победы 232, A(1)", "Призматрон", 3, 1, ["78_v33"]),
        _panel_row(2, "40 Лет Победы 232, A(2)", "Призматрон", 2, 1),
        _panel_row(3, "339 Стрелковой Дивизии, 7/ Содружества ул., A1", "Щит", 4, 0),
        _panel_row(4, "339 Стрелковой Дивизии, 7/ Содружества ул., A2", "Щит", 1, 0),
    ]

    monkeypatch.setattr(routes.repository, "list_addresses", lambda **kwargs: rows)

    items = routes.list_addresses(
        limit=100, date_from=None, date_to=None, date_mode="upload", client=None, group=None
    )["items"]

    # Призматрон A(1)+A(2) — одна строка; щит A1 и A2 — две разные.
    assert len(items) == 3

    prism = next(item for item in items if item["format"] == "Призматрон")
    assert prism["ids"] == [1, 2]
    assert prism["side"] == "A"
    assert prism["count"] == 5
    assert prism["period_count"] == 2
    assert prism["fingerprints"] == ["78_v33"]

    shield_sides = sorted(item["side"] for item in items if item["format"] == "Щит")
    assert shield_sides == ["A1", "A2"]


def test_panel_can_be_narrowed_to_a_group(monkeypatch):
    from app.api import routes

    rows = [
        _panel_row(1, "40 Лет Победы 232, A(1)", "Призматрон", 3, 1),
        _panel_row(2, "Таганрогская ул. 157/2, A", "Щит", 4, 0),
    ]
    rows[1]["city"] = "Таганрог"

    monkeypatch.setattr(routes.repository, "list_addresses", lambda **kwargs: rows)

    items = routes.list_addresses(
        limit=100, date_from=None, date_to=None, date_mode="upload", client=None, group="cities"
    )["items"]

    assert len(items) == 1
    assert items[0]["city"] == "Таганрог"

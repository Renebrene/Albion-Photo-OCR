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


def test_different_formats_on_one_base_do_not_merge():
    """Щит и призматрон по одному адресу — разные блоки, как на сайте."""

    rows = [
        {"legal_address": "40 Лет Победы 113, A", "format": "Щит", "scope": "other", "address_id": 1},
        {"legal_address": "40 Лет Победы 113, A", "format": "Призматрон", "scope": "other", "address_id": 2},
    ]

    groups = sides.group_surfaces(rows)

    assert len(groups) == 2
    assert {group["format"] for group in groups} == {"Щит", "Призматрон"}

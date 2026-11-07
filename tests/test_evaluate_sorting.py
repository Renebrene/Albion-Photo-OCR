from __future__ import annotations

import scripts.evaluate_sorting as evaluate_sorting


def test_intersection_matches_reversed_street_order(monkeypatch):
    addresses = [
        (144, "дачнаявавилова"),
        (211, "зоргестачки"),
        (147, "вавилова52"),
        (158, "зорге46"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            144: "Дачная / Вавилова",
            211: "Зорге / Стачки",
            147: "Вавилова 52",
            158: "Зорге 46",
        },
    )
    monkeypatch.setattr(evaluate_sorting, "COVERED_ADDRESSES", {144, 211, 147, 158})

    assert (
        evaluate_sorting.expected_address(
            "Вавилова ул. - Дачная ул., A (1).JPG", addresses
        )
        == 144
    )
    assert (
        evaluate_sorting.expected_address(
            "Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (12).jpg",
            addresses,
        )
        == 211
    )
    assert (
        evaluate_sorting.expected_address("Зорге 46 (2).JPG", addresses)
        == 158
    )


def test_intersection_prefers_covered_address(monkeypatch):
    addresses = [
        (211, "зоргестачки"),
        (2413, "стачкипрктзоргеулb"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            211: "Зорге / Стачки",
            2413: "Стачки пр-кт / Зорге ул., B",
        },
    )
    monkeypatch.setattr(evaluate_sorting, "COVERED_ADDRESSES", {211})

    assert (
        evaluate_sorting.expected_address("Стачки Зорге А (1).JPG", addresses)
        == 211
    )


def test_filename_aliases(monkeypatch):
    addresses = [
        (226, "шеболдаева8"),
        (168, "королевавозлемоста"),
        (146, "технологический"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            226: "Шеболдаева 8",
            168: "Королева возле моста",
            146: "Технологический",
        },
    )
    monkeypatch.setattr(
        evaluate_sorting,
        "ALIAS_ADDRESS_IDS",
        {
            ("шеболдаева", "риижт"): 226,
            ("королева", "мост"): 168,
            ("вавилова", "технологический"): 146,
        },
    )
    monkeypatch.setattr(evaluate_sorting, "COVERED_ADDRESSES", {226, 168, 146})

    assert (
        evaluate_sorting.expected_address(
            "Шеболдаева РИИЖТ А (1).JPG", addresses
        )
        == 226
    )
    assert (
        evaluate_sorting.expected_address("Королева мост А (1).JPG", addresses)
        == 168
    )
    assert (
        evaluate_sorting.expected_address(
            "Вавилова ул. - Технологический пер., B (1).JPG", addresses
        )
        == 146
    )


def test_side_aware_ab(monkeypatch):
    addresses = [
        (218, "таганрогская147а"),
        (219, "таганрогская147б"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {218: "Таганрогская 147 А", 219: "Таганрогская 147 Б"},
    )
    monkeypatch.setattr(evaluate_sorting, "COVERED_ADDRESSES", {218, 219})

    assert (
        evaluate_sorting.expected_address("Таганрогская 147 А (1).JPG", addresses)
        == 218
    )
    assert (
        evaluate_sorting.expected_address("Таганрогская 147 Б (1).JPG", addresses)
        == 219
    )


def test_unrelated_filename_is_not_guessed(monkeypatch):
    addresses = [(144, "дачнаявавилова")]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {144: "Дачная / Вавилова"},
    )
    monkeypatch.setattr(evaluate_sorting, "COVERED_ADDRESSES", {144})

    assert evaluate_sorting.expected_address("IMG_1017.JPG", addresses) is None

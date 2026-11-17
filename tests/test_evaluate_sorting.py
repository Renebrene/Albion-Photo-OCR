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


def test_side_letter_after_house_number(monkeypatch):
    addresses = [
        (206, "сальский3133"),
        (186, "ленина125127"),
        (194, "малиновского915"),
        (192, "малиновского25настачки"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            206: "Сальский 31-33",
            186: "Ленина 125-127",
            194: "Малиновского 9/15",
            192: "Малиновского 25 на Стачки",
        },
    )
    monkeypatch.setattr(
        evaluate_sorting, "COVERED_ADDRESSES", {206, 186, 194, 192}
    )

    assert (
        evaluate_sorting.expected_address("Сальский 31 А (5).JPG", addresses)
        == 206
    )
    assert (
        evaluate_sorting.expected_address("Ленина 125 А (1).JPG", addresses)
        == 186
    )
    assert (
        evaluate_sorting.expected_address("Малиновского 9 А (18).JPG", addresses)
        == 194
    )
    # Одна улица без номера адреса не угадывается между адресами.
    assert (
        evaluate_sorting.expected_address("Малиновского (7).JPG", addresses)
        is None
    )


def test_owner_confirmed_aliases(monkeypatch):
    addresses = [
        (220, "таганрогская157"),
        (174, "космонавтов1416аквадро"),
        (190, "ленина217жд"),
        (164, "комарова13"),
        (209, "вагулевскоголевый"),
        (210, "вагулевскогоправый"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            220: "Таганрогская 157",
            174: "Космонавтов 14-16 А на квадро",
            190: "Ленина 217 / ЖД",
            164: "Комарова 13",
            209: "Вагулевского (левый)",
            210: "Вагулевского (правый)",
        },
    )
    monkeypatch.setattr(
        evaluate_sorting,
        "ALIAS_ADDRESS_IDS",
        {
            ("таганрогская", "1572"): 220,
            ("космонавтов", "сжм"): 174,
            ("ленина", "жд"): 190,
            ("комарвоа",): 164,
            ("вагулевского", "левый"): 209,
            ("вагулевского", "правый"): 210,
        },
    )
    monkeypatch.setattr(
        evaluate_sorting, "COVERED_ADDRESSES", {220, 174, 190, 164, 209, 210}
    )

    assert (
        evaluate_sorting.expected_address(
            "Таганрогская ул. 1572, А (43).JPG", addresses
        )
        == 220
    )
    assert (
        evaluate_sorting.expected_address(
            "Космонавтов 14-16 на СЖМ (8).JPG", addresses
        )
        == 174
    )
    assert (
        evaluate_sorting.expected_address("ленина_ЖД_007.JPG", addresses)
        == 190
    )
    assert (
        evaluate_sorting.expected_address(
            "Комарвоа 13 Космонавтов А (8).JPG", addresses
        )
        == 164
    )
    # Латинская B в «Bагулевского» не мешает: токены переводят омоглифы.
    assert (
        evaluate_sorting.expected_address(
            "Стачки  Bагулевского - пл. Стачки 1902 года (позиция 1) левый, A(1).JPG",
            addresses,
        )
        == 209
    )


def test_kosmonavtov_14_16_is_14a(monkeypatch):
    """17.11.2026: «Космонавтов 14 в центр» и «14-16» — это Космонавтов 14а;
    отдельные позиции (СЖМ, Квадро) остаются своими адресами."""
    addresses = [
        (173, "космонавтов14а"),
        (174, "космонавтов1416аквадро"),
        (175, "космонавтов1416бвцентр"),
        (179, "космонавтов42бвцентр"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            173: "Космонавтов 14а",
            174: "Космонавтов 14-16 А на квадро",
            175: "Космонавтов 14-16 Б в центр",
            179: "Космонавтов 42 Б в центр",
        },
    )
    monkeypatch.setattr(
        evaluate_sorting,
        "ALIAS_ADDRESS_IDS",
        {
            ("космонавтов", "сжм"): 174,
            ("космонавтов", "квадро"): 174,
            ("космонавтов", "14", "16"): 173,
            ("космонавтов", "14", "центр"): 173,
            ("космонавтов", "42", "центр"): 179,
        },
    )
    monkeypatch.setattr(
        evaluate_sorting, "COVERED_ADDRESSES", {173, 174, 175, 179}
    )

    assert (
        evaluate_sorting.expected_address("Космонавтов 14 в центр.JPG", addresses)
        == 173
    )
    # «Б в центр» в имени — по решению владельца это тоже 14а.
    assert (
        evaluate_sorting.expected_address(
            "Космонавтов 14-16 Б в центр (5).JPG", addresses
        )
        == 173
    )
    # Голый «14-16» — 14а.
    assert (
        evaluate_sorting.expected_address("Космонавтов 14-16 (2).JPG", addresses)
        == 173
    )
    # Позиции со своими словами остаются отдельными адресами.
    assert (
        evaluate_sorting.expected_address(
            "Космонавтов 14-16 на СЖМ (8).JPG", addresses
        )
        == 174
    )
    assert (
        evaluate_sorting.expected_address(
            "Космонавтов 14-16 А на квадро (1).JPG", addresses
        )
        == 174
    )
    # «42 в центр» без буквы — адрес 42 Б в центр, а не 14-16.
    assert (
        evaluate_sorting.expected_address(
            "Космонавтов 42 в центр (3).JPG", addresses
        )
        == 179
    )


def test_intersection_ignores_house_numbers(monkeypatch):
    addresses = [
        (188, "ашхабадскийленина44"),
        (221, "шолохова242тебердинский"),
        (169, "королева1012"),
    ]
    monkeypatch.setattr(
        evaluate_sorting,
        "ADDRESS_NAMES",
        {
            188: "Ашхабадский / Ленина 44",
            221: "Шолохова 242 / Тебердинский",
            169: "Королева 10-12",
        },
    )
    monkeypatch.setattr(
        evaluate_sorting, "COVERED_ADDRESSES", {188, 221, 169}
    )

    # В адресе есть номер дома, которого нет в имени файла, — пересечение
    # всё равно должно сработать по двум улицам.
    assert (
        evaluate_sorting.expected_address(
            "Ленина Ашхабадский А (16).JPG", addresses
        )
        == 188
    )
    assert (
        evaluate_sorting.expected_address("шолохова тебердинский (3).JPG", addresses)
        == 221
    )
    # Одна общая улица — это не пересечение: пересечение не срабатывает
    # (голая улица может совпасть префиксом, если адрес улицы один).
    assert (
        evaluate_sorting._intersection_match("Королева (2).JPG", addresses)
        is None
    )
    assert (
        evaluate_sorting.expected_address("Королева (2).JPG", addresses)
        == 169
    )

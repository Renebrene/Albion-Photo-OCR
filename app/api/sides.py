"""
Стороны и поверхности рекламных конструкций.

Правила перенесены из проекта «Сайт»
(``albion_yandex_maps_presentation_demo/frontend/src/utils/constructionGroups.js``),
чтобы адреса в PhotoBase показывались так же, как на сайте:

    Конструкция = адрес + формат (один объект);
    Сторона     = A, B, C, а на разделительной полосе — A1, A2;
    Поверхность = A(1), A(2), A1(2)… — лежит на стороне.

    «Щит»      — любая подпись это сторона (щит статичен, поверхностей нет);
    «Экран»    — голая «A1» это сторона, а «A(1)» — уже поверхность;
    остальные  — «A1(2)» → «A1», «A(3)» → «A», голая «A1» → «A».

Так «Призматрон A(1) + A(2) + A(3)» становится одной стороной A, а у щита
A1 и A2 остаются разными сторонами (задание владельца, 28.10.2026).
"""

from __future__ import annotations

import re

# Сторона — хвост юридического адреса после запятой: «…, A», «…, A(1)»,
# «…, A1(2)», с возможными звёздочками-пометками («…, B*») и пробелами.
_SIDE_SUFFIX = re.compile(
    r",\s*([A-Za-zА-Яа-я]{1,3}\d*(?:\(\d+\))?)\s*\**\s*$"
)

_BARE_LETTER_NUMBER = re.compile(r"^[A-ZА-Я]+\d+$")
_SURFACE_INDEX = re.compile(r"\(\d+\)")

# Кириллические двойники латинских букв встречаются в названиях («…, А»), а в
# колонке «Сторона» сайта — латиница. Без нормализации одна и та же сторона
# попадала в две группы.
_HOMOGLYPHS = str.maketrans(
    "АВСЕНКМОРТХУ",
    "ABCEHKMOPTXY",
)


def _latin_side(value: str) -> str:
    return str(value or "").upper().strip().translate(_HOMOGLYPHS)


def split_legal_side(legal_address: str) -> tuple[str, str]:
    """
    Разделить юридический адрес на основу и подпись стороны.

    «339 Стрелковой Дивизии, 7/ Содружества ул., A1» → («…, 7/ Содружества
    ул.», «A1»). Если хвост не похож на сторону — сторона пустая.
    """

    text = " ".join(str(legal_address or "").replace("\xa0", " ").split())
    match = _SIDE_SUFFIX.search(text)

    if not match:
        return text, ""

    return text[: match.start()].strip(), _latin_side(match.group(1))


def is_shield_format(format_name: str) -> bool:
    return "щит" in str(format_name or "").lower()


def is_screen_format(format_name: str) -> bool:
    return "экран" in str(format_name or "").lower()


def parent_side(side: str, format_name: str) -> str:
    """Сторона, к которой относится подпись поверхности."""

    value = _latin_side(side)

    if not value:
        return ""

    # Щит: любая подпись — уже сторона, индекс не отбрасываем.
    if is_shield_format(format_name):
        return value

    # Индекс поверхности в скобках: «A(1)» → «A», «A1(2)» → «A1».
    if _SURFACE_INDEX.search(value):
        return _SURFACE_INDEX.sub("", value).strip()

    # Голая «A1»: у экрана это сторона, вне экрана — поверхность стороны A.
    if _BARE_LETTER_NUMBER.match(value):
        return value if is_screen_format(format_name) else re.sub(r"\d+$", "", value)

    return value


def group_surfaces(rows: list[dict]) -> list[dict]:
    """
    Свести адреса-поверхности в стороны.

    Возвращает группы в порядке первого появления: основа адреса, формат,
    сторона и её поверхности. Разные форматы на одном адресе не смешиваются —
    ключ группы включает формат, как на сайте.
    """

    groups: list[dict] = []
    by_key: dict[tuple[str, str, str], dict] = {}

    for item in rows:
        base, side = split_legal_side(item.get("legal_address", ""))
        key = (base.casefold(), str(item.get("format") or "").strip().casefold(),
               parent_side(side, item.get("format")))

        group = by_key.get(key)

        if group is None:
            group = {
                "base": base,
                "format": item.get("format") or "",
                "side": parent_side(side, item.get("format")),
                "city": item.get("city") or "",
                "scope": item.get("scope") or "",
                # Короткое имя берём с первой поверхности, где оно заполнено:
                # это подпись адреса, а не отдельной поверхности.
                "simple": "",
                "surfaces": [],
            }
            by_key[key] = group
            groups.append(group)

        if not group["simple"] and item.get("simple_address"):
            group["simple"] = item["simple_address"]

        group["surfaces"].append(
            {
                "address_id": item.get("address_id"),
                "legal_address": item.get("legal_address"),
                "side": side,
                "fingerprints": list(item.get("fingerprints") or []),
            }
        )

    for group in groups:
        group["count"] = len(group["surfaces"])

    return groups

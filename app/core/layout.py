"""
Keyboard-layout helpers for the search bar.

A user searching in the wrong layout types «rjvfyjdf» instead of «комарова».
Swapping each character through the ЙЦУКЕН/QWERTY map recovers the intended
word, so the search line can offer a corrected suggestion. Pure functions:
no database, no I/O.
"""

from __future__ import annotations

_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU = "йцукенгшщзхъфывапролджэячсмитьбю.ё"

_LAYOUT_MAP = {
    **dict(zip(_EN, _RU)),
    **dict(zip(_RU, _EN)),
}


def to_other_layout(text: str) -> str:
    """Swap each character between the English and Russian layouts."""

    result: list[str] = []

    for char in str(text):
        mapped = _LAYOUT_MAP.get(char.lower())

        if mapped is None:
            result.append(char)
            continue

        result.append(mapped.upper() if char.isupper() else mapped)

    return "".join(result)


def looks_like_wrong_layout(text: str) -> bool:
    """True when at least half of the letters can be swapped to the other layout."""

    letters = [char for char in str(text) if char.isalpha()]

    if not letters:
        return False

    mappable = sum(1 for char in letters if char.lower() in _LAYOUT_MAP)

    return mappable / len(letters) >= 0.5

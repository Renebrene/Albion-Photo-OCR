"""User colours reach CSS variables — only strict HEX is accepted."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import UserCreate, UserUpdate


@pytest.mark.parametrize("color", ["#1976d2", "#fff", "#1976d2ff"])
def test_valid_hex_colours(color):
    assert UserCreate(name="x", color=color).color == color
    assert UserUpdate(color=color).color == color


@pytest.mark.parametrize(
    "color",
    [
        "red",
        "#12345",
        "#1234567",
        "url(https://evil.example/x)",
        "#fff; background:url(https://evil.example/x)",
        "rgb(1,2,3)",
    ],
)
def test_invalid_colours_are_rejected(color):
    with pytest.raises(ValidationError):
        UserCreate(name="x", color=color)

    with pytest.raises(ValidationError):
        UserUpdate(color=color)


def test_colour_may_be_omitted():
    assert UserCreate(name="x").color is None
    assert UserUpdate().color is None

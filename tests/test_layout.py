"""Keyboard-layout conversion used by the search suggestions."""

from app.core.layout import looks_like_wrong_layout, to_other_layout


def test_english_layout_is_converted_to_russian():
    assert to_other_layout("rjvfhjdf") == "комарова"
    assert to_other_layout("hzpfyrf") == "рязанка"


def test_russian_layout_is_converted_to_english():
    assert to_other_layout("комарова") == "rjvfhjdf"


def test_case_is_preserved():
    assert to_other_layout("Rjvfhjdf") == "Комарова"
    assert to_other_layout("Комарова") == "Rjvfhjdf"


def test_non_mapped_characters_pass_through():
    assert to_other_layout("дом 13") == "ljv 13"


def test_layout_detection():
    assert looks_like_wrong_layout("rjvfyjdf")
    assert looks_like_wrong_layout("комарова")
    assert not looks_like_wrong_layout("")

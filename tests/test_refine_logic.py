"""
Правила «Уточнения»: серии и предложения по значениям (без базы).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.refine.logic import (
    Frame,
    build_groups,
    is_variant,
    propose,
    skeleton,
)


def _frame(photo_id, *, screen="78_v33", seconds=0, phash=0, client=None, brand=None):
    return Frame(
        photo_id=photo_id,
        screen=screen,
        taken_at=datetime(2026, 10, 1, 12, 0) + timedelta(seconds=seconds),
        phash=phash,
        client=client,
        brand=brand,
    )


# ---- нормализация имён -----------------------------------------------------


def test_skeleton_ignores_case_spaces_and_punctuation():
    assert skeleton("Ozon Fresh") == skeleton("ozon-fresh")


def test_skeleton_strips_legal_forms():
    assert skeleton("ООО «ЛЕНТА»") == skeleton("Лента")
    assert skeleton("ПАО Сбербанк") == skeleton("Сбербанк")


def test_skeleton_normalizes_yo():
    assert skeleton("Медрокёт") == skeleton("Медрокет")


def test_skeleton_folds_latin_and_cyrillic_lookalikes():
    assert skeleton("MTC") == skeleton("МТС")


def test_variant_is_strict_prefix():
    assert is_variant("Ян", "Яндекс") is True
    assert is_variant("Яндекс", "Ян") is False
    assert is_variant("Яндекс", "Яндекс") is False


# ---- серии -----------------------------------------------------------------


def test_groups_split_by_gap():
    frames = [
        _frame("a", seconds=0),
        _frame("b", seconds=10),
        _frame("c", seconds=100),
    ]

    groups = build_groups(frames, gap_seconds=30)

    assert [[frame.photo_id for frame in group] for group in groups] == [["a", "b"], ["c"]]


def test_groups_split_by_hash_distance():
    frames = [
        _frame("a", seconds=0, phash=0b0000),
        _frame("b", seconds=5, phash=0b0000),
        _frame("c", seconds=10, phash=0b1111_1111),
    ]

    groups = build_groups(frames, gap_seconds=30, max_distance=2)

    assert [[frame.photo_id for frame in group] for group in groups] == [["a", "b"], ["c"]]


def test_groups_split_by_screen():
    frames = [_frame("a", screen="78_v33"), _frame("b", screen="79_v33", seconds=5)]

    groups = build_groups(frames, gap_seconds=30)

    assert len(groups) == 2


def test_frames_without_time_are_not_grouped():
    frames = [_frame("a"), Frame("b", "78_v33", None, 0, "Яндекс", None)]

    groups = build_groups(frames, gap_seconds=30)

    assert [[frame.photo_id for frame in group] for group in groups] == [["a"]]


# ---- предложения -----------------------------------------------------------


def test_empty_value_is_filled_from_the_group():
    group = [
        _frame("a", seconds=0, brand="Яндекс"),
        _frame("b", seconds=5, brand=""),
    ]

    proposal = propose(group, "brand")

    assert proposal == {"fill": {"b": "Яндекс"}, "replace": {}, "disputed": []}


def test_short_reading_is_replaced_with_the_full_one():
    group = [
        _frame("a", seconds=0, brand="Ян"),
        _frame("b", seconds=5, brand="Яндекс"),
        _frame("c", seconds=10, brand="Яндекс"),
    ]

    proposal = propose(group, "brand")

    assert proposal["fill"] == {}
    assert proposal["replace"] == {"a": ("Ян", "Яндекс")}
    assert proposal["disputed"] == []


def test_different_names_make_the_group_disputed():
    group = [
        _frame("a", seconds=0, brand="Мираторг"),
        _frame("b", seconds=5, brand="МИРАТОРП PRIME SKIN"),
    ]

    proposal = propose(group, "brand")

    assert proposal["fill"] == {}
    assert proposal["replace"] == {}
    assert proposal["disputed"]


def test_single_frame_group_changes_nothing():
    proposal = propose([_frame("a", brand="Ян")], "brand")

    assert proposal == {"fill": {}, "replace": {}, "disputed": []}


def test_group_without_values_changes_nothing():
    group = [_frame("a", seconds=0), _frame("b", seconds=5)]

    assert propose(group, "client") == {"fill": {}, "replace": {}, "disputed": []}


# ---- прогон без включения --------------------------------------------------


def test_disabled_stage_reports_and_does_nothing(monkeypatch):
    from app.refine import config as refine_config
    from app.refine import runner

    monkeypatch.setattr(refine_config, "enabled", lambda: False)
    monkeypatch.setattr(
        runner,
        "load_frames",
        lambda *_args, **_kwargs: pytest.fail("кадры не должны читаться"),
    )

    report = runner.run_refine(limit=10)

    assert report["status"] == "disabled"
    assert report["photos_changed"] == 0

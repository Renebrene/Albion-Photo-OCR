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


def test_refine_is_available_while_qwen_takes_part(monkeypatch):
    """Пока QWEN включён в прогон, «Уточнение» доступно."""
    from app.qwen import processor as qwen_processor
    from app.refine import config as refine_config

    monkeypatch.setattr(qwen_processor, "in_pipeline", lambda: True)
    monkeypatch.setattr(refine_config, "qwen_has_results", lambda: False)

    assert refine_config.available() is True


def test_refine_needs_qwen_results_when_qwen_is_off(monkeypatch):
    """Без QWEN этап доступен только при сохранённых описаниях."""
    from app.qwen import processor as qwen_processor
    from app.refine import config as refine_config

    monkeypatch.setattr(qwen_processor, "in_pipeline", lambda: False)

    monkeypatch.setattr(refine_config, "qwen_has_results", lambda: False)
    assert refine_config.available() is False

    monkeypatch.setattr(refine_config, "qwen_has_results", lambda: True)
    assert refine_config.available() is True


def test_refine_is_not_enqueued_without_qwen(monkeypatch):
    """Воркер не ставит «Уточнение», если сравнивать нечего."""
    from app.jobs import database as jobs_db
    from app.jobs import worker
    from app.refine import config as refine_config

    calls: list[str] = []

    monkeypatch.setattr(refine_config, "enabled", lambda: True)
    monkeypatch.setattr(refine_config, "available", lambda: False)
    monkeypatch.setattr(
        jobs_db, "active_count", lambda job_type: calls.append("active") or 0
    )
    monkeypatch.setattr(
        jobs_db, "enqueue_refine", lambda: calls.append("refine")
    )

    worker._maybe_enqueue_refine()  # noqa: SLF001

    assert calls == []


# ---- прогресс прогона (без базы) -------------------------------------------


def test_refine_reports_progress_per_group(monkeypatch):
    """
    «Уточнение» сообщает прогресс, как остальные этапы.

    Иначе в шапке нечего показать рядом с описаниями: этап идёт своей
    очередью, и «сколько сделано / сколько всего» взять неоткуда.
    """

    from app.refine import config as refine_config
    from app.refine import runner

    monkeypatch.setattr(refine_config, "enabled", lambda: True)
    monkeypatch.setattr(refine_config, "gap_seconds", lambda: 30.0)

    frames = [
        _frame("PH_a", screen="78_v33", seconds=0, client="Лента"),
        _frame("PH_b", screen="78_v33", seconds=5, client=None),
    ]
    monkeypatch.setattr(runner, "load_frames", lambda *_a, **_k: frames)

    seen = []

    # dry_run — чтобы тест не писал в базу: прогресс считается до записи.
    report = runner.run_refine(
        limit=10,
        dry_run=True,
        progress=lambda done, total: seen.append((done, total)),
    )

    # Сначала нулевой отчёт (чтобы «0 / N» появилось сразу), затем по группам
    # до конца.
    assert seen
    assert seen[0][0] == 0
    assert seen[-1][0] == seen[-1][1]
    assert report["status"] == "dry_run"
    assert report["groups"] >= 1

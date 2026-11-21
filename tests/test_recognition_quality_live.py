"""
Живая сводка «Качества»: разбор строк прогона HYBRID без базы.

Ошибка здесь показала бы владельцу неверные проценты по адресам.
"""

from __future__ import annotations

from app.api.recognition_quality_live import build_snapshot, classify_influence


def _row(expected, predicted, *, original=None, changed=False):
    return {
        "photo_id": "PH_" + "0" * 24,
        "filename": "x.jpg",
        "expected": expected,
        "predicted": predicted,
        "original": original,
        "changed": changed,
    }


def test_influence_kind_explains_who_decided():
    assert classify_influence("fp", False) == "dino"
    assert classify_influence("fp", True) == "neighbors"
    # DINO не дал ответа — адрес выбрали серия/соседи.
    assert classify_influence(None, False) == "no_dino"


def test_snapshot_counts_per_address_and_ranks_by_accuracy():
    rows = [
        # Адрес 1: два подписанных, оба верно.
        _row(1, 1, original="fp1"),
        _row(1, 1, original="fp1", changed=True),
        # Адрес 2: один верно, один — ошибка в адрес 1.
        _row(2, 2, original="fp2"),
        _row(2, 1, original="fp2"),
    ]

    snapshot = build_snapshot(
        rows,
        address_names={1: "Адрес 1", 2: "Адрес 2"},
        fingerprint_photos={1: 10, 2: 4},
    )

    assert snapshot["totals"] == {
        "photos": 4,
        "labelled": 4,
        "correct": 3,
        "wrong": 1,
        "no_label": 0,
        "no_prediction": 0,
        "accuracy": 0.75,
    }

    first, second = snapshot["addresses"]

    # Ранжирование — по проценту совпадений.
    assert first["address_id"] == 1
    assert first["accuracy"] == 1.0
    assert first["photos"] == 3  # два своих + один чужой по ошибке
    assert first["fingerprint_photos"] == 10
    assert first["influence"]["kind"] == "dino"
    assert first["influence"]["counts"] == {"dino": 2, "neighbors": 1}

    assert second["address_id"] == 2
    assert second["accuracy"] == 0.5
    assert second["wrong"] == 1
    assert second["confused_with"] == {
        "address_id": 1,
        "name": "Адрес 1",
        "count": 1,
    }


def test_unlabelled_photos_count_in_the_address_but_not_the_percentage():
    rows = [
        _row(None, 5, original="fp5"),
        _row(None, 5, original="fp5"),
    ]

    snapshot = build_snapshot(
        rows,
        address_names={5: "Адрес 5"},
        fingerprint_photos={},
    )

    assert snapshot["totals"] == {
        "photos": 2,
        "labelled": 0,
        "correct": 0,
        "wrong": 0,
        "no_label": 2,
        "no_prediction": 0,
        "accuracy": None,
    }
    assert snapshot["addresses"][0]["photos"] == 2
    assert snapshot["addresses"][0]["accuracy"] is None


def test_missing_prediction_is_counted_and_named():
    rows = [_row(7, None)]

    snapshot = build_snapshot(
        rows,
        address_names={7: "Адрес 7"},
        fingerprint_photos={7: 3},
    )

    assert snapshot["totals"]["no_prediction"] == 1
    assert snapshot["totals"]["accuracy"] == 0.0
    assert snapshot["addresses"][0]["confused_with"] == {
        "address_id": None,
        "name": "без адреса",
        "count": 1,
    }
    # Фото не отнесено ни к какому адресу, но адрес 7 остался в таблице
    # из-за подписи файла.
    assert snapshot["addresses"][0]["photos"] == 0


def test_empty_run_returns_zeroes():
    snapshot = build_snapshot([], address_names={}, fingerprint_photos={})

    assert snapshot["addresses"] == []
    assert snapshot["totals"]["photos"] == 0
    assert snapshot["totals"]["accuracy"] is None

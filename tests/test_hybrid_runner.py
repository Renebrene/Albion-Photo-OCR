"""HYBRID verdict rules on fixed DINO candidates."""

from __future__ import annotations

from app.hybrid.database import HybridWorkItem
from app.hybrid.runner import hybrid_one


def _candidate(fingerprint_id: str, score: float, best_image: float) -> dict:
    return {
        "id": fingerprint_id,
        "score": score,
        "best_image_score": best_image,
    }


def _item(
    *,
    best: str | None = "a",
    margin: float = 0.005,
    candidates: list[dict] | None = None,
    photo_id: str = "PH_1",
    series_fp: str | None = None,
) -> HybridWorkItem:
    return HybridWorkItem(
        photo_id=photo_id,
        dino_run_id=1,
        dino_best_id=best,
        dino_score=0.9 if best else None,
        dino_second_score=0.89 if best else None,
        dino_margin=margin if best else None,
        dino_confidence="AMBIGUOUS",
        dino_status="AMBIGUOUS",
        candidates=(
            [
                _candidate("a", 0.90, 0.80),
                _candidate("b", 0.89, 0.95),
            ]
            if candidates is None
            else candidates
        ),
        series_fp=series_fp,
    )


def test_no_dino_best_falls_back_to_top_candidate():
    result = hybrid_one([_item(best=None)], 0)

    assert result["hybrid_final_id"] == "a"
    assert result["hybrid_changed"] is True


def test_no_dino_best_without_candidates_stays_unassigned():
    result = hybrid_one([_item(best=None, candidates=[])], 0)

    assert result["hybrid_final_id"] is None
    assert result["hybrid_changed"] is False
    assert result["hybrid_score"] == 0.0


def test_low_margin_prefers_two_neighbour_consensus():
    target = _item(
        candidates=[
            _candidate("a", 0.90, 0.99),
            _candidate("n", 0.80, 0.70),
        ],
        photo_id="PH_target",
    )
    left = _item(best="n", photo_id="PH_left")
    right = _item(best="n", photo_id="PH_right")

    result = hybrid_one([left, target, right], 1)

    assert result["hybrid_final_id"] == "n"
    assert result["hybrid_changed"] is True


def test_low_margin_falls_back_to_best_image_without_consensus():
    target = _item(photo_id="PH_target")
    left = _item(best="l", photo_id="PH_left")
    right = _item(best="r", photo_id="PH_right")

    result = hybrid_one([left, target, right], 1)

    assert result["hybrid_final_id"] == "b"
    assert result["hybrid_changed"] is True


def test_high_margin_does_not_use_best_image():
    result = hybrid_one([_item(margin=0.03)], 0)

    assert result["hybrid_final_id"] == "a"
    assert result["hybrid_changed"] is False


def test_series_consensus_wins_over_neighbours_and_best_image():
    target = _item(
        candidates=[
            _candidate("a", 0.90, 0.99),
            _candidate("s", 0.80, 0.70),
            _candidate("b", 0.89, 0.95),
        ],
        photo_id="PH_target",
        series_fp="s",
    )
    left = _item(best="n", photo_id="PH_left")
    right = _item(best="n", photo_id="PH_right")

    result = hybrid_one([left, target, right], 1)

    assert result["hybrid_final_id"] == "s"
    assert result["hybrid_changed"] is True


def test_no_dino_best_prefers_series_over_top_candidate():
    target = _item(
        best=None,
        series_fp="s",
        candidates=[
            _candidate("a", 0.60, 0.90),
            _candidate("s", 0.50, 0.40),
        ],
        photo_id="PH_target",
    )

    result = hybrid_one([target], 0)

    assert result["hybrid_final_id"] == "s"
    assert result["hybrid_changed"] is True


def test_no_dino_best_prefers_two_neighbour_consensus():
    target = _item(
        best=None,
        candidates=[
            _candidate("a", 0.60, 0.90),
            _candidate("n", 0.50, 0.40),
        ],
        photo_id="PH_target",
    )
    left = _item(best="n", photo_id="PH_left")
    right = _item(best="n", photo_id="PH_right")

    result = hybrid_one([left, target, right], 1)

    assert result["hybrid_final_id"] == "n"
    assert result["hybrid_changed"] is True

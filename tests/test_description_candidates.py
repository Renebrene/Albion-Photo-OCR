from collections import Counter
from datetime import datetime, timedelta
import pytest

from app.refine.description_candidates import (
    DescriptionFrame,
    analyze_adjacent_descriptions,
    text_similarity,
)


T0 = datetime(2026, 10, 1, 12, 0)


def frame(photo_id, seconds, text, *, dhash=0, screen="screen"):
    return DescriptionFrame(photo_id, T0 + timedelta(seconds=seconds), dhash, text, screen)


def test_text_similarity_normalizes_punctuation_and_lookalikes():
    assert text_similarity("BigFest", "BIG-FEST") == 1.0
    assert text_similarity("MTC", "МТС") == 1.0
    assert text_similarity("Ёлка", "елка") == 1.0


@pytest.mark.parametrize(
    ("left", "right"),
    [("BigFest", "Big Feast"), ("Big Fest", "Big Feet"), ("JACOO", "JAECCOO")],
)
def test_user_examples_are_scored_without_assuming_merge(left, right):
    score = text_similarity(left, right)
    assert 0.0 <= score <= 1.0


def test_adjacent_matching_crop_and_text_is_candidate_not_write():
    candidates = analyze_adjacent_descriptions(
        [frame("a", 0, "BigFest"), frame("b", 10, "Big Fest")]
    )
    assert len(candidates) == 1
    assert candidates[0].category == "high-confidence-candidate"
    assert candidates[0].gap_seconds == 10
    assert candidates[0].dhash_distance == 0


def test_time_window_is_inclusive_and_gap_beyond_is_rejected():
    result = analyze_adjacent_descriptions(
        [frame("a", 0, "BigFest"), frame("b", 10.01, "BigFest")]
    )
    assert result[0].category == "reject"
    assert "outside_time_window" in result[0].reasons


def test_crop_hash_mismatch_rejects_even_when_text_matches():
    result = analyze_adjacent_descriptions(
        [frame("a", 0, "BigFest", dhash=0), frame("b", 2, "BigFest", dhash=(1 << 7) - 1)]
    )
    assert result[0].category == "reject"
    assert "crop_dhash_mismatch" in result[0].reasons


def test_crop_hash_distance_six_is_inclusive():
    result = analyze_adjacent_descriptions(
        [frame("a", 0, "BigFest", dhash=0), frame("b", 2, "BigFest", dhash=(1 << 6) - 1)]
    )
    assert result[0].category == "high-confidence-candidate"
    assert result[0].dhash_distance == 6


def test_missing_time_or_hash_never_gets_high_confidence():
    result = analyze_adjacent_descriptions(
        [
            frame("a", 0, "BigFest", dhash=None),
            DescriptionFrame("b", T0 + timedelta(seconds=1), None, "BigFest", "screen"),
            DescriptionFrame("c", None, 0, "BigFest", "screen"),
        ]
    )
    assert len(result) == 1
    assert result[0].category == "reject"
    assert "missing_crop_dhash" in result[0].reasons


def test_short_text_is_review_not_auto_candidate():
    result = analyze_adjacent_descriptions([frame("a", 0, "ABC"), frame("b", 1, "ABD")])
    assert result[0].category == "reject"
    assert "text_too_short_for_high_confidence" in result[0].reasons


def test_only_consecutive_pairs_are_reported_not_transitive_clusters():
    result = analyze_adjacent_descriptions(
        [frame("a", 0, "BigFest"), frame("b", 1, "Big Feast"), frame("c", 2, "Big Feet")]
    )
    assert [(item.left_photo_id, item.right_photo_id) for item in result] == [("a", "b"), ("b", "c")]


def test_different_screen_is_not_high_confidence():
    result = analyze_adjacent_descriptions(
        [frame("a", 0, "BigFest", screen="one"), frame("b", 1, "BigFest", screen="two")]
    )
    assert result[0].category == "reject"
    assert "different_screen" in result[0].reasons


def _synthetic_pair_set():
    """Labeled examples include close spellings and unrelated same-context pairs."""

    positives = [
        ("BigFest", "Big Fest"),
        ("BigFest", "Big Feast"),
        ("JACOO", "JAECCOO"),
        ("MTC", "МТС"),
        ("Ozon Fresh", "Ozon-Fresh"),
        ("Лента", "ООО Лента"),
        ("Медрокёт", "Медрокет"),
        ("Яндекс", "Яндекс"),
    ]
    negatives = [
        ("Big Fest", "Big Feet"),
        ("BigFest", "BigFood"),
        ("Яндекс", "Яндекс Лавка"),
        ("Мираторг", "Мираторп Prime Skin"),
        ("Ozon", "Ozon Bank"),
        ("JACOO", "Jaguar"),
        ("ТВ-3", "Соседи"),
        ("Labo Coffee", "Lebo Coffee"),
        ("", "BigFest"),
    ]
    return positives, negatives


def _score_as_candidate(left, right):
    return text_similarity(left, right) >= 0.85 and min(
        len("".join(char for char in left.lower() if char.isalnum())),
        len("".join(char for char in right.lower() if char.isalnum())),
    ) >= 5


def test_wide_labeled_synthetic_text_sweep_reports_threshold_quality():
    positives, negatives = _synthetic_pair_set()
    true_positive = sum(_score_as_candidate(left, right) for left, right in positives)
    false_negative = len(positives) - true_positive
    false_positive = sum(_score_as_candidate(left, right) for left, right in negatives)
    true_negative = len(negatives) - false_positive

    # This is a regression baseline, not a claim about real-world accuracy.
    assert (true_positive, false_negative, false_positive, true_negative) == (6, 2, 2, 7)


def test_broad_labeled_adjacent_pair_run_has_expected_categories():
    positives, negatives = _synthetic_pair_set()
    pairs = positives + negatives
    frames = []
    for index, (left, right) in enumerate(pairs):
        frames.extend(
            [
                frame(f"{index:02d}-a", index * 20, left, dhash=index),
                frame(f"{index:02d}-b", index * 20 + 1, right, dhash=index),
                # Gap isolates this labeled pair from the next synthetic pair.
                frame(f"{index:02d}-next", index * 20 + 20, "unrelated", dhash=index),
            ]
        )

    candidates = analyze_adjacent_descriptions(frames)
    categories = Counter(candidate.category for candidate in candidates)
    assert len(candidates) == 48  # Blank descriptions are deliberately omitted.
    assert categories["high-confidence-candidate"] == 8
    assert categories["review"] == 17
    assert categories["reject"] == 23
    assert all(candidate.gap_seconds <= 10 for candidate in candidates if candidate.category != "reject")

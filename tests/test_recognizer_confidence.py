"""
Unit tests for the confidence classification in app.core.recognizer.

Threshold semantics (pinned):
    - confidence is derived from absolute score and margin;
    - the `threshold` argument is an absolute-score gate:
      best_score < threshold  ->  best_id = None / NO_MATCH.

Only the pure helpers and constants are exercised here; the full
recognize_folder path needs the DINO model and is not unit-tested.
"""

import pytest

from app.core.recognizer import SceneRecognizer


@pytest.mark.parametrize(
    "score, margin, expected",
    [
        (0.99, 0.50, "HIGH"),
        (0.90, 0.03, "HIGH"),      # exact HIGH boundaries
        (0.90, 0.02, "PROBABLE"),  # high score, margin below HIGH
        (0.85, 0.02, "PROBABLE"),
        (0.80, 0.015, "PROBABLE"), # exact PROBABLE boundaries
        (0.85, 0.01, "AMBIGUOUS"), # good score, margin below PROBABLE
        (0.80, 0.00, "AMBIGUOUS"),
        (0.70, 0.50, "NO_MATCH"),  # score below PROBABLE
        (0.00, 0.00, "NO_MATCH"),
    ],
)
def test_confidence_levels(score, margin, expected):
    assert SceneRecognizer._confidence(score, margin) == expected


@pytest.mark.parametrize(
    "confidence, expected_status",
    [
        ("HIGH", "CONFIDENT"),
        ("PROBABLE", "PROBABLE_MATCH"),
        ("AMBIGUOUS", "AMBIGUOUS"),
        ("NO_MATCH", "NO_MATCH"),
        ("UNKNOWN", "NO_MATCH"),
    ],
)
def test_status_from_confidence(confidence, expected_status):
    assert (
        SceneRecognizer._status_from_confidence(confidence)
        == expected_status
    )


def test_threshold_constants_are_pinned():
    # Changing these is a deliberate contract change and must
    # be reflected in docs and tests.
    assert SceneRecognizer.HIGH_SCORE == 0.90
    assert SceneRecognizer.PROBABLE_SCORE == 0.80
    assert SceneRecognizer.HIGH_MARGIN == 0.03
    assert SceneRecognizer.PROBABLE_MARGIN == 0.015
    assert SceneRecognizer.VERSION == "3.3"

"""Read-only prototype for comparing descriptions on adjacent crop series.

This module only produces evidence-bearing candidates. It never applies or
persists a description change. Thresholds are exploratory, not production
confidence guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.billboard.phash import distance
from app.refine.logic import skeleton

MAX_GAP_SECONDS = 10.0
MAX_CROP_DHASH_DISTANCE = 6
MIN_HIGH_CONFIDENCE_LENGTH = 5
HIGH_CONFIDENCE_TEXT_SCORE = 0.85


@dataclass(frozen=True)
class DescriptionFrame:
    photo_id: str
    taken_at: datetime | None
    crop_dhash: int | None
    description: str | None
    screen: str | None = None


@dataclass(frozen=True)
class DescriptionCandidate:
    left_photo_id: str
    right_photo_id: str
    left_description: str
    right_description: str
    gap_seconds: float | None
    dhash_distance: int | None
    text_score: float | None
    category: str
    reasons: tuple[str, ...]


def _edit_distance(left: str, right: str) -> int:
    """Levenshtein distance using memory proportional to the shorter string."""

    if len(left) < len(right):
        left, right = right, left

    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current

    return previous[-1]


def text_similarity(left: str, right: str) -> float:
    """Normalized character-edit similarity after existing name normalization."""

    left_key, right_key = skeleton(left), skeleton(right)
    if not left_key or not right_key:
        return 0.0

    return 1.0 - _edit_distance(left_key, right_key) / max(len(left_key), len(right_key))


def analyze_adjacent_descriptions(
    frames: list[DescriptionFrame],
    *,
    max_gap_seconds: float = MAX_GAP_SECONDS,
    max_dhash_distance: int = MAX_CROP_DHASH_DISTANCE,
    high_confidence_text_score: float = HIGH_CONFIDENCE_TEXT_SCORE,
    min_high_confidence_length: int = MIN_HIGH_CONFIDENCE_LENGTH,
) -> list[DescriptionCandidate]:
    """Score consecutive frames only; return no merge actions or DB changes.

    `high-confidence-candidate` is a prototype classification, not permission
    to write. Missing time/hash or a screen change prevents a high classification.
    """

    ordered = sorted(
        (frame for frame in frames if frame.taken_at is not None),
        key=lambda frame: (frame.taken_at, frame.photo_id),
    )
    results: list[DescriptionCandidate] = []

    for left, right in zip(ordered, ordered[1:]):
        left_text, right_text = (left.description or "").strip(), (right.description or "").strip()
        if not left_text or not right_text:
            continue

        gap = abs((right.taken_at - left.taken_at).total_seconds())
        hash_distance = (
            distance(left.crop_dhash, right.crop_dhash)
            if left.crop_dhash is not None and right.crop_dhash is not None
            else None
        )
        score = text_similarity(left_text, right_text)
        reasons: list[str] = []
        eligible = True

        if gap > max_gap_seconds:
            eligible = False
            reasons.append("outside_time_window")
        if left.screen != right.screen:
            eligible = False
            reasons.append("different_screen")
        if hash_distance is None:
            eligible = False
            reasons.append("missing_crop_dhash")
        elif hash_distance > max_dhash_distance:
            eligible = False
            reasons.append("crop_dhash_mismatch")
        if min(len(skeleton(left_text)), len(skeleton(right_text))) < min_high_confidence_length:
            eligible = False
            reasons.append("text_too_short_for_high_confidence")

        if not eligible:
            category = "reject"
        elif score >= high_confidence_text_score:
            category = "high-confidence-candidate"
            reasons.append("time_crop_hash_and_text_agree")
        else:
            category = "review"
            reasons.append("text_similarity_below_prototype_threshold")

        results.append(
            DescriptionCandidate(
                left_photo_id=left.photo_id,
                right_photo_id=right.photo_id,
                left_description=left_text,
                right_description=right_text,
                gap_seconds=gap,
                dhash_distance=hash_distance,
                text_score=round(score, 4),
                category=category,
                reasons=tuple(reasons),
            )
        )

    return results

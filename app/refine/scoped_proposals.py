"""Pure proposals for conservative, date-scoped QWEN enrichment.

This module does not persist values. It produces dry-run proposals only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.billboard.phash import distance
from app.refine.logic import skeleton

MAX_GAP_SECONDS = 10.0
MAX_CROP_DHASH_DISTANCE = 6


@dataclass(frozen=True)
class EnrichmentFrame:
    photo_id: str
    screen: str | None
    taken_at: datetime | None
    crop_dhash: int | None
    description: str | None = None
    tags: tuple[str, ...] = ()
    client: str | None = None
    brand: str | None = None


@dataclass(frozen=True)
class EnrichmentProposal:
    photo_id: str
    changes: dict[str, Any]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class EnrichmentReport:
    proposals: tuple[EnrichmentProposal, ...]
    description_variants: tuple[dict[str, Any], ...]
    ineligible_pairs: tuple[dict[str, Any], ...]


def _tags(values: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicate tags preserving first-seen spelling and order."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        tag = str(value or "").strip()
        key = skeleton(tag)
        if tag and key and key not in seen:
            seen.add(key)
            result.append(tag)
    return tuple(result)


def _descriptions_compatible(frames: list[EnrichmentFrame]) -> bool:
    """Only exact normalized agreement is considered unambiguous."""

    values = {skeleton(frame.description) for frame in frames if skeleton(frame.description)}
    return len(values) <= 1


def _group_is_eligible(
    group: list[EnrichmentFrame], *, max_gap_seconds: float, max_dhash_distance: int
) -> tuple[bool, list[dict[str, Any]]]:

    issues: list[dict[str, Any]] = []
    for left, right in zip(group, group[1:]):
        if not left.screen or not right.screen or left.screen != right.screen:
            issues.append({"left": left.photo_id, "right": right.photo_id, "reason": "different_or_missing_screen"})
            continue
        if left.taken_at is None or right.taken_at is None:
            issues.append({"left": left.photo_id, "right": right.photo_id, "reason": "missing_capture_time"})
            continue
        gap = abs((right.taken_at - left.taken_at).total_seconds())
        if gap > max_gap_seconds:
            issues.append({"left": left.photo_id, "right": right.photo_id, "reason": "outside_time_window", "gap_seconds": gap})
            continue
        if left.crop_dhash is None or right.crop_dhash is None:
            issues.append({"left": left.photo_id, "right": right.photo_id, "reason": "missing_crop_dhash"})
            continue
        hash_distance = distance(left.crop_dhash, right.crop_dhash)
        if hash_distance > max_dhash_distance:
            issues.append({"left": left.photo_id, "right": right.photo_id, "reason": "crop_dhash_mismatch", "dhash_distance": hash_distance})
    # Group callers pass a two-frame list. This explicit check avoids treating
    # frames as eligible when there is no actual adjacent comparison.
    return not issues, issues


def propose_enrichment(
    frames: list[EnrichmentFrame],
    *,
    max_gap_seconds: float = MAX_GAP_SECONDS,
    max_dhash_distance: int = MAX_CROP_DHASH_DISTANCE,
) -> EnrichmentReport:
    """Produce empty-description/tag-union proposals without applying them.

    Frames form a group only while each photo matches every other group member
    on strict visual/time eligibility. Description variants are informational:
    tags are still unioned, while an empty description is filled only when the
    group has one unambiguous normalized non-empty value.
    """

    if not isinstance(max_gap_seconds, (int, float)) or isinstance(max_gap_seconds, bool) or not 0 <= max_gap_seconds <= 10:
        raise ValueError("max_gap_seconds must be between 0 and 10")
    if not 0 <= max_dhash_distance <= MAX_CROP_DHASH_DISTANCE:
        raise ValueError("max_dhash_distance must be between 0 and 6")

    ordered = sorted(
        (frame for frame in frames if frame.taken_at is not None),
        key=lambda frame: (str(frame.screen or ""), frame.taken_at, frame.photo_id),
    )
    groups: list[list[EnrichmentFrame]] = []
    current: list[EnrichmentFrame] = []

    for frame in ordered:
        if not current:
            current = [frame]
            continue
        pair_ok, _issues = _group_is_eligible(
            [current[-1], frame],
            max_gap_seconds=max_gap_seconds,
            max_dhash_distance=max_dhash_distance,
        )
        all_members_ok = all(
            _group_is_eligible(
                [member, frame],
                max_gap_seconds=max_gap_seconds,
                max_dhash_distance=max_dhash_distance,
            )[0]
            for member in current
        )
        if pair_ok and all_members_ok:
            current.append(frame)
        else:
            if len(current) > 1:
                groups.append(current)
            current = [frame]
    if len(current) > 1:
        groups.append(current)

    proposals: dict[str, dict[str, Any]] = {}
    evidence_by_photo: dict[str, tuple[str, ...]] = {}
    description_variants: list[dict[str, Any]] = []
    ineligible_pairs: list[dict[str, Any]] = []

    for left, right in zip(ordered, ordered[1:]):
        eligible, issues = _group_is_eligible(
            [left, right],
            max_gap_seconds=max_gap_seconds,
            max_dhash_distance=max_dhash_distance,
        )
        if not eligible:
            ineligible_pairs.extend(issues)

    for group in groups:
        descriptions_by_key: dict[str, str] = {}
        for frame in group:
            description = (frame.description or "").strip()
            key = skeleton(description)
            if key:
                descriptions_by_key.setdefault(key, description)

        descriptions = list(descriptions_by_key.values())
        canonical_description = descriptions[0] if len(descriptions) == 1 else None
        if len(descriptions) > 1:
            description_variants.append({
                "photo_ids": [frame.photo_id for frame in group],
                "descriptions": descriptions,
                "reason": "multiple_description_variants_in_visual_group",
            })

        merged_tags = _tags(tuple(tag for frame in group for tag in frame.tags))
        evidence = (
            f"same_screen={group[0].screen}",
            f"max_gap_seconds<={max_gap_seconds:g}",
            f"max_crop_dhash_distance<={max_dhash_distance}",
        )

        for frame in group:
            changes: dict[str, Any] = {}
            evidence_by_photo[frame.photo_id] = evidence
            if not (frame.description or "").strip() and canonical_description:
                changes["description"] = canonical_description
            if merged_tags != _tags(frame.tags):
                changes["tags"] = list(merged_tags)
            if changes:
                proposals[frame.photo_id] = changes

    return EnrichmentReport(
        proposals=tuple(
            EnrichmentProposal(photo_id, changes, evidence_by_photo[photo_id])
            for photo_id, changes in sorted(proposals.items())
        ),
        description_variants=tuple(description_variants),
        ineligible_pairs=tuple(ineligible_pairs),
    )

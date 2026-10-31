"""Crop-level QWEN observation aggregation for one photo.

The alias map is a read-only snapshot of the existing audited client_aliases
source. Photo-level QWEN remains one row; crop observations remain attached to
photo_regions for occurrence counts and future replay.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any


def _compact(value: str) -> str:
    """Case/punctuation-insensitive key so «Big Fest» = «bigfest»."""

    return re.sub(r"[\s\-_«»\"'.,]+", "", value.casefold())


def _canonical(value: object, kind: str, aliases: dict[tuple[str, str], str]) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return aliases.get((kind, text.casefold()), text)


def aggregate_crop_fields(
    observations: list[dict[str, Any]],
    *,
    alias_rows: list[dict[str, str]] | None = None,
    frequencies: dict[str, Any] | None = None,
    primary_index: int = 0,
    global_frequency: bool = True,
) -> dict[str, Any]:
    """Build the backward-compatible photo-level fields from successful crops.

    Values are counted once per crop observation. Client and brand modes are
    independent. Ties resolve to the primary/largest crop if it has a tied
    value, otherwise stable lexical order. Secondary advertiser values remain
    present in tags/descriptions.
    """

    aliases = {
        (row.get("kind", "client"), row.get("alias", "").casefold()): row.get("canonical", "").strip()
        for row in (alias_rows or [])
        if row.get("alias") and row.get("canonical")
    }
    crops = sorted(
        (row for row in observations if row.get("status", "DONE") == "DONE"),
        key=lambda row: (int(row.get("crop_index", 0)), int(row.get("region_id", 0))),
    )
    if not crops:
        return {"client": None, "brand": None, "description": None, "category": None, "tags": []}

    primary = crops[0]
    result: dict[str, Any] = {}
    for field, kind in (("client", "client"), ("brand", "brand")):
        counts: Counter[str] = Counter()
        crop_values: list[str | None] = []
        for crop in crops:
            fields = crop.get("fields") or crop.get("qwen_fields") or {}
            normalized = _canonical(fields.get(field), kind, aliases)
            crop_values.append(normalized)
            if normalized:
                counts[normalized] += 1
            # Полный кадр иногда кладёт того же рекламодателя в client,
            # а не в brand. При частотном выборе это тоже голос за бренд,
            # иначе Бигфест терялся бы из-за поля, в которое его записала модель.
            if (
                field == "brand"
                and global_frequency
                and frequencies
                and frequencies.get("brand")
            ):
                other = _canonical(fields.get("client"), "client", aliases)
                if other:
                    counts.setdefault(other, 0)
        if global_frequency and counts and frequencies and frequencies.get(kind):
            # Crop observations in this photo vote only among their candidates,
            # weighted by the occurrence frequency in the whole QWEN base.
            # Variants without a dictionary alias («Big Fest» / «bigfest»)
            # still share one vote through the compact key.
            index: dict[str, int] = {}
            for name, vote in frequencies[kind].items():
                key = _compact(str(name))
                index[key] = index.get(key, 0) + int(vote)
            for value in list(counts):
                counts[value] = index.get(_compact(value), 0)
        if counts:
            highest = max(counts.values())
            winners = {value for value, count in counts.items() if count == highest}
            primary_crop = next(
                (crop for crop in crops if int(crop.get("crop_index", 0)) == primary_index),
                primary,
            )
            primary_fields = primary_crop.get("fields") or primary_crop.get("qwen_fields") or {}
            primary_value = _canonical(primary_fields.get(field), kind, aliases)
            selected = primary_value if primary_value in winners else min(winners, key=str.casefold)
        else:
            selected = None

        # Показывать предпочтительное написание из частотного справочника,
        # а не случайный регистр из конкретного чтения («БИГФЕСТ»).
        display = (frequencies or {}).get("display") or {}
        if selected and isinstance(display, dict):
            selected = display.get(_compact(selected), selected)
        result[field] = selected

    descriptions: list[str] = []
    tags: list[str] = []
    seen_tags: set[str] = set()
    categories: list[str] = []
    for crop in crops:
        fields = crop.get("fields") or crop.get("qwen_fields") or {}
        description = str(fields.get("description") or "").strip()
        if description and description not in descriptions:
            descriptions.append(description)
        category = str(fields.get("category") or "").strip()
        if category and category not in categories:
            categories.append(category)
        crop_tags = list(fields.get("tags") or [])
        for value in crop_tags:
            text = str(value or "").strip()
            key = text.casefold()
            if text and key not in seen_tags:
                seen_tags.add(key)
                tags.append(text)

    # Проигравший рекламодатель не должен исчезнуть из карточки: выигравшие
    # client/brand уже стоят в своих полях, остальные остаются в тегах.
    for field, kind in (("client", "client"), ("brand", "brand")):
        selected = (result.get(field) or "").casefold()
        for crop in crops:
            fields = crop.get("fields") or crop.get("qwen_fields") or {}
            text = _canonical(fields.get(field), kind, aliases)
            if not text or text.casefold() == selected:
                continue
            key = text.casefold()
            if key not in seen_tags:
                seen_tags.add(key)
                tags.append(text)

    result["description"] = " | ".join(descriptions)[:800] if descriptions else None
    result["category"] = categories[0] if categories else None
    result["tags"] = tags[:40]
    result["crop_observations"] = len(crops)
    result["client_crop_counts"] = dict(counts_for_field(crops, "client", "client", aliases))
    result["brand_crop_counts"] = dict(counts_for_field(crops, "brand", "brand", aliases))
    return result


def counts_for_field(crops, field, kind, aliases):
    counts: Counter[str] = Counter()
    for crop in crops:
        fields = crop.get("fields") or crop.get("qwen_fields") or {}
        value = _canonical(fields.get(field), kind, aliases)
        if value:
            counts[value] += 1
    return counts

"""Validated, versioned JSON rules for optional refinement reruns."""

from __future__ import annotations

import json
from typing import Any

from app import settings_store

RULES_KEY = "refine_rules_v1"
MAX_RULES_BYTES = 16_384
DEFAULT_RULES: dict[str, Any] = {
    "schema_version": 1,
    "max_gap_seconds": 10,
    "max_crop_dhash_distance": 6,
    "description_mode": "fill_empty",
    "tags_mode": "union_unique",
    "conflict_mode": "block_group",
    "use_client_aliases": True,
    "crop_frequency_date_from": "2026-09-01",
    "crop_frequency_date_to": "2026-10-29",
    "crop_primary_tie_break": "largest_crop",
    "advertiser_dictionary": "client_aliases",
    "advertiser_alias_import_enabled": False,
    # Предпочтение частого рекламодателя при двух щитах в кадре.
    "crop_frequency_enabled": True,
    # При нескольких кропах дополнительно читать полный кадр: детектор может
    # пропустить щит (например, Бигфест рядом с Sunlight и автобусом).
    "multi_crop_full_frame_enabled": True,
}


def validate_rules(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("rules must be a JSON object")

    expected = set(DEFAULT_RULES)
    unknown = sorted(set(value) - expected)
    if unknown:
        raise ValueError("invalid rules fields (unknown keys: " + ", ".join(unknown) + ")")

    # Older saved versions predate the newer optional fields. Fill those from
    # defaults instead of resetting the user's whole rules version, and never
    # accept unknown keys (they could silently change behaviour).
    value = {**DEFAULT_RULES, **value}
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    gap = value["max_gap_seconds"]
    if type(gap) not in {int, float} or not 0 <= gap <= 10:
        raise ValueError("max_gap_seconds must be between 0 and 10")
    distance = value["max_crop_dhash_distance"]
    if type(distance) is not int or not 0 <= distance <= 6:
        raise ValueError("max_crop_dhash_distance must be an integer between 0 and 6")
    if value["description_mode"] != "fill_empty":
        raise ValueError("description_mode must be fill_empty")
    if value["tags_mode"] != "union_unique":
        raise ValueError("tags_mode must be union_unique")
    if value["conflict_mode"] != "block_group":
        raise ValueError("conflict_mode must be block_group")
    if type(value["use_client_aliases"]) is not bool:
        raise ValueError("use_client_aliases must be boolean")
    if value["crop_primary_tie_break"] != "largest_crop":
        raise ValueError("crop_primary_tie_break must be largest_crop")
    if value["advertiser_dictionary"] != "client_aliases":
        raise ValueError("advertiser_dictionary must be client_aliases")
    if type(value["advertiser_alias_import_enabled"]) is not bool:
        raise ValueError("advertiser_alias_import_enabled must be boolean")
    if type(value["crop_frequency_enabled"]) is not bool:
        raise ValueError("crop_frequency_enabled must be boolean")
    if type(value["multi_crop_full_frame_enabled"]) is not bool:
        raise ValueError("multi_crop_full_frame_enabled must be boolean")
    for key in ("crop_frequency_date_from", "crop_frequency_date_to"):
        item = value[key]
        if not isinstance(item, str) or len(item) != 10:
            raise ValueError(f"{key} must be an ISO date")
        try:
            from datetime import date
            date.fromisoformat(item)
        except ValueError as exc:
            raise ValueError(f"{key} must be an ISO date") from exc
    if value["crop_frequency_date_to"] < value["crop_frequency_date_from"]:
        raise ValueError("crop frequency end date must not precede start date")

    # Round-trip through JSON also rejects custom objects should this function be
    # reused outside HTTP parsing; no code is executable in the rules format.
    return json.loads(json.dumps(value))


def parse_rules_json(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_RULES_BYTES:
        raise ValueError("rules JSON exceeds maximum size")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    return validate_rules(value)


def get_rules() -> dict[str, Any]:
    stored = settings_store.get(RULES_KEY)
    if not isinstance(stored, dict):
        return {"version": 0, "rules": dict(DEFAULT_RULES)}
    try:
        rules = validate_rules(stored.get("rules"))
        version = int(stored.get("version", 0))
    except (TypeError, ValueError):
        return {"version": 0, "rules": dict(DEFAULT_RULES)}
    history = stored.get("history", [])
    if not isinstance(history, list):
        history = []
    return {"version": version, "rules": rules, "history": history[-20:]}


def save_rules(value: object) -> dict[str, Any]:
    rules = parse_rules_json(value) if isinstance(value, str) else validate_rules(value)
    current = get_rules()
    version = current["version"] + 1
    result = {"version": version, "rules": rules}
    history = current.get("history", [])
    history.append({"version": version, "rules": rules})
    result["history"] = history[-20:]
    settings_store.set_value(RULES_KEY, result)

    # Частотный снапшот кэшируется; новые правила могут изменить источник.
    from app.refine import crop_frequency

    crop_frequency.clear_cache()
    return result

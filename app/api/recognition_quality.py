"""Read and validate the curated recognition-quality snapshot."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from fastapi import HTTPException

DEFAULT_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data/reports/recognition_quality/snapshot.json"
)
SNAPSHOT_PATH = Path(
    os.getenv("SCENE_RECOGNITION_QUALITY_SNAPSHOT", str(DEFAULT_SNAPSHOT_PATH))
)
SUPPORTED_SCHEMA_VERSION = 1


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate(snapshot: object) -> dict:
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    if snapshot.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("unsupported snapshot schema")

    source = snapshot.get("source")
    totals = snapshot.get("totals")
    variants = snapshot.get("variants")
    addresses = snapshot.get("addresses")
    address_metrics_source = snapshot.get("address_metrics_source")

    if not isinstance(source, dict) or not isinstance(totals, dict):
        raise ValueError("snapshot source and totals are required")
    if not isinstance(variants, list) or not isinstance(addresses, list):
        raise ValueError("snapshot variants and addresses must be arrays")
    if not isinstance(address_metrics_source, dict):
        raise ValueError("address_metrics_source is required")
    address_counts = [
        address_metrics_source.get(key)
        for key in ("items", "labelled", "correct", "wrong", "unknown")
    ]
    if not all(_is_non_negative_int(value) for value in address_counts):
        raise ValueError("address_metrics_source counts are invalid")
    address_items, address_labelled, address_correct, address_wrong, address_unknown = address_counts
    if address_labelled > address_items or address_correct + address_wrong + address_unknown != address_labelled:
        raise ValueError("address_metrics_source counts do not add up")
    if not isinstance(address_metrics_source.get("notes"), str):
        raise ValueError("address_metrics_source notes are required")
    split_keys = (
        "selected_addresses", "error_addresses", "naming_variant_addresses",
        "selected_items", "error_items", "naming_variant_items",
    )
    label_keys = ("label_error_addresses", "label_error_items")
    if any(key in address_metrics_source for key in split_keys):
        if not all(_is_non_negative_int(address_metrics_source.get(key)) for key in split_keys):
            raise ValueError("address_metrics_source split counts are invalid")
        label_addresses = address_metrics_source.get("label_error_addresses", 0)
        label_items = address_metrics_source.get("label_error_items", 0)
        if not _is_non_negative_int(label_addresses) or not _is_non_negative_int(label_items):
            raise ValueError("address_metrics_source label counts are invalid")
        if (
            address_metrics_source["error_addresses"]
            + address_metrics_source["naming_variant_addresses"]
            + label_addresses
            != address_metrics_source["selected_addresses"]
        ):
            raise ValueError("address_metrics_source address split does not add up")
        if (
            address_metrics_source["error_items"]
            + address_metrics_source["naming_variant_items"]
            + label_items
            != address_metrics_source["selected_items"]
        ):
            raise ValueError("address_metrics_source item split does not add up")
    if not all(_is_non_negative_int(totals.get(key)) for key in ("items", "labelled", "unlabelled")):
        raise ValueError("snapshot totals are invalid")
    if totals["labelled"] + totals["unlabelled"] != totals["items"]:
        raise ValueError("snapshot totals do not add up")
    if source.get("labelled_items") != totals["labelled"]:
        raise ValueError("source labelled_items must match totals")
    if source.get("unlabelled_items") != totals["unlabelled"]:
        raise ValueError("source unlabelled_items must match totals")
    if source.get("sample_items") != totals["items"]:
        raise ValueError("source sample_items must match totals")
    if source.get("address_aggregate_items") != address_metrics_source.get("items"):
        raise ValueError("address aggregate item count must match its source")
    if source.get("address_aggregate_scored_items") != (
        address_metrics_source["correct"] + address_metrics_source["wrong"]
    ):
        raise ValueError("address aggregate scored count must match its source")
    if source.get("address_aggregate_no_result") != address_metrics_source["unknown"]:
        raise ValueError("address aggregate unknown count must match its source")
    if not isinstance(source.get("is_temporal_holdout"), bool):
        raise ValueError("is_temporal_holdout must be explicit")
    if not isinstance(source.get("independent_manual_labels"), bool):
        raise ValueError("independent_manual_labels must be explicit")
    if not isinstance(source.get("label_method"), str) or not source["label_method"].strip():
        raise ValueError("label_method is required")
    if not isinstance(source.get("notes"), list) or not all(
        isinstance(note, str) for note in source["notes"]
    ):
        raise ValueError("source notes must be strings")

    variant_ids: set[str] = set()
    for variant in variants:
        if not isinstance(variant, dict):
            raise ValueError("variant must be an object")
        variant_id = variant.get("id")
        if not isinstance(variant_id, str) or not variant_id or variant_id in variant_ids:
            raise ValueError("variant ids must be unique non-empty strings")
        variant_ids.add(variant_id)
        counts = [variant.get(key) for key in ("labelled", "correct", "wrong", "review")]
        if not all(_is_non_negative_int(value) for value in counts):
            raise ValueError("variant counts are invalid")
        labelled, correct, wrong, review = counts
        if correct + wrong + review != labelled:
            raise ValueError("variant counts do not add up")
        accuracy = variant.get("accuracy")
        if not isinstance(accuracy, (int, float)) or not math.isfinite(accuracy) or not 0 <= accuracy <= 1:
            raise ValueError("variant accuracy is invalid")
        if labelled == 0 or not math.isclose(accuracy, correct / labelled, abs_tol=1e-8):
            raise ValueError("variant accuracy does not match its denominator")
        delta = variant.get("delta_vs_production")
        if delta is not None and (not isinstance(delta, int) or isinstance(delta, bool)):
            raise ValueError("variant delta_vs_production is invalid")
        if not isinstance(variant.get("wrong_pairs"), list):
            raise ValueError("variant wrong_pairs must be an array")
        for pair in variant["wrong_pairs"]:
            _validate_pair(pair)

    address_ids: set[int] = set()
    for address in addresses:
        if not isinstance(address, dict):
            raise ValueError("address must be an object")
        address_id = address.get("address_id")
        if not _is_non_negative_int(address_id) or address_id in address_ids:
            raise ValueError("address ids must be unique non-negative integers")
        address_ids.add(address_id)
        counts = [address.get(key) for key in ("items", "fingerprint_items", "correct", "wrong", "unknown")]
        if not all(_is_non_negative_int(value) for value in counts):
            raise ValueError("address counts are invalid")
        items, _fingerprint_items, correct, wrong, unknown = counts
        if correct + wrong + unknown != items:
            raise ValueError("address counts do not add up")
        rate = address.get("error_rate")
        if not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0 <= rate <= 1:
            raise ValueError("address error_rate is invalid")
        if items == 0 or not math.isclose(rate, wrong / items, abs_tol=1e-8):
            raise ValueError("address error_rate does not match its denominator")
        if not isinstance(address.get("top_confusions"), list):
            raise ValueError("address top_confusions must be an array")
        for pair in address["top_confusions"]:
            _validate_address_confusion(pair)
        is_variant = address.get("is_naming_variant", False)
        if not isinstance(is_variant, bool):
            raise ValueError("address is_naming_variant must be boolean")
        classification = address.get("classification")
        if classification is not None:
            if classification not in {"recognition_error", "naming_variant", "label_error"}:
                raise ValueError("address classification is invalid")
            if (classification == "naming_variant") != bool(is_variant):
                raise ValueError("address naming variant flags disagree")
        if is_variant:
            if not _is_non_negative_int(address.get("canonical_address_id")):
                raise ValueError("naming variant canonical_address_id is invalid")
            canonical_name = address.get("canonical_name")
            if not isinstance(canonical_name, str) or not canonical_name.strip():
                raise ValueError("naming variant canonical_name is required")

    return snapshot


def _validate_address_confusion(pair: object) -> None:
    if not isinstance(pair, dict):
        raise ValueError("address confusion must be an object")
    if not _is_non_negative_int(pair.get("address_id")):
        raise ValueError("address confusion address_id is invalid")
    if not isinstance(pair.get("name"), str) or not pair["name"].strip():
        raise ValueError("address confusion name is required")
    if not _is_non_negative_int(pair.get("count")) or pair["count"] == 0:
        raise ValueError("address confusion count must be positive")


def _validate_pair(pair: object) -> None:
    if not isinstance(pair, dict):
        raise ValueError("confusion pair must be an object")
    if not _is_non_negative_int(pair.get("expected_id")):
        raise ValueError("confusion expected_id is invalid")
    if not _is_non_negative_int(pair.get("predicted_id")):
        raise ValueError("confusion predicted_id is invalid")
    if pair["expected_id"] == pair["predicted_id"]:
        raise ValueError("confusion pair must have distinct addresses")
    if not _is_non_negative_int(pair.get("count")) or pair["count"] == 0:
        raise ValueError("confusion count must be positive")
    if not isinstance(pair.get("expected"), str) or not isinstance(pair.get("predicted"), str):
        raise ValueError("confusion address names are required")


def load_snapshot() -> dict:
    """Load one fixed, operator-published snapshot. No database access."""
    try:
        with SNAPSHOT_PATH.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return _validate(payload)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="снимок качества распознавания пока не опубликован",
        ) from exc
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="снимок качества распознавания недоступен или повреждён",
        ) from exc

"""
Runtime settings for the background billboard branch.

Environment variables are the defaults; values written to app_settings
override them at runtime (same convention as QWEN). The branch is additive:
it never changes INGEST/DINO/HYBRID data.
"""

from __future__ import annotations

import os
from pathlib import Path

from app import settings_store

DETECT_ENABLED_KEY = "billboard_detect"
SCORE_KEY = "billboard_score"
PADDING_KEY = "billboard_padding"
MAX_SIDE_KEY = "billboard_max_side"
MODEL_KEY = "billboard_model"
CLASSES_KEY = "billboard_classes"
SECOND_RATIO_KEY = "billboard_second_ratio"
MAX_REGIONS_KEY = "billboard_max_regions"

DEFAULT_CLASSES = (
    "billboard",
    "digital billboard screen",
    "advertising screen",
)

DEFAULT_SCORE = float(os.getenv("SCENE_BILLBOARD_SCORE", "0.4"))
DEFAULT_PADDING = float(os.getenv("SCENE_BILLBOARD_PADDING", "0.02"))
DEFAULT_MAX_SIDE = int(os.getenv("SCENE_BILLBOARD_MAX_SIDE", "1920"))
DEFAULT_MODEL = os.getenv(
    "SCENE_BILLBOARD_MODEL", "data/models/yolov8s-worldv2.pt"
)
# A second billboard is analysed only when it is comparable in size to the
# largest one; tiny background signs are ignored. Two is the typical number
# on one frame (two panels side by side).
DEFAULT_SECOND_RATIO = float(
    os.getenv("SCENE_BILLBOARD_SECOND_RATIO", "0.35")
)
DEFAULT_MAX_REGIONS = int(os.getenv("SCENE_BILLBOARD_MAX_REGIONS", "2"))

# Crops are derived artifacts; they live outside tracked directories.
CROPS_ROOT = Path(os.getenv("SCENE_CROPS_ROOT", "data/crops"))

DETECTOR_NAME = "yolo-world-v2"


def _stored(key: str):
    try:
        return settings_store.get(key)
    except Exception:  # noqa: BLE001 - without a DB fall back to env defaults
        return None


def set_enabled(enabled: bool) -> bool:
    """Persist the billboard detection/crop switch used by QWEN."""
    settings_store.set_value(DETECT_ENABLED_KEY, bool(enabled))
    return bool(enabled)


def resolve_settings() -> dict:
    """Current detector configuration (settings override environment)."""

    enabled = _stored(DETECT_ENABLED_KEY)

    if enabled is None:
        enabled = os.getenv("SCENE_BILLBOARD_DETECT", "1").strip().lower() in {
            "1",
            "true",
            "yes",
        }

    try:
        score = float(_stored(SCORE_KEY) or DEFAULT_SCORE)
    except (TypeError, ValueError):
        score = DEFAULT_SCORE

    padding_raw = _stored(PADDING_KEY)

    try:
        padding = float(
            padding_raw if padding_raw is not None else DEFAULT_PADDING
        )
    except (TypeError, ValueError):
        padding = DEFAULT_PADDING

    try:
        max_side = int(_stored(MAX_SIDE_KEY) or DEFAULT_MAX_SIDE)
    except (TypeError, ValueError):
        max_side = DEFAULT_MAX_SIDE

    classes = _stored(CLASSES_KEY) or DEFAULT_CLASSES

    if isinstance(classes, str):
        classes = [part.strip() for part in classes.split(",") if part.strip()]

    second_raw = _stored(SECOND_RATIO_KEY)

    try:
        second_ratio = float(
            second_raw if second_raw is not None else DEFAULT_SECOND_RATIO
        )
    except (TypeError, ValueError):
        second_ratio = DEFAULT_SECOND_RATIO

    max_regions_raw = _stored(MAX_REGIONS_KEY)

    try:
        max_regions = int(
            max_regions_raw
            if max_regions_raw is not None
            else DEFAULT_MAX_REGIONS
        )
    except (TypeError, ValueError):
        max_regions = DEFAULT_MAX_REGIONS

    return {
        "enabled": bool(enabled),
        "score": min(max(score, 0.0), 1.0),
        "padding": min(max(padding, 0.0), 0.2),
        "max_side": max(320, max_side),
        "classes": tuple(str(item) for item in classes) or DEFAULT_CLASSES,
        "model": str(_stored(MODEL_KEY) or DEFAULT_MODEL),
        "detector": DETECTOR_NAME,
        "second_ratio": min(max(second_ratio, 0.0), 1.0),
        "max_regions": min(max(max_regions, 1), 4),
    }

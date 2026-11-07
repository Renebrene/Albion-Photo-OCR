"""Whole-scene context descriptors for the optional v3.5 fingerprint profile.

These features are deliberately independent of the DINO global embedding:
they describe the scene around the billboards (top greenery, sky, gray
building/road) and are used only as an optional pair-level veto, starting with
Zorge/Stachki. They are not crop fingerprints.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

CONTEXT_NAMES = ("green_top", "sky_top", "gray_building")
CONTEXT_DESCRIPTOR = "whole_scene_v1"


def context_features(path: str | Path) -> np.ndarray:
    """Return [green_top, sky_top, gray_building] in the 0..1 range."""

    image = Image.open(path).convert("RGB")
    image.thumbnail((640, 640))
    a = np.asarray(image).astype(np.float32) / 255.0
    h, _, _ = a.shape

    top = a[: max(1, int(h * 0.30))]
    mid = a[int(h * 0.30): int(h * 0.75)]

    def masks(part):
        r, g, b = part[:, :, 0], part[:, :, 1], part[:, :, 2]
        bright = part.mean(axis=2)
        mx, mn = part.max(axis=2), part.min(axis=2)
        sat = (mx - mn) / (mx + 1e-6)
        green = (g > r * 1.05) & (g > b * 0.98) & (g > 0.18)
        sky = ((b > r * 1.03) & (b > g * 0.98) & (bright > 0.35)) | (
            (bright > 0.78) & (sat < 0.12)
        )
        gray = (sat < 0.12) & (bright > 0.25) & (bright < 0.80)
        return green, sky, gray

    green_top, sky_top, _ = masks(top)
    _, _, gray_mid = masks(mid)

    return np.asarray(
        [green_top.mean(), sky_top.mean(), gray_mid.mean()],
        dtype=np.float32,
    )


def context_summary(paths: list[Path]) -> dict:
    """Mean/std of the context vector for a fingerprint's source images."""

    values = np.stack([context_features(path) for path in paths])
    return {
        "context_descriptor": CONTEXT_DESCRIPTOR,
        "context_names": list(CONTEXT_NAMES),
        "context_mean": values.mean(axis=0).tolist(),
        "context_std": values.std(axis=0).tolist(),
    }

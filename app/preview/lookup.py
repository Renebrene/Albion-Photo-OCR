"""Where a derivative already exists: the MIDDLE preview as a DINO input.

DINO resizes every image to 518 px (global embedding) and 128 px (compact
descriptors), so reading a 4–8 MB original is wasted work: decoding dominates
the CPU pass. The MIDDLE preview is already ≤1280 px, and a measurement on
100 photos showed the same best fingerprint in 99 cases, with the only
difference a near-tie below the review margin (docs/dino_preview_experiment.md).

This module is deliberately light: the API process must not import torch or
OpenCV just to locate a file.
"""

from __future__ import annotations

from pathlib import Path

from app.api.config import PREVIEW_ROOT


def middle_preview_path(
    photo_id: str,
    *,
    preview_root: str | Path | None = None,
) -> Path | None:
    """Existing MIDDLE preview (current format, then legacy JPEG), or None."""

    if not photo_id:
        return None

    from app.preview import formats
    from app.preview.generator import build_preview_paths

    try:
        paths = build_preview_paths(
            preview_root=preview_root or PREVIEW_ROOT,
            photo_id=str(photo_id),
        )
    except (TypeError, ValueError):
        return None

    for candidate in formats.candidate_paths(paths.middle):
        if candidate.is_file():
            return candidate

    return None


def dino_input_path(
    photo_id: str,
    source_path: str | Path,
    *,
    use_preview: bool = True,
    preview_root: str | Path | None = None,
) -> Path:
    """
    File DINO should read: the MIDDLE preview when it exists, else the original.

    The original remains the fallback for photos whose preview has not been
    generated yet (or was removed), so a DINO batch never waits for previews.
    """

    if use_preview:
        preview = middle_preview_path(photo_id, preview_root=preview_root)

        if preview is not None:
            return preview

    return Path(source_path)

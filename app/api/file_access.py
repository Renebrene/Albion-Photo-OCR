"""Shared fail-closed access checks for registered original media paths."""

from __future__ import annotations

from pathlib import Path


def allowed_media_path(source_path: str, roots: list[Path]) -> Path | None:
    """Resolve a registered source only when it remains within an allowed root."""

    try:
        resolved = Path(source_path).resolve(strict=True)
    except (OSError, RuntimeError):
        return None

    for root in roots:
        try:
            root_resolved = root.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if (resolved == root_resolved or root_resolved in resolved.parents) and resolved.is_file():
            return resolved
    return None

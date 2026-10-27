"""Shared fail-closed access checks for registered original media paths."""

from __future__ import annotations

from pathlib import Path

# Why an original cannot be served, in a form the UI can show without
# exposing the path itself (see original_availability).
ORIGINAL_OK = "ok"
ORIGINAL_NOT_CONFIGURED = "not_configured"
ORIGINAL_OUTSIDE_ROOTS = "outside_roots"
ORIGINAL_MISSING = "missing"
# The path sits inside a configured root, but the root itself is not a
# directory any more: the volume was unmounted, moved or never mounted here.
# Kept apart from ORIGINAL_MISSING on purpose — the fix is different
# (mount the volume, or remap the stored paths with
# scripts/remap_source_root.py), and "файл не найден" on a whole volume
# sends people looking for a missing file instead of a missing disk.
ORIGINAL_ROOT_UNAVAILABLE = "root_unavailable"


def original_availability(source_path: str | None, roots: list[Path]) -> str:
    """
    Classify a registered source path without leaking it.

    Unlike `allowed_media_path`, the missing file and the disallowed root are
    told apart, because they mean different things to a user: "оригинал
    недоступен, используйте превью" versus a configuration problem. A path
    below a configured root whose directory does not exist is reported
    separately (ORIGINAL_ROOT_UNAVAILABLE) instead of "файл не найден". No
    content is read — only resolve(), is_dir() and is_file().
    """

    if not source_path:
        return ORIGINAL_MISSING
    if not roots:
        return ORIGINAL_NOT_CONFIGURED

    try:
        resolved = Path(source_path).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return ORIGINAL_MISSING

    inside = False
    root_available = False
    for root in roots:
        try:
            root_resolved = root.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue
        # The loop cannot stop at the first match: a live root later in the
        # list must win over a dead one earlier in it, so the path is only
        # called rootless after every root has been considered.
        if resolved != root_resolved and root_resolved not in resolved.parents:
            continue
        inside = True
        try:
            if root_resolved.is_dir():
                root_available = True
                break
        except OSError:
            continue

    if not inside:
        return ORIGINAL_OUTSIDE_ROOTS
    if not root_available:
        return ORIGINAL_ROOT_UNAVAILABLE
    try:
        return ORIGINAL_OK if resolved.is_file() else ORIGINAL_MISSING
    except OSError:
        return ORIGINAL_MISSING


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

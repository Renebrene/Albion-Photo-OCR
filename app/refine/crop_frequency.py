"""Cached advertiser frequency priors for multi-crop QWEN aggregation.

The prior is the whole QWEN base (one photo card = one vote), not only the
current crop observations: at the start of the multi-crop rollout there are
too few saved crop fields to rank advertisers reliably.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from app.qwen.database import base_value_frequencies, stored_value_frequencies
from app.refine.rules import get_rules

_lock = Lock()
_cache: dict[bool, dict[str, dict[str, int]]] = {}


def snapshot(*, use_aliases: bool | None = None) -> dict[str, dict[str, int]]:
    """Case-folded ``{kind: {value: count}}`` for the whole QWEN base."""

    if use_aliases is None:
        use_aliases = bool(get_rules()["rules"]["use_client_aliases"])

    key = bool(use_aliases)
    with _lock:
        if key not in _cache:
            # Prefer the precomputed table (schema/058); fall back to a live
            # count on legacy databases or when aliases are explicitly off.
            data = stored_value_frequencies() if key else None
            _cache[key] = data or base_value_frequencies(use_aliases=key)
        return _cache[key]


def aggregation_context() -> dict[str, Any] | None:
    """
    Parameters for ``aggregate_crop_fields`` when the rule is enabled.

    ``None`` keeps the old tie-break (primary/largest crop). The context is
    cheap after the first call: the base snapshot is cached until rules change.
    """

    rules = get_rules()["rules"]

    if not rules.get("crop_frequency_enabled"):
        return None

    return {
        "use_client_aliases": bool(rules["use_client_aliases"]),
        "global_frequency": True,
        "frequencies": snapshot(use_aliases=bool(rules["use_client_aliases"])),
    }


def clear_cache() -> None:
    with _lock:
        _cache.clear()

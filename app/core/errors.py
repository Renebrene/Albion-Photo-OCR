"""
Helpers for producing user-facing error text without leaking local paths.

Absolute paths are useful in server logs but should not be returned to
callers or stored in result objects. The file name is kept for context.
"""

from __future__ import annotations

from pathlib import Path


def redact_paths(message, *paths) -> str:
    """
    Replace occurrences of the given paths in *message* with their basename.

    Empty candidates are ignored. If a path is not present, the message is
    returned unchanged.
    """

    text = str(message)

    for candidate in paths:
        if not candidate:
            continue

        value = str(candidate)

        if value and value in text:
            text = text.replace(value, Path(value).name)

    return text

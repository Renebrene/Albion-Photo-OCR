"""
Helpers for producing user-facing error text without leaking local paths.

Absolute paths are useful in server logs but should not be returned to
callers or stored in result objects. The file name is kept for context.
"""

from __future__ import annotations

import re
from pathlib import Path

# Absolute POSIX paths that start a token (start of string or after whitespace).
_ABS_PATH_RE = re.compile(r"(?:(?<=\s)|^)(/[^\s]+)")


def redact_absolute_paths(message) -> str:
    """
    Replace absolute paths found anywhere in *message* with their basename.

    Used when an error string may contain an unknown server path (for example
    an exception raised by a decoder or a cloud provider). Paths are only
    matched when they begin a token, so URLs like https://host/path are left
    alone.
    """

    text = str(message)

    def _repl(match: re.Match) -> str:
        value = match.group(1)
        return Path(value).name or value

    return _ABS_PATH_RE.sub(_repl, text)


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

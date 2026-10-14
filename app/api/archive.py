"""
Downloading a selection as one ZIP archive.

The archive is assembled on the server, in a spooled temporary file: small
selections stay in memory, large ones spill to disk, so a big download cannot
exhaust RAM. Files are stored, not re-compressed - originals are JPEG/PNG
already, and deflating them would only spend CPU for a percent or two.

Names come from the caller (the window already builds them exactly as for a
single-file download: original name, or "<address>__<name>"). They are still
sanitised here: an archive entry must never contain a path, "..", or a name
that collides with another entry.
"""

from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import Path

# Guard rails: a selection bigger than this is refused instead of building a
# multi-gigabyte archive (and a multi-minute request) by accident.
MAX_ITEMS = 500
MAX_TOTAL_BYTES = int(2.5 * 1024**3)
SPOOL_MAX_BYTES = 64 * 1024 * 1024

_UNSAFE = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")
MAX_NAME_LENGTH = 180


class ArchiveError(ValueError):
    """The selection cannot be archived (too big, empty, unreadable)."""


def safe_archive_name(name: str | None, fallback: str) -> str:
    """
    A file name that is safe inside a zip entry.

    Only the base name survives, so a crafted name cannot write outside the
    extraction folder; the result is never empty and not too long.
    """

    base = Path(str(name or "").replace("\\", "/")).name
    base = _UNSAFE.sub("_", base).strip(" .")

    if not base:
        base = fallback or "photo.jpg"

    if len(base) > MAX_NAME_LENGTH:
        stem, dot, suffix = base.rpartition(".")

        keep = MAX_NAME_LENGTH - (len(suffix) + 1 if dot else 0)

        base = f"{stem[:keep]}.{suffix}" if dot else base[:MAX_NAME_LENGTH]

    return base


def unique_name(name: str, used: set[str]) -> str:
    """Append " (2)", " (3)"… so two entries never share a name."""

    if name not in used:
        used.add(name)
        return name

    stem, dot, suffix = name.rpartition(".")
    stem = stem if dot else name
    suffix = f".{suffix}" if dot else ""

    index = 2

    while True:
        candidate = f"{stem} ({index}){suffix}"

        if candidate not in used:
            used.add(candidate)
            return candidate

        index += 1


def build_archive(entries: list[tuple[Path, str]]) -> tuple[object, int]:
    """
    Zip [(path, name)] into a spooled file; returns (file, size).

    The file is rewound and ready to be streamed. Raises ArchiveError when the
    selection is empty, a file is unreadable, or the total size is over the cap.
    """

    if not entries:
        raise ArchiveError("нечего архивировать")

    buffer = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_BYTES)

    used: set[str] = set()
    total = 0

    try:
        with zipfile.ZipFile(
            buffer, "w", compression=zipfile.ZIP_STORED
        ) as archive:
            for path, name in entries:
                try:
                    size = path.stat().st_size
                except OSError as exc:
                    raise ArchiveError(f"файл недоступен: {path.name}") from exc

                total += size

                if total > MAX_TOTAL_BYTES:
                    raise ArchiveError(
                        "выбранные файлы слишком велики для одного архива"
                    )

                archive.write(path, arcname=unique_name(name, used))
    except BaseException:
        buffer.close()
        raise

    buffer.seek(0)

    return buffer, total

"""
Fast INGEST check for the metadata-v1 identity scheme.

The legacy check reads the whole file twice: SHA-256 and a full decode. This
one reads only the header and EXIF, then lets PIL verify the structure. The
full decode is not lost: PREVIEW decodes the file anyway, and a broken image
surfaces there instead of delaying registration.

The file is still opened read-only and never modified.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.errors import redact_paths
from app.ingest.integrity import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_FORMATS,
    read_identity_metadata,
    read_taken_at,
)


def check_file_metadata(path: Path) -> dict:
    """Header + EXIF check; returns the same keys as integrity.check_file."""

    result = {
        "filename": path.name,
        "source_path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "extension_valid": path.suffix.lower() in SUPPORTED_EXTENSIONS,
        "size_bytes": None,
        # Identity comes from metadata; the content SHA is not computed.
        "sha256": None,
        "container_format": None,
        "width": None,
        "height": None,
        "frame_count": None,
        "taken_at": None,
        "exif_serial": None,
        "exif_subsec": None,
        "decoded": False,
        "integrity_status": "INVALID",
        "error": None,
    }

    if not result["exists"] or not result["is_file"]:
        result["error"] = "File does not exist or is not a regular file"
        return result

    if not result["extension_valid"]:
        result["error"] = f"Unsupported extension: {path.suffix}"
        return result

    result["size_bytes"] = path.stat().st_size

    try:
        with Image.open(path) as image:
            result["container_format"] = image.format

            if image.format not in SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format: {image.format}")

            result["width"], result["height"] = image.size
            result["frame_count"] = getattr(image, "n_frames", 1)
            result["taken_at"] = read_taken_at(image)
            result.update(read_identity_metadata(image))

            # Structural check only: it does not decode pixel data, which is
            # what keeps this pass cheap. PREVIEW performs the real decode.
            image.verify()

        result["integrity_status"] = "VALID"

    except Exception as exc:
        result["error"] = redact_paths(str(exc), path)

    return result

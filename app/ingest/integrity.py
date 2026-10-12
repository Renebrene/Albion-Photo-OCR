from pathlib import Path
import hashlib
from PIL import Image

from app.core.errors import redact_paths

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}
SUPPORTED_FORMATS = {"JPEG", "MPO"}


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_file(path: Path) -> dict:
    result = {
        "filename": path.name,
        "source_path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "extension_valid": path.suffix.lower() in SUPPORTED_EXTENSIONS,
        "size_bytes": None,
        "sha256": None,
        "container_format": None,
        "width": None,
        "height": None,
        "frame_count": None,
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
        result["sha256"] = calculate_sha256(path)

        with Image.open(path) as image:
            result["container_format"] = image.format

            if image.format not in SUPPORTED_FORMATS:
                raise ValueError(
                    f"Unsupported format: {image.format}"
                )

            result["width"], result["height"] = image.size
            result["frame_count"] = getattr(image, "n_frames", 1)

            image.verify()

        with Image.open(path) as image:
            image.seek(0)
            image.load()

        result["decoded"] = True
        result["integrity_status"] = "VALID"

    except Exception as exc:
        result["error"] = redact_paths(str(exc), path)

    return result


def discover_files(directory: str | Path) -> list[Path]:
    root = Path(directory)
    return sorted(
        p for p in root.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def check_directory(directory: str | Path) -> list[dict]:
    return [check_file(p) for p in discover_files(directory)]

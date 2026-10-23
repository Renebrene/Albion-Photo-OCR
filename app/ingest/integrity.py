from dataclasses import dataclass
from pathlib import Path
import hashlib
from datetime import date, datetime

from PIL import Image

from app.core.errors import redact_paths

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}
SUPPORTED_FORMATS = {"JPEG", "MPO"}

# EXIF tags carrying the capture date, in order of preference.
EXIF_DATETIME = 0x0132  # DateTime (0th IFD, usually write time)
EXIF_DATETIME_ORIGINAL = 0x9003  # DateTimeOriginal (Exif sub-IFD)
EXIF_DATETIME_DIGITIZED = 0x9004  # DateTimeDigitized (Exif sub-IFD)
EXIF_SUB_IFD = 0x8769  # ExifOffset, pointer to the Exif sub-IFD
EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
# Parts of the metadata identity (app/ingest/identity_v2.py).
EXIF_BODY_SERIAL = 0xA431  # BodySerialNumber
EXIF_SUB_SEC_ORIGINAL = 0x9291  # SubSecTimeOriginal, hundredths of a second


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_exif_datetime(value: object) -> str | None:
    """
    Convert an EXIF capture date into "YYYY-MM-DD HH:MM:SS".

    Returns None for anything unusable (absent, wrong type, malformed or
    obviously out of range such as the "0000:00:00" placeholder).
    """

    if not isinstance(value, str):
        return None

    raw = value.strip()

    try:
        moment = datetime.strptime(raw[:19], EXIF_DATETIME_FORMAT)
    except ValueError:
        return None

    if not 1900 <= moment.year <= 2100:
        return None

    return moment.isoformat(sep=" ")


def read_taken_at(image: Image.Image) -> str | None:
    """
    Capture date of the currently selected frame, or None when unavailable.

    DateTimeOriginal/DateTimeDigitized live in the Exif sub-IFD (ExifOffset),
    which is where camera JPEGs put them; the 0th IFD usually only carries the
    coarser "DateTime" tag, so it is the last resort.

    EXIF is best-effort metadata: an unreadable or absent block is not an
    error and must not fail the integrity check.
    """

    try:
        exif = image.getexif()
    except Exception:
        return None

    if not exif:
        return None

    values: list[object] = []

    try:
        sub_ifd = exif.get_ifd(EXIF_SUB_IFD)
    except Exception:
        sub_ifd = {}

    if sub_ifd:
        values.append(sub_ifd.get(EXIF_DATETIME_ORIGINAL))
        values.append(sub_ifd.get(EXIF_DATETIME_DIGITIZED))

    # Some writers (and Pillow's own test files) put the tags in the 0th IFD.
    values.append(exif.get(EXIF_DATETIME_ORIGINAL))
    values.append(exif.get(EXIF_DATETIME_DIGITIZED))
    values.append(exif.get(EXIF_DATETIME))

    for value in values:
        taken_at = parse_exif_datetime(value)

        if taken_at:
            return taken_at

    return None


def read_identity_metadata(image: Image.Image) -> dict:
    """
    Camera serial and sub-second capture time for the metadata identity.

    Best-effort, like taken_at: missing tags are normal (edited exports) and
    must never fail the integrity check. The capture time is read with the
    same rules as read_taken_at(), so seconds always come from the same tag.
    """

    result = {"exif_serial": None, "exif_subsec": None}

    try:
        exif = image.getexif()
    except Exception:
        return result

    if not exif:
        return result

    try:
        sub_ifd = exif.get_ifd(EXIF_SUB_IFD)
    except Exception:
        sub_ifd = {}

    serial = (sub_ifd or {}).get(EXIF_BODY_SERIAL) or exif.get(EXIF_BODY_SERIAL)
    subsec = (sub_ifd or {}).get(EXIF_SUB_SEC_ORIGINAL) or exif.get(
        EXIF_SUB_SEC_ORIGINAL
    )

    if serial is not None:
        result["exif_serial"] = str(serial).strip() or None

    if subsec is not None:
        result["exif_subsec"] = str(subsec).strip() or None

    return result


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
        result["sha256"] = calculate_sha256(path)

        with Image.open(path) as image:
            result["container_format"] = image.format

            if image.format not in SUPPORTED_FORMATS:
                raise ValueError(
                    f"Unsupported format: {image.format}"
                )

            result["width"], result["height"] = image.size
            result["frame_count"] = getattr(image, "n_frames", 1)
            # Capture date of frame 0 (MPO), best-effort: never fails the check.
            result["taken_at"] = read_taken_at(image)
            result.update(read_identity_metadata(image))

            image.verify()

        with Image.open(path) as image:
            image.seek(0)
            image.load()

        result["decoded"] = True
        result["integrity_status"] = "VALID"

    except Exception as exc:
        result["error"] = redact_paths(str(exc), path)

    return result


@dataclass(frozen=True)
class Discovery:
    """
    Supported files below a folder plus what the date filter dropped.

    *excluded_by_period* counts files that exist and have a supported
    extension but fall outside the requested window, so a scan can say
    "в папке 5000 файлов, в периоде — 120" without a second walk.
    """

    files: list[Path]
    excluded_by_period: int


def file_date(path: Path) -> date | None:
    """
    Calendar date of the file's own timestamp (mtime), local timezone.

    This is the "дата загрузки" of the source tree: when the file appeared or
    was last written on the volume — not the EXIF capture date. Reading EXIF
    would require reading the whole file, which is exactly what the shallow
    filter must avoid. A file whose stat() fails (network share gone) returns
    None and is kept by `date_in_period`.
    """

    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date()
    except OSError:
        return None


def date_in_period(
    value: date | None,
    since: date | None,
    until: date | None,
) -> bool:
    """
    Inclusive date window; None means "no bound" on either side.

    An unknown date (unreadable EXIF, failed stat) is kept: a network hiccup
    must not look like "the file is too old".
    """

    if value is None:
        return True
    if since is not None and value < since:
        return False
    if until is not None and value > until:
        return False
    return True


def discover(
    directory: str | Path,
    *,
    recursive: bool = True,
    since: date | None = None,
    until: date | None = None,
) -> Discovery:
    """
    Source files with a supported extension below *directory*.

    Recursive by default (the working folder is a tree with subfolders); the
    result is sorted so repeated runs are deterministic. *since*/*until* are
    an inclusive window over the file's own date (see `file_date`).
    """

    root = Path(directory)
    walker = root.rglob if recursive else root.glob
    pattern = "*"

    matched: list[Path] = []
    excluded = 0

    for path in walker(pattern):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if date_in_period(file_date(path), since, until):
            matched.append(path)
        else:
            excluded += 1

    return Discovery(files=sorted(matched), excluded_by_period=excluded)


def discover_files(
    directory: str | Path,
    *,
    recursive: bool = True,
    since: date | None = None,
    until: date | None = None,
) -> list[Path]:
    """`discover()` reduced to the file list (kept for existing callers)."""

    return discover(
        directory, recursive=recursive, since=since, until=until
    ).files


def scan_directory(
    directory: str | Path,
    *,
    recursive: bool = True,
    since: date | None = None,
    until: date | None = None,
) -> dict:
    """
    Count supported photos and their total size without reading them.

    Used by the folder picker: it must not hash or decode anything, and it
    must not touch the database.
    """

    discovery = discover(
        directory, recursive=recursive, since=since, until=until
    )
    files = discovery.files
    total = 0

    for path in files:
        try:
            total += path.stat().st_size
        except OSError:
            # A file that disappeared mid-scan is simply not counted.
            continue

    return {
        "path": str(directory),
        "files": len(files),
        "bytes": total,
        "excluded_by_period": discovery.excluded_by_period,
    }


def check_directory(directory: str | Path) -> list[dict]:
    return [check_file(p) for p in discover_files(directory)]

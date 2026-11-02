"""
Smart search by an uploaded photo (backlog item 2, first increment: photos).

The uploaded image is transient: it is written to a dedicated working folder,
described by the local QWEN vision model and deleted as soon as the job
finishes. Nothing is added to the photo tables - only the job result keeps the
description and the matched photo_ids.

Search backend: the QWEN description of the uploaded image (description,
brand, category, client) plus its tags are matched against the stored QWEN
metadata of the base photos. No second model call is made, so the mapping from
image to search terms stays deterministic: the model that describes the query
image is the same one that described the base.

Inference never runs here: the API stores the file and enqueues MEDIA_SEARCH;
the worker calls describe() and run().
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from app.api.crop_search import search_by_hash
from app.api.nl_search import MAX_PER_TERM, MAX_TOTAL

# The raw answer may still carry a literal <think> block; it is not a search
# phrase, so it is dropped before the fallback text is used.
_THINK_TAGS = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

MAX_FILE_BYTES = int(os.getenv("SCENE_SEARCH_MAX_BYTES", 25 * 1024 * 1024))

# A video query is bigger than a photo one: a 20-second phone clip is a few
# tens of megabytes.
MAX_VIDEO_BYTES = int(
    os.getenv("SCENE_SEARCH_MAX_VIDEO_BYTES", 300 * 1024 * 1024)
)

# Ролики короткие (владелец: «не более 20 секунд»), и кадры из них берутся
# по секундам 2, 4, 6 … — столько, сколько влезает в длительность.
MAX_VIDEO_SECONDS = float(os.getenv("SCENE_SEARCH_MAX_VIDEO_SECONDS", "20"))
FRAME_SECONDS = (2, 4, 6, 8, 10, 12, 14, 16, 18)
MAX_FRAMES = len(FRAME_SECONDS)

# Deliberately outside SCENE_INBOX: query files are working copies, not photo
# sources, and must never look like INGEST input.
QUERY_DIR = Path(os.getenv("SCENE_SEARCH_QUERY_DIR", "data/media_search"))

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov", ".mpeg", ".mpg"}

ALLOWED_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_CHUNK = 1024 * 1024

# Stale query files (worker killed mid-job) are pruned opportunistically.
MAX_AGE_SECONDS = 24 * 3600


def sanitize_filename(name: str | None) -> str | None:
    """Return a safe basename with an allowed image extension, or None."""

    base = os.path.basename(name or "").strip()

    if not base:
        return None

    base = _SAFE_CHARS.sub("_", base)

    if base in {"", ".", ".."}:
        return None

    if Path(base).suffix.lower() not in ALLOWED_SUFFIXES:
        return None

    return base


def prune_stale() -> int:
    """Delete query files older than MAX_AGE_SECONDS; returns how many."""

    if not QUERY_DIR.is_dir():
        return 0

    removed = 0
    deadline = time.time() - MAX_AGE_SECONDS

    for entry in QUERY_DIR.iterdir():
        try:
            if entry.is_file() and entry.stat().st_mtime < deadline:
                entry.unlink()
                removed += 1
        except OSError:
            continue

    return removed


def store_query(
    filename: str | None,
    stream,
    *,
    max_bytes: int | None = None,
) -> Path:
    """
    Store one uploaded query file (photo or video) under QUERY_DIR.

    The name is sanitized, the size is bounded (photos and videos have
    different caps) and the file is written to a unique path (mkstemp, mode
    0600) so two uploads can never collide and a failed write never leaves a
    partial file behind. The client's own name is only kept as the stem: the
    file is a short-lived working copy.
    """

    import tempfile

    limit = MAX_FILE_BYTES if max_bytes is None else int(max_bytes)

    safe_name = sanitize_filename(filename)

    if safe_name is None:
        raise ValueError("unsupported image name or extension")

    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    prune_stale()

    stem = Path(safe_name).stem
    suffix = Path(safe_name).suffix.lower()

    handle_fd, temp_name = tempfile.mkstemp(
        prefix=f"{stem}_",
        suffix=suffix,
        dir=QUERY_DIR,
    )
    temp_path = Path(temp_name)

    written = 0

    try:
        with os.fdopen(handle_fd, "wb") as handle:
            while True:
                chunk = stream.read(_CHUNK)

                if not chunk:
                    break

                written += len(chunk)

                if written > limit:
                    raise ValueError(
                        "файл слишком большой: "
                        f"{written / 1024 / 1024:.1f} МБ, "
                        f"предел {limit / 1024 / 1024:.0f} МБ"
                    )

                handle.write(chunk)

        if written == 0:
            raise ValueError("empty file")
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return temp_path


def verify_image(path: Path) -> None:
    """Decode the stored file; a file the decoder rejects is not a query."""

    from PIL import Image

    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            image.seek(0)
            image.load()
    except Exception as exc:
        raise ValueError(f"not a decodable image: {exc}") from exc


def kind_for(path: str | Path) -> str:
    """'video' for the video extensions, 'image' otherwise."""

    return "video" if Path(path).suffix.lower() in VIDEO_SUFFIXES else "image"


def frame_times(duration: float, *, seconds=FRAME_SECONDS) -> list[float]:
    """
    Моменты съёмки кадров: 2, 4, 6 … секунда — сколько влезает в ролик.

    У совсем короткого ролика кадр берётся один, из середины: иначе искать
    было бы не по чему.
    """

    times = [float(value) for value in seconds if value < duration - 0.1]

    if not times:
        times = [max(0.0, duration / 2)]

    return times[:MAX_FRAMES]


def video_metadata(path: str | Path) -> dict:
    """
    Basic facts about a video, read by OpenCV (there is no ffmpeg on this box).

    Raises ValueError when the file cannot be opened or is longer than a query
    may be - the modal shows these details back to the user.
    """

    import cv2

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        capture.release()
        raise ValueError(
            "видео не читается: формат или кодек не поддерживается "
            "(принимаются MP4 и MPEG)"
        )

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fourcc = int(capture.get(cv2.CAP_PROP_FOURCC) or 0)
    finally:
        capture.release()

    codec = "".join(
        chr((fourcc >> (8 * index)) & 0xFF) for index in range(4)
    ).strip()

    duration = frames / fps if fps > 0 and frames > 0 else 0.0

    if duration <= 0 or width <= 0 or height <= 0:
        raise ValueError(
            "видео не читается: не удалось определить длительность или размер"
        )

    if duration > MAX_VIDEO_SECONDS:
        raise ValueError(
            f"ролик длиннее {MAX_VIDEO_SECONDS:.0f} с: "
            f"{duration:.1f} с — обрежьте его или возьмите другой"
        )

    return {
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "frames": int(frames),
        "duration_sec": round(duration, 2),
        "codec": codec,
    }


def frames_dir(path: str | Path) -> Path:
    """Папка кадров рядом с загруженным роликом."""

    path = Path(path)

    return path.parent / f"{path.stem}_frames"


def extract_frames(
    path: str | Path,
    *,
    seconds=FRAME_SECONDS,
) -> list[dict]:
    """
    [{path, sec}] — кадры ролика, сохранённые рядом с ним.

    Кадры лежат в отдельной папке, поэтому удаление запроса удаляет и их.
    """

    import cv2

    path = Path(path)
    meta = video_metadata(path)

    target = frames_dir(path)
    target.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(path))
    saved: list[dict] = []

    try:
        for index, moment in enumerate(
            frame_times(meta["duration_sec"], seconds=seconds),
            start=1,
        ):
            capture.set(cv2.CAP_PROP_POS_MSEC, moment * 1000)
            ok, frame = capture.read()

            if not ok or frame is None:
                continue

            out = target / f"frame_{index:02d}_s{int(moment):02d}.jpg"

            if cv2.imwrite(str(out), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88]):
                saved.append({"path": out, "sec": float(moment)})
    finally:
        capture.release()

    if not saved:
        raise ValueError("из ролика не удалось извлечь ни одного кадра")

    return saved


def verify_media(path: str | Path) -> dict:
    """
    Check that the upload really is a photo or a video; return the video facts.

    Photos go through the PIL decoder, videos are opened by OpenCV. Anything
    the decoders reject is refused here with a readable reason.
    """

    if kind_for(path) == "video":
        return video_metadata(path)

    verify_image(path)

    return {}


def delete_query(path: str | Path) -> bool:
    """Remove a query file (and the frames of a video query)."""

    import shutil

    path = Path(path)

    removed = False

    try:
        path.unlink()
        removed = True
    except FileNotFoundError:
        pass
    except OSError:
        pass

    folder = frames_dir(path)

    if folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)

    return removed


def discard_query_file(path: object) -> bool:
    """
    Delete a job's query image, but only if it really lives in QUERY_DIR.

    Used when a queued job is cancelled: the worker never runs it, so nothing
    else would remove the uploaded file. The containment check keeps a crafted
    job payload from turning this into "delete any file on the server".
    """

    if not isinstance(path, str) or not path:
        return False

    try:
        candidate = Path(path).resolve(strict=True)
        root = QUERY_DIR.resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, ValueError):
        return False

    return delete_query(candidate)


def description_filters(fields: dict) -> dict:
    """
    Turn the QWEN fields of the query image into search filters.

    `q` carries the free-text description; brand/category/client are searched
    as exact metadata matches (the same columns the text search already uses).
    `tags` travels as its own list of terms: the user edits them in the manual
    window, so they must reach the search, not just fold into `q`.
    """

    def clean(value: object) -> str | None:
        if not isinstance(value, str):
            return None

        value = value.strip()
        return value or None

    tags = fields.get("tags")
    tag_list: list[str] = []

    if isinstance(tags, list):
        for tag in tags:
            cleaned = clean(tag)

            if cleaned and cleaned not in tag_list:
                tag_list.append(cleaned)

    joined_tags = ", ".join(tag_list)

    return {
        "q": clean(fields.get("description")) or joined_tags or None,
        "client": clean(fields.get("client")),
        "brand": clean(fields.get("brand")),
        "category": clean(fields.get("category")),
        "tags": tag_list,
        "address": None,
    }


# Tags are extra free-text terms: bound them so a hand-edited filter set cannot
# turn one search into an unbounded number of queries.
MAX_TAG_TERMS = 12
MAX_TERM_CHARS = 60


def search(filters: dict, *, limit: int = MAX_PER_TERM) -> dict:
    """
    Run the photo search for already-built filters (read-only).

    Photos are ranked by how many query terms they match, so the most relevant
    come first: an exact metadata field (client/brand/category) weighs more than
    the free-text description and tags. Ties keep the order in which the terms
    were scanned, which keeps the result stable for equal scores.
    """

    from app.api import repository

    weighted: list[tuple[str, int]] = [
        (term, weight)
        for term, weight in (
            (filters.get("q"), 1),
            (filters.get("client"), 2),
            (filters.get("brand"), 2),
            (filters.get("category"), 2),
        )
        if term
    ]

    # Extra free-text terms from the edited tag list (weight as the description):
    # a photo matching both the description and a tag outranks one matching only
    # the description.
    seen = {term for term, _ in weighted}

    for raw in list(filters.get("tags") or [])[:MAX_TAG_TERMS]:
        tag = str(raw).strip()

        if not tag or len(tag) > MAX_TERM_CHARS or tag in seen:
            continue

        weighted.append((tag, 1))
        seen.add(tag)

    scores: dict[str, int] = {}
    truncated = False

    for term, weight in weighted:
        items, next_cursor = repository.list_photos(
            limit=limit,
            query=term,
            recognized_only=True,
        )

        if next_cursor is not None:
            truncated = True

        for item in items:
            scores[item.photo_id] = scores.get(item.photo_id, 0) + weight

            if len(scores) >= MAX_TOTAL:
                truncated = True
                break

        if len(scores) >= MAX_TOTAL:
            break

    # Stable sort: equal scores keep insertion order.
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    return {
        "photo_ids": [photo_id for photo_id, _ in ranked],
        "scores": {photo_id: score for photo_id, score in ranked},
        "count": len(ranked),
        "truncated": truncated,
    }


# A query image gets more room than a batch photo: some models ignore
# `think: false` and spend tokens on reasoning before the JSON.
QUERY_MAX_OUTPUT_TOKENS = int(os.getenv("SCENE_SEARCH_MAX_TOKENS", "1024"))

# Longest raw-model text kept as a search phrase when the JSON never arrives.
MAX_FALLBACK_CHARS = 300


def describe(path: str | Path, *, model: str | None = None) -> dict:
    """
    Run the QWEN vision model over the query image (worker only).

    A photo search does not need the strict field set: when the model answers
    with prose instead of JSON (it happens when the reasoning channel eats the
    token budget), the text itself is used as the search phrase instead of
    failing the job.
    """

    from app.qwen.processor import QwenParseError, analyze_image, resolve_settings

    config = {**resolve_settings(), "max_output_tokens": QUERY_MAX_OUTPUT_TOKENS}

    try:
        fields, _raw, seconds = analyze_image(
            str(path),
            model=model or config.get("model"),
            config=config,
        )
    except QwenParseError as exc:
        text = _plain_text(exc.raw)

        if not text:
            raise

        return {
            "fields": {
                "description": text[:MAX_FALLBACK_CHARS],
                "address": None,
                "client": None,
                "brand": None,
                "category": None,
                "tags": [],
            },
            "seconds": 0.0,
            "fallback": True,
        }

    return {"fields": fields, "seconds": seconds, "fallback": False}


def _plain_text(raw: str) -> str:
    """Reduce a model answer to a single-line search phrase."""

    text = _THINK_TAGS.sub(" ", str(raw or ""))
    return " ".join(text.split())


def _merge_fields(frame_fields: list[dict]) -> dict:
    """
    Свести ответы по кадрам в один.

    Теги — объединение (по ним и идёт поиск), описание/адрес/клиент/бренд/
    категория — первые непустые, чтобы в окне было что показать.
    """

    tags: list[str] = []

    merged = {
        "description": None,
        "address": None,
        "client": None,
        "brand": None,
        "category": None,
        "tags": tags,
    }

    for fields in frame_fields:
        for key in ("description", "address", "client", "brand", "category"):
            value = fields.get(key)

            if value and not merged[key]:
                merged[key] = value

        for tag in fields.get("tags") or []:
            text = str(tag).strip()

            if text and text not in tags:
                tags.append(text)

    return merged


def run(
    path: str | Path,
    *,
    kind: str | None = None,
    progress=None,
    mode: str = "auto",
    frame_seconds: float | None = None,
) -> dict:
    """
    Describe the uploaded photo/video and search the base with that description.

    A video is described frame by frame — кадры берутся по фиксированным
    секундам ролика (2, 4, 6 …), поиск идёт по каждому кадру, а результаты
    объединяются: фото — сумма без повторов, теги — объединение,
    описание/адрес/клиент/бренд — первые непустые.

    `progress(done, total, stage)` вызывается перед каждым кадром: по нему
    окно рисует полосу и замечает отмену.

    *mode*: "auto" — описать и искать; "describe" — только описать (ручной
    режим: окно показывает поля, пользователь их правит и запускает поиск
    отдельным запросом).

    *frame_seconds*: для видео — описать только один кадр в эту секунду
    (ручной выбор кадра); иначе описываются все фиксированные кадры.

    Returns a serialisable result for the job row.
    """

    if mode not in ("auto", "describe"):
        raise ValueError("mode must be 'auto' or 'describe'")

    if frame_seconds is not None and frame_seconds < 0:
        raise ValueError("frame_seconds must be >= 0")

    kind = kind or kind_for(path)

    if kind == "video":
        sources = (
            extract_frames(path, seconds=(float(frame_seconds),))
            if frame_seconds is not None
            else extract_frames(path)
        )
    else:
        sources = [{"path": Path(path), "sec": None}]

    total = len(sources)

    frame_fields: list[dict] = []
    per_frame: list[dict] = []
    photo_ids: dict[str, None] = {}
    hash_matches: dict[tuple[str, int], dict] = {}
    hash_query = None
    hash_query_phash = None
    seconds_total = 0.0
    truncated = False
    fallback = False

    for index, source in enumerate(sources, start=1):
        if progress is not None:
            stage = (
                f"кадр {index} из {total} ({source['sec']:.0f} с)"
                if source["sec"] is not None
                else "распознавание"
            )
            progress(index - 1, total, stage)

        described = describe(source["path"])
        fields = described["fields"]

        seconds_total += float(described["seconds"] or 0.0)
        fallback = fallback or bool(described.get("fallback"))
        frame_fields.append(fields)

        found = (
            search(description_filters(fields))
            if mode == "auto"
            else {"photo_ids": [], "count": 0, "truncated": False}
        )
        truncated = truncated or bool(found["truncated"])

        for photo_id in found["photo_ids"]:
            photo_ids.setdefault(photo_id, None)

        # Hash search is an independent candidate source (OR with QWEN):
        # metadata can differ for the same creative, while the crop hash
        # still finds the same banner.
        hash_found = (
            search_by_hash(source["path"]) if mode == "auto" else None
        )
        if hash_found is not None:
            hash_query = hash_found.get("query_hash")
            hash_query_phash = hash_found.get("query_phash")
            for match in hash_found.get("matches") or []:
                photo_ids.setdefault(match["photo_id"], None)
                key = (match["photo_id"], match["region_id"])
                previous = hash_matches.get(key)
                if previous is None or match["distance"] < previous["distance"]:
                    hash_matches[key] = {**match, "sec": source["sec"]}

        per_frame.append(
            {
                "sec": source["sec"],
                "description": fields.get("description"),
                "client": fields.get("client"),
                "brand": fields.get("brand"),
                "category": fields.get("category"),
                "tags": list(fields.get("tags") or []),
                "count": found["count"],
                "hash_count": len(hash_found.get("matches") or []) if hash_found else 0,
            }
        )

        # Общий предел поиска: дальше кадры смотреть смысла нет.
        if len(photo_ids) >= MAX_TOTAL:
            truncated = True
            break

    if progress is not None:
        progress(total, total, "готово")

    merged = _merge_fields(frame_fields)

    # OR, not AND: a hash-near crop is a hit even when QWEN described the
    # layout differently. Hash-near photos go first (and carry a distance),
    # then the remaining metadata matches.
    ordered_hash = sorted(
        hash_matches.values(),
        key=lambda item: (item["distance"], item["photo_id"], item["crop_index"]),
    )
    ordered_ids: list[str] = []
    seen: set[str] = set()

    for match in ordered_hash:
        if match["photo_id"] not in seen:
            seen.add(match["photo_id"])
            ordered_ids.append(match["photo_id"])

    for photo_id in photo_ids:
        if photo_id not in seen:
            seen.add(photo_id)
            ordered_ids.append(photo_id)

    result = {
        "kind": kind,
        "mode": mode,
        "frames_count": total,
        "per_frame": per_frame,
        "filters": description_filters(merged),
        "qwen": merged,
        "qwen_time_sec": round(seconds_total, 3),
        # True when the model answered with prose and the text itself became
        # the search phrase.
        "fallback": fallback,
        "photo_ids": ordered_ids,
        "count": len(ordered_ids),
        "truncated": truncated,
        "hash_query": hash_query,
        "hash_query_phash": hash_query_phash,
        "hash_matches": [
            {key: value for key, value in match.items() if key != "sec"}
            for match in ordered_hash[:50]
        ],
    }

    _write_search_log(path, kind, result)
    return result


def _write_search_log(path: str | Path, kind: str, result: dict) -> None:
    """Append one JSON line per search: distances, photo and address."""
    try:
        log_path = Path(
            os.getenv("SCENE_SEARCH_LOG", "data/logs/media_search.log")
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        line = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "kind": kind,
            "query": Path(path).name,
            "photo_ids": len(result.get("photo_ids") or []),
            "hash_matches": [
                {
                    "photo_id": item["photo_id"],
                    "crop_index": item["crop_index"],
                    "distance": item["distance"],
                    "dhash_distance": item.get("dhash_distance"),
                    "phash_distance": item.get("phash_distance"),
                    "address": item.get("address"),
                }
                for item in result.get("hash_matches") or []
            ],
            "truncated": bool(result.get("truncated")),
        }
        with log_path.open("a", encoding="utf-8") as sink:
            sink.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        # The search result must not fail because the log file is unwritable.
        pass

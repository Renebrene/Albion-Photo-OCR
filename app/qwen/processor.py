"""
QWEN metadata extraction through Ollama.

Runs as a deferred job (job_type QWEN_PHOTO). It is a parallel process:
independent from DINO/HYBRID and never touching photo identity.

Uses only the standard library for HTTP, so no extra dependency is required.
"""

from __future__ import annotations

import base64
import io
import json
import re
import time
import urllib.request

from PIL import Image

from app import settings_store
from app.qwen import database as db
from app.qwen.config import (
    OLLAMA_URL,
    QWEN_FIELDS,
    QWEN_MODEL,
    QWEN_TIMEOUT,
)

MAX_IMAGE_SIDE = 1280

# Settings key holding the runtime-selected QWEN model.
QWEN_MODEL_KEY = "qwen_model"


def resolve_model() -> str:
    """Runtime model: value from settings, else the environment default."""

    try:
        stored = settings_store.get(QWEN_MODEL_KEY)
    except Exception:
        stored = None

    return str(stored or QWEN_MODEL)


def list_models() -> list[dict]:
    """Return the models available in the local Ollama instance."""

    with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=15) as response:
        payload = json.loads(response.read())

    return [
        {"name": item.get("name"), "size": item.get("size")}
        for item in payload.get("models", [])
    ]


def unload_model(model: str | None = None) -> None:
    """Ask Ollama to unload a model from memory (free VRAM)."""

    body = json.dumps(
        {"model": model or resolve_model(), "keep_alive": 0}
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        response.read()

PROMPT = (
    "Ты анализируешь фотографию городской застройки/вывески. "
    "Верни СТРОГО JSON без пояснений со следующими ключами: "
    "description (краткое описание сцены, строка), "
    "address (видимый адрес или ориентир, строка или null), "
    "client (компания/клиент с вывески, строка или null), "
    "brand (бренд, строка или null), "
    "category (категория объекта, строка или null), "
    "tags (массив коротких строк). "
    "Если данных нет — используй null, не выдумывай."
)


def encode_image(path: str) -> str:
    """Load an image (MPO frame 0), downscale it and return base64 JPEG."""

    with Image.open(path) as image:
        if getattr(image, "n_frames", 1) > 1:
            image.seek(0)

        image = image.convert("RGB")

        width, height = image.size
        longest = max(width, height)

        if longest > MAX_IMAGE_SIDE:
            scale = MAX_IMAGE_SIDE / longest
            image = image.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.Resampling.LANCZOS,
            )

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)

    return base64.b64encode(buffer.getvalue()).decode("ascii")


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_result(content) -> dict:
    """Normalize the model's JSON into the expected field set."""

    if isinstance(content, dict):
        data = content
    else:
        text = str(content).strip()

        if not text:
            raise ValueError("QWEN response is empty")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fall back to the first {...} block (models sometimes wrap the
            # JSON in surrounding prose).
            match = _JSON_OBJECT_RE.search(text)

            if match is None:
                raise ValueError("QWEN response has no JSON object")

            data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("QWEN response is not a JSON object")

    result: dict = {}

    for key in QWEN_FIELDS:
        value = data.get(key)
        if isinstance(value, str):
            value = value.strip() or None
        result[key] = value

    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]
    elif isinstance(tags, list):
        tags = [str(part).strip() for part in tags if str(part).strip()]
    else:
        tags = []

    result["tags"] = tags

    return result


def analyze_image(
    path: str,
    model: str | None = None,
) -> tuple[dict, dict, float]:
    """Send one image to Ollama and return (fields, raw_payload, seconds)."""

    model = model or resolve_model()

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [encode_image(path)],
                }
            ],
            "stream": False,
            "format": "json",
            # Disable "thinking" where supported so the answer lands in
            # message.content rather than message.thinking.
            "think": False,
            # Unload the model from memory right after this request (free VRAM).
            "keep_alive": 0,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    started = time.perf_counter()

    with urllib.request.urlopen(request, timeout=QWEN_TIMEOUT) as response:
        payload = json.loads(response.read())

    elapsed = time.perf_counter() - started

    message = payload.get("message", {})
    # Fall back to the reasoning channel if the model left content empty.
    content = message.get("content") or message.get("thinking") or ""

    return parse_result(content), payload, elapsed


def run_photo(photo_id: str) -> dict:
    """Full pipeline for one photo: load source, analyze, persist."""

    source_path = db.get_photo_source(photo_id)

    if not source_path:
        raise ValueError(f"photo not found: {photo_id}")

    model = resolve_model()

    db.mark_running(photo_id)

    try:
        fields, raw, elapsed = analyze_image(source_path, model)
    except Exception as exc:
        db.save_failure(photo_id, str(exc))
        raise

    db.save_success(
        photo_id,
        fields=fields,
        raw=raw,
        model=model,
        time_sec=elapsed,
    )

    return {
        "photo_id": photo_id,
        "model": model,
        "time_sec": round(elapsed, 2),
        **fields,
    }

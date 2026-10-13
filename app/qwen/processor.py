"""
QWEN metadata extraction.

Runs as a deferred job (job_type QWEN_PHOTO). It is a parallel process:
independent from DINO/HYBRID and never touching photo identity.

Two providers are supported:
  * `ollama` — local Ollama (default; nothing leaves the machine);
  * `openai` — an OpenAI-compatible HTTP endpoint (cloud; images are uploaded
    to that endpoint, so it must be enabled explicitly).

Uses only the standard library for HTTP, so no extra dependency is required.
"""

from __future__ import annotations

import base64
import io
import json
import re
import time
import urllib.error
import urllib.request

from PIL import Image

from app import settings_store
from app.core.errors import redact_absolute_paths
from app.qwen import database as db
from app.qwen.config import (
    OLLAMA_URL,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
    PROVIDERS,
    QWEN_BASE_URL,
    QWEN_FIELDS,
    QWEN_KEEP_ALIVE,
    QWEN_MODEL,
    QWEN_PROVIDER,
    QWEN_TIMEOUT,
    QWEN_UNLOAD_ON_IDLE,
)

MAX_IMAGE_SIDE = 1280

PROMPT = (
    "Ты анализируешь фотографию городской застройки/вывески. "
    "Верни СТРОГО JSON без пояснений со следующими ключами: "
    "description (краткое описание сцены, строка), "
    "address (видимый адрес или ориентир, строка или null), "
    "client (компания/клиент с вывески, строка или null), "
    "brand (бренд, строка или null), "
    "category (категория объекта, строка или null), "
    "tags (массив не более 10 коротких строк). "
    "Ответ должен быть коротким и полностью закрытым JSON. "
    "Если данных нет — используй null, не выдумывай."
)

# Output cap: without it the model occasionally truncates the JSON mid-array
# (done_reason "length"), which then fails to parse.
MAX_OUTPUT_TOKENS = 512

# Settings keys (runtime overrides of the environment defaults).
QWEN_PROVIDER_KEY = "qwen_provider"
QWEN_MODEL_KEY = "qwen_model"
QWEN_BASE_URL_KEY = "qwen_base_url"
QWEN_API_KEY_KEY = "qwen_api_key"
QWEN_KEEP_ALIVE_KEY = "qwen_keep_alive"
QWEN_UNLOAD_IDLE_KEY = "qwen_unload_on_idle"


def _stored(key: str):
    try:
        return settings_store.get(key)
    except Exception:
        return None


def resolve_settings() -> dict:
    """Runtime QWEN configuration (settings override environment defaults)."""

    provider = str(_stored(QWEN_PROVIDER_KEY) or QWEN_PROVIDER).strip().lower()

    if provider not in PROVIDERS:
        provider = PROVIDER_OLLAMA

    keep_alive = _stored(QWEN_KEEP_ALIVE_KEY)

    unload_idle = _stored(QWEN_UNLOAD_IDLE_KEY)

    return {
        "provider": provider,
        "model": str(_stored(QWEN_MODEL_KEY) or QWEN_MODEL),
        "base_url": str(_stored(QWEN_BASE_URL_KEY) or QWEN_BASE_URL).rstrip("/"),
        "api_key": str(_stored(QWEN_API_KEY_KEY) or ""),
        "keep_alive": (
            str(keep_alive) if keep_alive is not None else QWEN_KEEP_ALIVE
        ),
        "unload_on_idle": (
            bool(unload_idle)
            if unload_idle is not None
            else QWEN_UNLOAD_ON_IDLE
        ),
        "timeout": QWEN_TIMEOUT,
        "ollama_url": OLLAMA_URL,
    }


def resolve_model() -> str:
    """Runtime model: value from settings, else the environment default."""

    return resolve_settings()["model"]


def mask_api_key(api_key: str) -> str | None:
    """Return a display-safe api key (never the full secret)."""

    if not api_key:
        return None

    if len(api_key) <= 8:
        return "…" + api_key[-2:]

    return "…" + api_key[-4:]


def public_settings() -> dict:
    """Settings safe to return over the API (api key masked)."""

    config = resolve_settings()

    return {
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config["base_url"],
        "api_key_set": bool(config["api_key"]),
        "api_key_hint": mask_api_key(config["api_key"]),
        "keep_alive": config["keep_alive"],
        "unload_on_idle": config["unload_on_idle"],
    }


def update_settings(
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    keep_alive: str | None = None,
    unload_on_idle: bool | None = None,
) -> dict:
    """Persist the supplied settings; return the public view."""

    if provider is not None:
        provider = provider.strip().lower()
        if provider not in PROVIDERS:
            raise ValueError(f"unknown provider: {provider}")
        settings_store.set_value(QWEN_PROVIDER_KEY, provider)

    if model is not None:
        settings_store.set_value(QWEN_MODEL_KEY, model)

    if base_url is not None:
        settings_store.set_value(QWEN_BASE_URL_KEY, base_url.rstrip("/"))

    # An empty api_key clears it; None leaves it unchanged.
    if api_key is not None:
        settings_store.set_value(QWEN_API_KEY_KEY, api_key)

    if keep_alive is not None:
        settings_store.set_value(QWEN_KEEP_ALIVE_KEY, str(keep_alive))

    if unload_on_idle is not None:
        settings_store.set_value(QWEN_UNLOAD_IDLE_KEY, bool(unload_on_idle))

    return public_settings()


# ---------------------------------------------------------------------------
# Transport: Ollama (local)
# ---------------------------------------------------------------------------


def _ollama_list_models(config: dict) -> list[dict]:
    url = f"{config['ollama_url']}/api/tags"

    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.loads(response.read())

    return [
        {"name": item.get("name"), "size": item.get("size")}
        for item in payload.get("models", [])
    ]


def _ollama_unload(config: dict, model: str) -> None:
    body = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")

    request = urllib.request.Request(
        f"{config['ollama_url']}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        response.read()


def _ollama_analyze(config: dict, path: str) -> tuple[dict, dict, float]:
    body = json.dumps(
        {
            "model": config["model"],
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
            # Keep the model warm between consecutive jobs; settings control
            # the window (0 unloads immediately after each request).
            "keep_alive": config["keep_alive"],
            "options": {"temperature": 0, "num_predict": MAX_OUTPUT_TOKENS},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{config['ollama_url']}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    payload = _post_json(request, config["timeout"])

    message = payload.get("message", {})
    # Fall back to the reasoning channel if the model left content empty.
    content = message.get("content") or message.get("thinking") or ""

    return parse_result(content), payload, 0.0


# ---------------------------------------------------------------------------
# Transport: OpenAI-compatible (cloud)
# ---------------------------------------------------------------------------


def _openai_headers(config: dict) -> dict:
    headers = {"Content-Type": "application/json"}

    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    return headers


def _openai_list_models(config: dict) -> list[dict]:
    if not config["base_url"]:
        raise ValueError("qwen_base_url is not configured")

    request = urllib.request.Request(
        f"{config['base_url']}/models",
        headers=_openai_headers(config),
    )

    payload = _get_json(request, 15)

    return [
        {"name": item.get("id"), "size": None}
        for item in payload.get("data", [])
    ]


def _openai_analyze(config: dict, path: str) -> tuple[dict, dict, float]:
    if not config["base_url"]:
        raise ValueError("qwen_base_url is not configured")

    image = encode_image(path)

    body = json.dumps(
        {
            "model": config["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image}"
                            },
                        },
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{config['base_url']}/chat/completions",
        data=body,
        headers=_openai_headers(config),
    )

    payload = _post_json(request, config["timeout"])

    choices = payload.get("choices") or []

    if not choices:
        raise ValueError("cloud provider returned no choices")

    content = (choices[0].get("message") or {}).get("content") or ""

    return parse_result(content), payload, 0.0


def _get_json(request, timeout: float) -> dict:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _post_json(request, timeout: float) -> dict:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


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
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def parse_result(content) -> dict:
    """Normalize the model's JSON into the expected field set."""

    if isinstance(content, dict):
        data = content
    else:
        text = str(content).strip()

        # Some models wrap their reasoning in a literal <think>...</think>
        # block even when thinking is disabled; drop it before parsing.
        text = _THINK_RE.sub("", text).strip()

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


def list_models(config: dict | None = None) -> list[dict]:
    """Return the models available for the active provider."""

    config = config or resolve_settings()

    if config["provider"] == PROVIDER_OPENAI:
        return _openai_list_models(config)

    return _ollama_list_models(config)


def unload_model(model: str | None = None) -> bool:
    """
    Free the local model (Ollama only). Returns True when an unload was sent.

    The cloud provider holds no local state, so this is a no-op there.
    """

    config = resolve_settings()

    if config["provider"] != PROVIDER_OLLAMA:
        return False

    _ollama_unload(config, model or config["model"])
    return True


def analyze_image(
    path: str,
    model: str | None = None,
    config: dict | None = None,
) -> tuple[dict, dict, float]:
    """Send one image to the active provider; return (fields, raw, seconds)."""

    config = config or resolve_settings()

    if model:
        config = {**config, "model": model}

    started = time.perf_counter()

    if config["provider"] == PROVIDER_OPENAI:
        fields, payload, _ = _openai_analyze(config, path)
    else:
        fields, payload, _ = _ollama_analyze(config, path)

    return fields, payload, time.perf_counter() - started


def chat_text(prompt: str, config: dict | None = None) -> str:
    """
    One-shot text completion through the active provider.

    Used by the NL-search job (text-only). Returns the raw content string for
    the caller to parse.
    """

    config = config or resolve_settings()

    if config["provider"] == PROVIDER_OPENAI:
        if not config["base_url"]:
            raise ValueError("qwen_base_url is not configured")

        body = json.dumps(
            {
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{config['base_url']}/chat/completions",
            data=body,
            headers=_openai_headers(config),
        )
        payload = _post_json(request, config["timeout"])
        choices = payload.get("choices") or []

        if not choices:
            raise ValueError("cloud provider returned no choices")

        return (choices[0].get("message") or {}).get("content") or ""

    body = json.dumps(
        {
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "think": False,
            "keep_alive": config["keep_alive"],
            "options": {"temperature": 0},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{config['ollama_url']}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    payload = _post_json(request, config["timeout"])
    message = payload.get("message", {})

    return message.get("content") or message.get("thinking") or ""


def run_photo(photo_id: str) -> dict:
    """Full pipeline for one photo: load source, analyze, persist."""

    source_path = db.get_photo_source(photo_id)

    if not source_path:
        raise ValueError(f"photo not found: {photo_id}")

    config = resolve_settings()
    model = config["model"]

    db.mark_running(photo_id)

    try:
        fields, raw, elapsed = analyze_image(source_path, config=config)
    except urllib.error.URLError as exc:
        db.save_failure(
            photo_id,
            redact_absolute_paths(f"provider unavailable: {exc.reason}"),
        )
        raise
    except Exception as exc:
        db.save_failure(photo_id, redact_absolute_paths(str(exc)))
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
        "provider": config["provider"],
        "time_sec": round(elapsed, 2),
        **fields,
    }

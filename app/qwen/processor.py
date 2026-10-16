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
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

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

# Where PREVIEW writes SMALL/MIDDLE JPEGs. Read straight from the environment
# (same convention as app/api/config.py): importing app.core.config here would
# pull torch into the API process, which imports this module for settings.
_PREVIEW_ROOT = Path(os.getenv("SCENE_PREVIEW_ROOT", "data/preview"))

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
QWEN_MODEL_KEYS = {
    PROVIDER_OLLAMA: "qwen_model_ollama",
    PROVIDER_OPENAI: "qwen_model_openai",
}
QWEN_BASE_URL_KEY = "qwen_base_url"
QWEN_CROP_KEY = "qwen_crop"
QWEN_CROP_RATIO_KEY = "qwen_crop_ratio"
QWEN_API_KEY_KEY = "qwen_api_key"
QWEN_KEEP_ALIVE_KEY = "qwen_keep_alive"
QWEN_UNLOAD_IDLE_KEY = "qwen_unload_on_idle"


def _stored(key: str):
    try:
        return settings_store.get(key)
    except Exception:
        return None


def _migrate_legacy_model() -> None:
    """
    Один раз разложить старый единственный ключ `qwen_model` по провайдерам.

    Ключ писался, когда провайдер был один. Если раздельные ключи уже есть,
    старый просто убираем: иначе после переключения провайдера чужое имя
    «прилипало» к другому — в окне у локальной Ollama показывалась модель
    облака. Если раздельных ключей нет вовсе, значение принадлежит текущему
    провайдеру и переносится к нему.
    """

    try:
        legacy = _stored(QWEN_MODEL_KEY)

        if not legacy:
            return

        # Пустая строка = «значения нет»: так ключ перестаёт участвовать.
        if any(_stored(key) for key in QWEN_MODEL_KEYS.values()):
            # Раздельные значения уже есть — старый ключ не приписываем никому:
            # он писался при другом провайдере и «прилипал» к чужому.
            settings_store.set_value(QWEN_MODEL_KEY, "")
            return

        provider = str(
            _stored(QWEN_PROVIDER_KEY) or QWEN_PROVIDER
        ).strip().lower()
        key = QWEN_MODEL_KEYS.get(provider)

        if key:
            settings_store.set_value(key, str(legacy))

        settings_store.set_value(QWEN_MODEL_KEY, "")
    except Exception:  # noqa: BLE001 - без БД работаем на значениях из env
        return


def crop_settings() -> dict:
    """
    Кроп кадра перед отправкой в модель (по умолчанию выключен).

    Большой щит часто занимает лишь центр кадра; если обрезать края, щит
    займёт больше пикселей при том же лимите 1280 px. Режимы:
    `off` — весь кадр (поведение по умолчанию), `center` — центральная часть
    с долей `ratio` от каждой стороны. Настройка живёт в `app_settings`
    (`qwen_crop`, `qwen_crop_ratio`), поэтому меняется без перезапуска.
    """

    mode = str(
        _stored(QWEN_CROP_KEY) or os.getenv("SCENE_QWEN_CROP", "off")
    ).strip().lower()

    if mode not in ("off", "center"):
        mode = "off"

    try:
        ratio = float(
            _stored(QWEN_CROP_RATIO_KEY)
            or os.getenv("SCENE_QWEN_CROP_RATIO", "0.6")
        )
    except (TypeError, ValueError):
        ratio = 0.6

    return {"mode": mode, "ratio": min(max(ratio, 0.2), 1.0)}


def model_for_provider(provider: str) -> str:
    """
    The model saved for one provider, falling back to environment defaults.

    Each provider remembers its own model: у локальной Ollama и у облака разные
    имена, и переключение провайдера не должно терять выбор другого.
    """

    _migrate_legacy_model()

    per_provider = _stored(QWEN_MODEL_KEYS.get(provider, ""))

    if per_provider:
        return str(per_provider)

    return QWEN_MODEL if provider == PROVIDER_OLLAMA else ""


def resolve_settings() -> dict:
    """Runtime QWEN configuration (settings override environment defaults)."""

    provider = str(_stored(QWEN_PROVIDER_KEY) or QWEN_PROVIDER).strip().lower()

    if provider not in PROVIDERS:
        provider = PROVIDER_OLLAMA

    keep_alive = _stored(QWEN_KEEP_ALIVE_KEY)

    unload_idle = _stored(QWEN_UNLOAD_IDLE_KEY)

    return {
        "provider": provider,
        "model": model_for_provider(provider),
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
        "crop": crop_settings(),
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
        # Что запомнено для каждого провайдера: окно показывает оба значения,
        # чтобы при переключении было видно, какая модель вернётся.
        "models": {
            name: model_for_provider(name) for name in PROVIDERS
        },
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
        # The model belongs to the provider being set (or to the current one
        # when only the model is sent), so switching providers keeps both.
        target = provider or str(
            _stored(QWEN_PROVIDER_KEY) or QWEN_PROVIDER
        ).strip().lower()

        settings_store.set_value(
            QWEN_MODEL_KEYS.get(target, QWEN_MODEL_KEY), model
        )

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
                    "images": [encode_image(path, crop=config.get("crop"))],
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
            "options": {
            "temperature": 0,
            # A caller may need a longer answer (the query-image description
            # gets more room); the batch default is unchanged.
            "num_predict": int(
                config.get("max_output_tokens", MAX_OUTPUT_TOKENS)
            ),
        },
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

    limit = int(config.get("max_output_tokens", MAX_OUTPUT_TOKENS))

    # A «thinking» model that spent the whole budget on reasoning: say so
    # instead of failing later with «no JSON object».
    truncated = answer_truncated(payload, content, config["model"], limit)

    if truncated is not None:
        raise truncated

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

    image = encode_image(path, crop=config.get("crop"))

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

    # Облако ограничивает частоту: повторяем с паузой, чтобы массовый прогон
    # не помечал упавшими фото из-за 429.
    payload = _post_json(
        request, config["timeout"], retries=CLOUD_RETRY_ATTEMPTS
    )

    choices = payload.get("choices") or []

    if not choices:
        raise ValueError("cloud provider returned no choices")

    content = (choices[0].get("message") or {}).get("content") or ""

    # The cloud provider reports the same «ran out of budget» as finish_reason.
    truncated = answer_truncated(
        {"done_reason": choices[0].get("finish_reason"), "message": {}},
        content,
        config["model"],
    )

    if truncated is not None:
        raise truncated

    return parse_result(content), payload, 0.0


def _get_json(request, timeout: float) -> dict:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


# Ограничение частоты у облачного провайдера — штатная ситуация: без повторов
# один массовый прогон выжигает квоту и помечает упавшими сотни фото.
CLOUD_RETRY_ATTEMPTS = int(os.getenv("SCENE_QWEN_CLOUD_RETRIES", "3"))
CLOUD_RETRY_DELAY = float(os.getenv("SCENE_QWEN_CLOUD_RETRY_DELAY", "5"))
_RETRYABLE_STATUS = {429, 503, 504}
_MAX_WAIT = 60.0


class ProviderRateLimited(RuntimeError):
    """Провайдер ограничил частоту запросов и не отпустил после повторов."""


def _retry_after(exc: urllib.error.HTTPError) -> float | None:
    headers = getattr(exc, "headers", None)
    raw = headers.get("Retry-After") if headers is not None else None

    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _post_json(
    request, timeout: float, *, retries: int = 1, retry_delay: float | None = None
) -> dict:
    """
    POST one JSON request, retrying a rate-limited provider.

    `retries`/`retry_delay` are for the cloud path; the local Ollama keeps a
    single attempt (a stopped server must fail fast, not wait).
    """

    delay = CLOUD_RETRY_DELAY if retry_delay is None else retry_delay

    for attempt in range(1, max(1, retries) + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            last = attempt >= max(1, retries)

            if last or exc.code not in _RETRYABLE_STATUS:
                if exc.code == 429:
                    raise ProviderRateLimited(
                        "провайдер ограничил частоту запросов (HTTP 429): "
                        "подождите или проверьте лимиты тарифа"
                    ) from exc

                raise

            wait = _retry_after(exc) or delay * (2 ** (attempt - 1))
            time.sleep(min(wait, _MAX_WAIT))
        except urllib.error.URLError:
            if attempt >= max(1, retries):
                raise

            time.sleep(min(delay * (2 ** (attempt - 1)), _MAX_WAIT))

    raise ProviderRateLimited("провайдер недоступен после повторов")


def encode_image(path: str, *, crop: dict | None = None) -> str:
    """
    Load an image (MPO frame 0), optionally crop it, and return base64 JPEG.

    `crop` = {"mode": "off"|"center", "ratio": 0.2..1.0}: центральный кроп
    перед уменьшением — щит занимает больше пикселей при том же лимите.
    """

    with Image.open(path) as image:
        if getattr(image, "n_frames", 1) > 1:
            image.seek(0)

        image = image.convert("RGB")

        if crop and crop.get("mode") == "center":
            ratio = float(crop.get("ratio") or 1.0)

            if 0 < ratio < 1:
                source_width, source_height = image.size
                crop_width = max(1, int(source_width * ratio))
                crop_height = max(1, int(source_height * ratio))
                left = (source_width - crop_width) // 2
                top = (source_height - crop_height) // 2
                image = image.crop(
                    (left, top, left + crop_width, top + crop_height)
                )

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


class QwenParseError(ValueError):
    """
    The model answered, but not with the expected JSON object.

    `raw` keeps the plain text of the answer so a caller that can live with
    unstructured output (a search query, for instance) may still use it. Some
    models ignore `think: false`, so the reasoning channel can hold prose and
    the truncated answer never reaches the JSON.
    """

    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


def answer_truncated(
    payload: dict,
    content: str,
    model: str,
    limit: int = MAX_OUTPUT_TOKENS,
) -> QwenParseError | None:
    """
    The «thinking» failure, turned into a readable error (or None).

    Some models (Qwen3 without the -instruct tag, for instance) reason before
    answering and ignore `think: false`; the whole output budget goes into the
    reasoning and the answer is cut off before the JSON. Left as it is, every
    photo fails with a cryptic «no JSON object» - this says what to do.
    """

    if str(content).strip():
        return None

    if payload.get("done_reason") != "length":
        return None

    return QwenParseError(
        f"модель «{model}» не успела ответить: ответ обрезан по лимиту "
        f"{limit} токенов, всё ушло на рассуждения. Возьмите instruct-модель "
        "(например qwen3-vl:4b-instruct) или модель без «размышлений».",
        raw=str((payload.get("message") or {}).get("thinking") or "")[:2000],
    )


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
            raise QwenParseError("QWEN response is empty")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fall back to the first {...} block (models sometimes wrap the
            # JSON in surrounding prose).
            match = _JSON_OBJECT_RE.search(text)

            if match is None:
                raise QwenParseError(
                    "QWEN response has no JSON object",
                    raw=text,
                )

            data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise QwenParseError(
            "QWEN response is not a JSON object",
            raw=str(content),
        )

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
        payload = _post_json(
            request, config["timeout"], retries=CLOUD_RETRY_ATTEMPTS
        )
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


def analysis_input(photo_id: str, source_path: str) -> str:
    """
    Pick the file to analyse: the local MIDDLE preview when it exists.

    The preview is already the ≤1280 px JPEG that encode_image() would build
    from the original, so the model sees the same input - but the original does
    not have to be read again. That matters when the originals live on a
    network share (INGEST/DINO also read them) and it removes a decode+resize
    per photo. Falls back to the original when the preview is missing.
    """

    if not _PREVIEW_ROOT:
        return source_path

    try:
        from app.preview.generator import build_preview_paths

        middle = build_preview_paths(
            preview_root=_PREVIEW_ROOT,
            photo_id=photo_id,
        ).middle

        if Path(middle).is_file():
            return str(middle)
    except Exception:  # noqa: BLE001 - a missing preview must not fail QWEN
        pass

    return source_path


def run_photo(
    photo_id: str,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Full pipeline for one photo: load source, analyze, persist.

    `provider`/`model` — разовый обход настроек: кнопка «Пересканировать» в
    карточке фото умеет прогнать один снимок локально или в облаке, не меняя
    провайдера для всей очереди.
    """

    source_path = db.get_photo_source(photo_id)

    if not source_path:
        raise ValueError(f"photo not found: {photo_id}")

    config = resolve_settings()

    if provider and provider != config["provider"]:
        if provider not in PROVIDERS:
            raise ValueError(f"unknown provider: {provider}")

        config = {
            **config,
            "provider": provider,
            "model": model or model_for_provider(provider),
        }
    elif model:
        config = {**config, "model": model}

    model = config["model"]

    db.mark_running(photo_id)

    try:
        fields, raw, elapsed = analyze_image(
            analysis_input(photo_id, source_path),
            config=config,
        )
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

"""
Tests for QWEN provider selection and keep-alive (app.qwen.processor).

No network and no PostgreSQL: settings_store and urllib are stubbed.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from app.qwen import processor


@pytest.fixture
def fake_settings(monkeypatch):
    store: dict = {}

    monkeypatch.setattr(
        processor.settings_store, "get", lambda key, default=None: store.get(key, default)
    )
    monkeypatch.setattr(
        processor.settings_store, "set_value", lambda key, value: store.__setitem__(key, value)
    )

    return store


def test_mask_api_key():
    assert processor.mask_api_key("") is None
    assert processor.mask_api_key("sk-abcdefghijkl") == "…ijkl"
    assert processor.mask_api_key("short") == "…rt"


def test_resolve_settings_defaults_to_ollama(fake_settings):
    config = processor.resolve_settings()

    assert config["provider"] == "ollama"
    assert config["keep_alive"]  # non-empty default
    assert config["unload_on_idle"] is True


def test_update_settings_roundtrip_and_masking(fake_settings):
    view = processor.update_settings(
        provider="openai",
        model="gpt-4o-mini",
        base_url="https://api.example.com/v1/",
        api_key="sk-secret-123456",
        keep_alive="2m",
        unload_on_idle=False,
    )

    assert view["provider"] == "openai"
    assert view["model"] == "gpt-4o-mini"
    assert view["base_url"] == "https://api.example.com/v1"  # trailing slash removed
    assert view["api_key_set"] is True
    assert view["api_key_hint"] == "…3456"
    assert "api_key" not in view
    assert view["keep_alive"] == "2m"
    assert view["unload_on_idle"] is False

    # The raw key is stored, but never returned.
    assert fake_settings["qwen_api_key"] == "sk-secret-123456"


def test_each_provider_keeps_its_own_model(fake_settings):
    """У локальной и облачной модели разные имена: выбор не теряется."""

    processor.update_settings(provider="openai", model="ling-3.0-flash-vl")
    processor.update_settings(provider="ollama", model="qwen3-vl:4b-instruct")

    assert processor.model_for_provider("openai") == "ling-3.0-flash-vl"
    assert processor.model_for_provider("ollama") == "qwen3-vl:4b-instruct"

    # Переключение провайдера возвращает модель именно этого провайдера.
    assert processor.resolve_settings()["model"] == "qwen3-vl:4b-instruct"
    processor.update_settings(provider="openai")
    assert processor.resolve_settings()["model"] == "ling-3.0-flash-vl"


def test_model_without_provider_updates_the_current_one(fake_settings):
    processor.update_settings(provider="openai", model="ling-3.0-flash-vl")
    processor.update_settings(model="ling-3.0-flash-vl-v2")

    assert processor.resolve_settings()["model"] == "ling-3.0-flash-vl-v2"


def test_legacy_model_key_belongs_to_the_current_provider(fake_settings):
    """Единственный старый ключ читается как модель текущего провайдера."""

    fake_settings["qwen_provider"] = "openai"
    fake_settings["qwen_model"] = "ling-3.0-flash-vl"

    assert processor.model_for_provider("openai") == "ling-3.0-flash-vl"
    # Локальной Ollama старое облачное имя не навязывается.
    assert processor.model_for_provider("ollama") == processor.QWEN_MODEL


def test_crop_takes_the_centre_of_the_frame(tmp_path):
    """Кроп обязан обрезать кадр, а не менять масштаб целиком."""

    from PIL import Image

    source = tmp_path / "wide.jpg"
    Image.new("RGB", (1000, 500), color=(10, 20, 30)).save(source)

    full = processor.encode_image(str(source))
    cropped = processor.encode_image(
        str(source), crop={"mode": "center", "ratio": 0.5}
    )

    def size(payload: str) -> tuple[int, int]:
        import base64
        import io as _io

        with Image.open(_io.BytesIO(base64.b64decode(payload))) as image:
            return image.size

    assert size(full) == (1000, 500)
    # Центральные 50% по каждой стороне: 500x250, и это по-прежнему < 1280.
    assert size(cropped) == (500, 250)


def test_crop_defaults_to_the_whole_frame(fake_settings):
    """По умолчанию кроп выключен — поведение не меняется."""

    assert processor.crop_settings() == {"mode": "off", "ratio": 0.6}

    fake_settings["qwen_crop"] = "center"
    fake_settings["qwen_crop_ratio"] = 0.9

    assert processor.crop_settings() == {"mode": "center", "ratio": 0.9}

    # Мусор в настройке не ломает распознавание.
    fake_settings["qwen_crop"] = "diagonal"
    fake_settings["qwen_crop_ratio"] = "abc"

    assert processor.crop_settings() == {"mode": "off", "ratio": 0.6}


def test_legacy_model_key_is_migrated_to_the_current_provider(fake_settings):
    """Старый единственный ключ переносится к текущему провайдеру один раз."""

    fake_settings["qwen_provider"] = "ollama"
    fake_settings["qwen_model"] = "qwen3-vl:4b-instruct"

    assert processor.model_for_provider("ollama") == "qwen3-vl:4b-instruct"
    assert fake_settings["qwen_model_ollama"] == "qwen3-vl:4b-instruct"
    assert not fake_settings.get("qwen_model")
    assert processor.model_for_provider("openai") == ""


def test_legacy_key_does_not_stick_to_another_provider(fake_settings):
    """
    Чужое имя не «прилипает» после переключения провайдера.

    В окне у локальной Ollama показывалась облачная модель: старый общий ключ
    читался как модель ЛЮБОГО текущего провайдера.
    """

    fake_settings["qwen_model_openai"] = "ling-3.0-flash-vl"
    fake_settings["qwen_provider"] = "ollama"
    fake_settings["qwen_model"] = "ling-3.0-flash-vl"

    assert processor.model_for_provider("ollama") == processor.QWEN_MODEL
    assert processor.model_for_provider("openai") == "ling-3.0-flash-vl"
    assert not fake_settings.get("qwen_model")


def test_public_settings_lists_the_model_of_each_provider(fake_settings):
    fake_settings["qwen_model_ollama"] = "qwen3-vl:4b-instruct"
    fake_settings["qwen_model_openai"] = "ling-3.0-flash-vl"

    view = processor.public_settings()

    assert view["models"] == {
        "ollama": "qwen3-vl:4b-instruct",
        "openai": "ling-3.0-flash-vl",
    }


def test_update_settings_rejects_unknown_provider(fake_settings):
    with pytest.raises(ValueError):
        processor.update_settings(provider="nope")


def test_update_settings_allows_ollama_without_base_url(fake_settings):
    view = processor.update_settings(provider="ollama")
    assert view["provider"] == "ollama"


def test_ollama_analyze_sends_configured_keep_alive(fake_settings, monkeypatch):
    captured = {}

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            json.dumps(
                {"message": {"content": '{"description": "ok"}'}}
            ).encode("utf-8")
        )

    monkeypatch.setattr(processor.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(processor, "encode_image", lambda path, **kw: "BASE64")

    config = {**processor.resolve_settings(), "keep_alive": "7m"}

    processor._ollama_analyze(config, "/tmp/x.jpg")

    assert captured["url"].endswith("/api/chat")
    assert captured["body"]["keep_alive"] == "7m"
    assert captured["body"]["options"]["num_predict"] == processor.MAX_OUTPUT_TOKENS


def test_cloud_retries_a_rate_limited_provider(monkeypatch):
    """429 — не приговор: ждём и повторяем, а не помечаем фото упавшим."""

    calls = {"n": 0}
    slept: list[float] = []

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1

        if calls["n"] == 1:
            raise urllib.error.HTTPError(
                request.full_url, 429, "Too Many Requests", {}, None
            )

        return _Response(json.dumps({"ok": True}).encode("utf-8"))

    monkeypatch.setattr(processor.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(processor.time, "sleep", lambda value: slept.append(value))

    request = processor.urllib.request.Request("https://example.invalid/v1/x")
    assert processor._post_json(request, 5.0, retries=3) == {"ok": True}
    assert calls["n"] == 2
    assert slept and slept[0] > 0


def test_cloud_gives_up_with_a_readable_message(monkeypatch):
    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 429, "Too Many Requests", {}, None
        )

    monkeypatch.setattr(processor.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(processor.time, "sleep", lambda value: None)

    request = processor.urllib.request.Request("https://example.invalid/v1/x")

    with pytest.raises(processor.ProviderRateLimited) as excinfo:
        processor._post_json(request, 5.0, retries=2)

    assert "429" in str(excinfo.value)


def test_local_provider_does_not_retry(monkeypatch):
    """У локальной Ollama повторов нет: остановленный сервер падает сразу."""

    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(processor.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(processor.time, "sleep", lambda value: None)

    request = processor.urllib.request.Request("http://127.0.0.1:11434/api/chat")

    with pytest.raises(urllib.error.URLError):
        processor._post_json(request, 5.0)

    assert calls["n"] == 1


def test_openai_analyze_builds_request_and_parses(fake_settings, monkeypatch):
    captured = {}

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"brand": "Luvio", "tags": ["a", "b"]}'
                            }
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(processor.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(processor, "encode_image", lambda path, **kw: "BASE64")

    config = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-xyz",
        "keep_alive": "10m",
        "unload_on_idle": True,
        "timeout": 30,
        "ollama_url": "http://127.0.0.1:11434",
    }

    fields, _payload, _elapsed = processor._openai_analyze(config, "/tmp/x.jpg")

    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-xyz"
    assert captured["body"]["model"] == "gpt-4o-mini"
    assert fields["brand"] == "Luvio"
    assert fields["tags"] == ["a", "b"]


def test_unload_is_noop_for_cloud(fake_settings):
    processor.update_settings(provider="openai", base_url="https://x/v1")
    assert processor.unload_model() is False


# ---- analysis input: the local MIDDLE preview beats re-reading the original ----


def test_analysis_input_prefers_the_middle_preview(tmp_path, monkeypatch):
    photo_id = "PH_0123456789abcdef01234567"
    middle = tmp_path / "middle" / f"{photo_id}.jpg"
    middle.parent.mkdir(parents=True)
    middle.write_bytes(b"preview")

    monkeypatch.setattr(processor, "_PREVIEW_ROOT", tmp_path)

    assert (
        processor.analysis_input(photo_id, "/mnt/photos/a.jpg") == str(middle)
    )


def test_analysis_input_falls_back_to_the_original(tmp_path, monkeypatch):
    monkeypatch.setattr(processor, "_PREVIEW_ROOT", tmp_path / "empty")

    assert (
        processor.analysis_input("PH_x", "/mnt/photos/a.jpg") == "/mnt/photos/a.jpg"
    )


def test_analysis_input_without_a_preview_root_uses_the_original(monkeypatch):
    monkeypatch.setattr(processor, "_PREVIEW_ROOT", None)

    assert processor.analysis_input("PH_x", "/mnt/photos/a.jpg") == "/mnt/photos/a.jpg"

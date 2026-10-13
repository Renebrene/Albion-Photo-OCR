"""
Tests for QWEN provider selection and keep-alive (app.qwen.processor).

No network and no PostgreSQL: settings_store and urllib are stubbed.
"""

from __future__ import annotations

import io
import json

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
    monkeypatch.setattr(processor, "encode_image", lambda path: "BASE64")

    config = {**processor.resolve_settings(), "keep_alive": "7m"}

    processor._ollama_analyze(config, "/tmp/x.jpg")

    assert captured["url"].endswith("/api/chat")
    assert captured["body"]["keep_alive"] == "7m"
    assert captured["body"]["options"]["num_predict"] == processor.MAX_OUTPUT_TOKENS


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
    monkeypatch.setattr(processor, "encode_image", lambda path: "BASE64")

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

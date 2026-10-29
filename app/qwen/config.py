"""
Configuration for the QWEN metadata process.

Qwen can run through a local Ollama instance (default) or an OpenAI-compatible
cloud endpoint ("provider"). Providers are chosen at runtime via settings and
are independent from the DINO/HYBRID recognition pipeline.
"""

from __future__ import annotations

import os

# --- Providers -----------------------------------------------------------------
# Local Ollama (default): no data leaves the machine.
PROVIDER_OLLAMA = "ollama"
# OpenAI-compatible HTTP API (cloud): images are uploaded to the endpoint.
PROVIDER_OPENAI = "openai"
PROVIDERS = (PROVIDER_OLLAMA, PROVIDER_OPENAI)

# Default provider; override at runtime with the `qwen_provider` setting.
QWEN_PROVIDER = os.getenv("QWEN_PROVIDER", PROVIDER_OLLAMA).strip().lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

# Base URL for the OpenAI-compatible provider (e.g. https://api.openai.com/v1).
# No default: the operator must supply it explicitly.
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "").strip()

# Vision-capable model. The exact tag depends on the provider; for Ollama it is
# whatever has been pulled locally (qwen3-vl:8b, qwen3-vl:4b-instruct, ...).
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3-vl:8b")

# Seconds to wait for one image analysis.
# Таймаут одного ответа модели. Замеры на корпусе: медиана 2,6 с, p90 3,2 с,
# максимум 57 с — 300 с держали очередь на зависшем запросе пять минут.
# Владелец (29.10.2026): таймаут меньше, чтобы сбойное фото падало быстро и
# следующий запуск его повторил, а не ждал.
QWEN_TIMEOUT = float(os.getenv("QWEN_TIMEOUT", "120"))

# How long Ollama keeps the model resident after a request. A duration string
# ("10m", "1h") keeps it warm between consecutive jobs; "0" unloads right after
# every request (old behaviour). Ignored by the cloud provider.
QWEN_KEEP_ALIVE = os.getenv("QWEN_KEEP_ALIVE", "10m").strip()

# When the job queue drains, the worker explicitly unloads the local model.
QWEN_UNLOAD_ON_IDLE = os.getenv("QWEN_UNLOAD_ON_IDLE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
}

# Fields the model must return (minimal set + tags).
QWEN_FIELDS = (
    "description",
    "address",
    "client",
    "brand",
    "category",
)

"""
Configuration for the QWEN metadata process.

Qwen runs through a local Ollama instance and is independent from the
DINO/HYBRID recognition pipeline.
"""

from __future__ import annotations

import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

# Vision-capable model served by Ollama. Configurable because the exact tag
# depends on what is pulled locally (qwen3-vl:8b, qwen3-vl:4b-instruct, ...).
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3-vl:8b")

# Seconds to wait for one image analysis.
QWEN_TIMEOUT = float(os.getenv("QWEN_TIMEOUT", "300"))

# Fields the model must return (minimal set + tags).
QWEN_FIELDS = (
    "description",
    "address",
    "client",
    "brand",
    "category",
)

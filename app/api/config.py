"""
Lightweight configuration for the read-only web API.

Intentionally avoids importing app.core.config, which pulls in torch.
Only what the API needs is read from the environment.
"""

from __future__ import annotations

import os
from pathlib import Path

# Preview files live outside the database; the path is built from photo_id,
# never taken from a client-supplied path.
PREVIEW_ROOT = Path(
    os.getenv("SCENE_PREVIEW_ROOT", "data/preview")
)

API_HOST = os.getenv("SCENE_API_HOST", "127.0.0.1")
# Default 8010 (not 8000) to avoid clashing with other local services;
# override with SCENE_API_PORT.
API_PORT = int(os.getenv("SCENE_API_PORT", "8010"))

# Comma-separated list of allowed browser origins (dev servers).
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "SCENE_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

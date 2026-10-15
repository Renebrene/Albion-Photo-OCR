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
VIDEO_PREVIEW_ROOT = Path(
    os.getenv("SCENE_VIDEO_PREVIEW_ROOT", str(PREVIEW_ROOT / "videos"))
)

# Fingerprint artifacts (FAISS + metadata) live next to the data directory.
FINGERPRINTS_ROOT = Path(
    os.getenv("SCENE_DATA", "data")
) / "fingerprints"

# Montage the builder writes next to the vectors (app/core/fingerprint.py
# PREVIEW_NAME). Repeated here on purpose: importing the builder would pull
# faiss/opencv into the API process, which this module exists to avoid.
FINGERPRINT_PREVIEW_NAME = "preview.jpg"

# Allowed roots for serving original files. Comma-separated absolute paths
# (e.g. the mounted photo volume). Empty -> originals are refused (fail-closed):
# a registered path outside these roots is never served.
ORIGINALS_ROOTS = [
    Path(root.strip())
    for root in os.getenv("SCENE_ORIGINALS_ROOTS", "").split(",")
    if root.strip()
]

# --- Working (source) folder for INGEST ------------------------------------
# The folder the ingest scans for new photos. It is selected in the UI and
# persisted in app_settings; SCENE_SOURCE_FOLDER is only the fallback default.
SOURCE_FOLDER_KEY = "source_folder"
SOURCE_FOLDER_DEFAULT = os.getenv("SCENE_SOURCE_FOLDER", "")

# Optional allowlist: when non-empty, only folders below these roots can be
# selected, counted or ingested. Empty means "any readable directory", which
# is acceptable on the single-machine deployment (the endpoints still require
# the jobs:write scope); set it on a shared host.
SOURCE_ROOTS = [
    Path(root.strip())
    for root in os.getenv("SCENE_SOURCE_ROOTS", "").split(",")
    if root.strip()
]

# Upper bound for the folder statistics walk, so a huge tree cannot keep a
# request busy forever. Exceeding it reports truncated=True.
SOURCE_SCAN_FILE_LIMIT = int(os.getenv("SCENE_SOURCE_SCAN_LIMIT", "200000"))

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

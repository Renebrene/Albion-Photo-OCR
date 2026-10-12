"""
Technical-section helpers: host monitor, fingerprint inventory, last run.

Read-only and lightweight (no torch, no model loading).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import psutil

from app.api.config import FINGERPRINTS_ROOT
from app.ingest.database import get_connection


def system_info() -> dict:
    """Host CPU / memory / disk / uptime snapshot."""

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.cwd()))

    try:
        load_avg = list(os.getloadavg())
    except (AttributeError, OSError):
        load_avg = None

    return {
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "load_avg": load_avg,
        "memory": {
            "total": memory.total,
            "used": memory.used,
            "percent": memory.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "percent": disk.percent,
        },
        "uptime_sec": max(0.0, time.time() - psutil.boot_time()),
    }


def list_fingerprints() -> list[dict]:
    """Inventory of fingerprint artifacts under the data directory."""

    root = FINGERPRINTS_ROOT

    if not root.is_dir():
        return []

    items: list[dict] = []

    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue

        metadata_file = directory / "metadata.json"

        if not metadata_file.is_file():
            continue

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue

        items.append(
            {
                "id": directory.name,
                "images": metadata.get("images"),
                "dimension": metadata.get("dimension"),
                "version": metadata.get("version"),
                "model": metadata.get("model"),
            }
        )

    return items


def last_run() -> dict:
    """Summary of the most recent processing activity."""

    result: dict = {"dino_batch": None, "hybrid_run": None, "jobs": {}}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT batch_id, run_type, status, total_count,
                       completed_count, failed_count, created_at, finished_at
                FROM public.dino_batches
                ORDER BY batch_id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

            if row is not None:
                result["dino_batch"] = {
                    "batch_id": int(row[0]),
                    "run_type": row[1],
                    "status": row[2],
                    "total_count": int(row[3]),
                    "completed_count": int(row[4]),
                    "failed_count": int(row[5]),
                    "created_at": row[6],
                    "finished_at": row[7],
                }

            cur.execute(
                """
                SELECT hybrid_run_id, dino_batch_id, status, total_count,
                       completed_count, failed_count, created_at, finished_at
                FROM public.hybrid_runs
                ORDER BY hybrid_run_id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

            if row is not None:
                result["hybrid_run"] = {
                    "hybrid_run_id": int(row[0]),
                    "dino_batch_id": int(row[1]),
                    "status": row[2],
                    "total_count": int(row[3]),
                    "completed_count": int(row[4]),
                    "failed_count": int(row[5]),
                    "created_at": row[6],
                    "finished_at": row[7],
                }

            cur.execute(
                """
                SELECT status, count(*)
                FROM public.job_queue
                GROUP BY status
                """
            )
            result["jobs"] = {
                row[0]: int(row[1]) for row in cur.fetchall()
            }

    return result

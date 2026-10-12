```python
# app/pipeline/supervisor.py
import os
import time
import signal
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue, Empty

# Константы
MODE_MANUAL = "manual"
MODE_AUTOMATIC = "automatic"
MODE_WATCHER = "watcher"
PIPELINE_CONTROL_ID = 1
WORKER_TIMEOUT = 300  # 5 минут
MAX_RETRIES = 3

# Настройки
DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_state():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    mode,
                    auto_enabled,
                    auto_time,
                    watcher_enabled,
                    watcher_path,
                    running,
                    stop_requested
                FROM pipeline_control
                WHERE id = %s
                """,
                (PIPELINE_CONTROL_ID,)
            )
            row = cur.fetchone()
    
    if row is None:
        return {
            "mode": MODE_MANUAL,
            "auto_enabled": False,
            "auto_time": None,
            "watcher_enabled": False,
            "watcher_path": "",
            "running": False,
            "stop_requested": False
        }
    
    return {
        "mode": row["mode"],
        "auto_enabled": bool(row["auto_enabled"]),
        "auto_time": row["auto_time"],
        "watcher_enabled": bool(row["watcher_enabled"]),
        "watcher_path": row["watcher_path"],
        "running": bool(row["running"]),
        "stop_requested": bool(row["stop_requested"])
    }

def set_state(state):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = %s,
                    auto_enabled = %s,
                    auto_time = %s,
                    watcher_enabled = %s,
                    watcher_path = %s,
                    running = %s,
                    stop_requested = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    state["mode"],
                    state["auto_enabled"],
                    state["auto_time"],
                    state["watcher_enabled"],
                    state["watcher_path"],
                    state["running"],
                    state["stop
```
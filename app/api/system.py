"""
Technical-section helpers: host monitor, fingerprint inventory, last run.

Read-only and lightweight (no torch, no model loading).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections import deque
from pathlib import Path

import psutil

from app.api.config import FINGERPRINTS_ROOT
from app.api import security
from app.ingest.database import get_connection

ALERT_CPU = float(os.getenv("SCENE_ALERT_CPU", "90"))
ALERT_CPU_WINDOW_SEC = float(os.getenv("SCENE_ALERT_CPU_WINDOW_SEC", "300"))
ALERT_RAM = float(os.getenv("SCENE_ALERT_RAM", "75"))
ALERT_DISK = float(os.getenv("SCENE_ALERT_DISK", "75"))
ALERT_TEMP = float(os.getenv("SCENE_ALERT_TEMP", "80"))
ALERT_GPU = float(os.getenv("SCENE_ALERT_GPU", "90"))
ALERT_NETWORK_MBPS = float(os.getenv("SCENE_ALERT_NETWORK_MBPS", "1"))
ALERT_NETWORK_LOW_SEC = float(os.getenv("SCENE_ALERT_NETWORK_LOW_SEC", "120"))

_cpu_samples: deque[tuple[float, float]] = deque(maxlen=200)
_last_net: tuple[float, int, int, int, int] | None = None
_low_network_since: float | None = None
_gpu_cache: tuple[float, list[dict]] = (0.0, [])


def _temperatures() -> list[dict]:
    """Best-effort CPU/board temperatures (empty when unsupported)."""

    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False) or {}
    except (AttributeError, OSError):
        return []

    readings = []

    for name, entries in sensors.items():
        for entry in entries:
            if entry.current is None:
                continue

            readings.append(
                {
                    "sensor": name,
                    "label": entry.label or name,
                    "current": round(float(entry.current), 1),
                    "high": (
                        round(float(entry.high), 1)
                        if entry.high is not None
                        else None
                    ),
                }
            )

    return readings


def _gpu_info() -> list[dict]:
    """NVIDIA GPU metrics via nvidia-smi (empty when unavailable)."""

    global _gpu_cache

    now = time.time()

    if now - _gpu_cache[0] < 5:
        return _gpu_cache[1]

    if shutil.which("nvidia-smi") is None:
        _gpu_cache = (now, [])
        return []

    try:
        output = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        _gpu_cache = (now, [])
        return []

    gpus = []
    for line in output.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]

        if len(parts) < 6:
            continue

        try:
            used = int(parts[3])
            total = int(parts[4])
            gpus.append(
                {
                    "index": int(parts[0]),
                    "name": parts[1],
                    "utilization": float(parts[2]),
                    "memory_used": used,
                    "memory_total": total,
                    "memory_percent": round(used / total * 100, 1) if total else 0.0,
                    "temperature": float(parts[5]),
                }
            )
        except (TypeError, ValueError, ZeroDivisionError):
            continue

    _gpu_cache = (now, gpus)
    return gpus


def _network_rate() -> tuple[float | None, dict]:
    """MB/s over the interval since the previous system_info() call."""

    global _last_net

    try:
        net = psutil.net_io_counters()
    except (AttributeError, OSError):
        return (None, {})

    now = time.time()
    rate = None

    if _last_net is not None:
        previous, sent0, recv0, err0, drop0 = _last_net
        elapsed = max(0.001, now - previous)
        sent = max(0, net.bytes_sent - sent0)
        recv = max(0, net.bytes_recv - recv0)
        rate = round((sent + recv) / elapsed / 1024 / 1024, 3)
        errors = max(0, net.errin + net.errout - err0)
        drops = max(0, net.dropin + net.dropout - drop0)
    else:
        errors = 0
        drops = 0

    _last_net = (
        now,
        net.bytes_sent,
        net.bytes_recv,
        net.errin + net.errout,
        net.dropin + net.dropout,
    )

    return (
        rate,
        {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "rate_mbps": rate,
            "errors": errors,
            "drops": drops,
        },
    )


def _active_job_types() -> dict[str, int]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT job_type, count(*) FROM public.job_queue "
                    "WHERE status IN ('PENDING','RUNNING') GROUP BY job_type"
                )
                return {row[0]: int(row[1]) for row in cur.fetchall()}
    except Exception:  # noqa: BLE001 - alerts must not break the System tab
        return {}


def _alert(code: str, severity: str, message: str, **extra) -> dict:
    return {"code": code, "severity": severity, "message": message, **extra}


def build_alerts(
    *,
    cpu_percent: float,
    memory_percent: float,
    disk_percent: float,
    temperatures: list[dict],
    gpus: list[dict],
    network: dict,
    active_jobs: dict[str, int],
    security_snapshot: dict,
) -> list[dict]:
    """Threshold alerts for the System tab (no persistence, no side effects)."""

    global _low_network_since

    now = time.time()
    _cpu_samples.append((now, float(cpu_percent)))
    while _cpu_samples and _cpu_samples[0][0] < now - ALERT_CPU_WINDOW_SEC:
        _cpu_samples.popleft()

    alerts: list[dict] = []

    if len(_cpu_samples) >= 5:
        hot = sum(1 for _, value in _cpu_samples if value >= ALERT_CPU)
        if hot / len(_cpu_samples) >= 0.8:
            alerts.append(
                _alert(
                    "cpu_high",
                    "warning",
                    f"CPU ≥ {ALERT_CPU:.0f}% большую часть последних "
                    f"{int(ALERT_CPU_WINDOW_SEC // 60)} мин",
                    value=round(cpu_percent, 1),
                    threshold=ALERT_CPU,
                )
            )

    if memory_percent >= ALERT_RAM:
        alerts.append(
            _alert(
                "memory_high", "warning",
                f"Занято {memory_percent:.0f}% памяти (порог {ALERT_RAM:.0f}%)",
                value=round(memory_percent, 1), threshold=ALERT_RAM,
            )
        )

    if disk_percent >= ALERT_DISK:
        alerts.append(
            _alert(
                "disk_high", "warning",
                f"Занято {disk_percent:.0f}% диска (порог {ALERT_DISK:.0f}%)",
                value=round(disk_percent, 1), threshold=ALERT_DISK,
            )
        )

    for temperature in temperatures:
        if temperature.get("current") is not None and temperature["current"] >= ALERT_TEMP:
            alerts.append(
                _alert(
                    "temperature_high", "warning",
                    f"{temperature.get('label') or temperature.get('sensor')}: "
                    f"{temperature['current']}°C",
                    value=temperature["current"], threshold=ALERT_TEMP,
                )
            )

    for gpu in gpus:
        if gpu["utilization"] >= ALERT_GPU or gpu["memory_percent"] >= ALERT_GPU:
            alerts.append(
                _alert(
                    "gpu_high", "warning",
                    f"GPU {gpu['index']}: загрузка {gpu['utilization']:.0f}%, "
                    f"память {gpu['memory_percent']:.0f}%",
                    value=max(gpu["utilization"], gpu["memory_percent"]),
                    threshold=ALERT_GPU,
                )
            )

    rate = network.get("rate_mbps")
    file_jobs = sum(
        count for job_type, count in active_jobs.items()
        if job_type in {"INGEST_DIR", "PHOTO_PREVIEW", "BILLBOARD_DETECT", "QWEN_PHOTO"}
    )

    if rate is not None and file_jobs and rate < ALERT_NETWORK_MBPS:
        if _low_network_since is None:
            _low_network_since = now
        elif now - _low_network_since >= ALERT_NETWORK_LOW_SEC:
            alerts.append(
                _alert(
                    "network_low", "warning",
                    f"Скорость сети {rate:.2f} МБ/с при активных файловых jobs",
                    value=rate, threshold=ALERT_NETWORK_MBPS,
                )
            )
    else:
        _low_network_since = None

    if network.get("errors") or network.get("drops"):
        alerts.append(
            _alert(
                "network_errors", "warning",
                f"Сетевые ошибки/потери: {network.get('errors', 0)}/"
                f"{network.get('drops', 0)} за интервал",
                value=network.get("errors", 0) + network.get("drops", 0),
            )
        )

    failures = int(security_snapshot.get("login_failures", 0))
    limit = int(security_snapshot.get("login_failure_limit", 10))
    if failures >= limit:
        alerts.append(
            _alert(
                "login_failures", "critical",
                f"{failures} неудачных входов за "
                f"{security_snapshot.get('login_failure_window_sec', 600) // 60} мин",
                value=failures, threshold=limit,
            )
        )

    for ip, count in (security_snapshot.get("login_failures_by_ip") or {}).items():
        if count >= limit:
            alerts.append(
                _alert(
                    "login_failures_ip", "critical",
                    f"{count} неудачных входов с {ip}",
                    value=count, threshold=limit, ip=ip,
                )
            )

    request_limit = int(security_snapshot.get("request_limit", 300))
    for ip, count in (security_snapshot.get("requests_by_ip") or {}).items():
        if count >= request_limit:
            alerts.append(
                _alert(
                    "requests_ip", "warning",
                    f"{count} запросов/мин с {ip}",
                    value=count, threshold=request_limit, ip=ip,
                )
            )

    return alerts


def system_info() -> dict:
    """Host CPU / memory / disk / network / temperature / uptime snapshot."""

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.cwd()))

    try:
        load_avg = list(os.getloadavg())
    except (AttributeError, OSError):
        load_avg = None

    _, network = _network_rate()
    temperatures = _temperatures()
    gpus = _gpu_info()
    cpu_percent = psutil.cpu_percent(interval=None)
    active_jobs = _active_job_types()
    security_snapshot = security.snapshot()

    return {
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": cpu_percent,
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
        "network": network,
        "gpus": gpus,
        "temperatures": temperatures,
        "uptime_sec": max(0.0, time.time() - psutil.boot_time()),
        "active_jobs": active_jobs,
        "security": security_snapshot,
        "alerts": build_alerts(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            temperatures=temperatures,
            gpus=gpus,
            network=network,
            active_jobs=active_jobs,
            security_snapshot=security_snapshot,
        ),
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

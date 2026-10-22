"""Threshold alerts for the System tab (pure evaluation)."""

from __future__ import annotations

from app.api import security, system


def _alerts(**overrides):
    values = {
        "cpu_percent": 10.0,
        "memory_percent": 30.0,
        "disk_percent": 40.0,
        "temperatures": [],
        "gpus": [],
        "network": {"rate_mbps": 50.0, "errors": 0, "drops": 0},
        "active_jobs": {},
        "security_snapshot": {
            "login_failures": 0,
            "login_failures_by_ip": {},
            "login_failure_limit": 10,
            "login_failure_window_sec": 600,
            "requests_by_ip": {},
            "request_limit": 300,
        },
    }
    values.update(overrides)
    return system.build_alerts(**values)


def test_memory_disk_temperature_and_gpu_alerts():
    codes = {
        alert["code"]
        for alert in _alerts(
            memory_percent=80.0,
            disk_percent=90.0,
            temperatures=[{"sensor": "k10temp", "label": "Tctl", "current": 85.0}],
            gpus=[{
                "index": 0, "name": "GPU", "utilization": 95.0,
                "memory_percent": 50.0, "temperature": 60.0,
            }],
        )
    }

    assert {"memory_high", "disk_high", "temperature_high", "gpu_high"} <= codes


def test_login_failure_alert():
    snapshot = _alerts(
        security_snapshot={
            "login_failures": 12,
            "login_failures_by_ip": {"10.0.0.5": 11},
            "login_failure_limit": 10,
            "login_failure_window_sec": 600,
            "requests_by_ip": {},
            "request_limit": 300,
        },
    )
    codes = {alert["code"] for alert in snapshot}

    assert "login_failures" in codes
    assert "login_failures_ip" in codes


def test_cpu_alert_needs_a_sustained_window():
    system._cpu_samples.clear()

    for _ in range(10):
        alerts = _alerts(cpu_percent=95.0)

    assert any(alert["code"] == "cpu_high" for alert in alerts)


def test_security_snapshot_counts_failures():
    security.record_login_failure("127.0.0.1", "tester")
    snapshot = security.snapshot()

    assert snapshot["login_failures"] >= 1
    assert snapshot["login_failures_by_ip"]["127.0.0.1"] >= 1

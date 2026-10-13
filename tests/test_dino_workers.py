"""
DINO worker-count resolution (SCENE_DINO_WORKERS).

Pure logic only: no model loading, no PostgreSQL.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.config import settings
from app.dino import runner


def test_explicit_workers_win():
    assert runner.resolve_workers(3) == 3


def test_settings_workers_used(monkeypatch):
    monkeypatch.setattr(runner, "settings", replace(settings, dino_workers=4))
    assert runner.resolve_workers() == 4


def test_zero_means_automatic_half_cpu(monkeypatch):
    monkeypatch.setattr(runner, "settings", replace(settings, dino_workers=0))
    assert runner.resolve_workers() == runner.default_workers()


def test_invalid_workers_rejected():
    with pytest.raises(ValueError):
        runner.resolve_workers(-1)


def test_default_workers_at_least_one():
    assert runner.default_workers() >= 1


def test_explicit_batch_wins():
    assert runner.resolve_batch(8) == 8


def test_settings_batch_used(monkeypatch):
    monkeypatch.setattr(runner, "settings", replace(settings, dino_batch=4))
    assert runner.resolve_batch() == 4


def test_invalid_batch_rejected():
    with pytest.raises(ValueError):
        runner.resolve_batch(0)

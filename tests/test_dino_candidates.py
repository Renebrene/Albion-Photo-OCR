"""DINO keeps enough candidates for HYBRID low-margin reranking."""

from __future__ import annotations

from types import SimpleNamespace

from app.dino import runner as dino_runner
from app.dino.database import MAX_CANDIDATES


def test_rank_keeps_top_fifteen(monkeypatch):
    fingerprints = [
        (f"f{index}", SimpleNamespace(index=index))
        for index in range(20)
    ]
    runner = object.__new__(dino_runner.DinoRunner)
    runner.fingerprints = fingerprints

    def fake_compare_loaded(**kwargs):
        index = int(kwargs["data"].index)
        return {
            "score": 1.0 - index * 0.001,
            "global": 0.9,
            "environment": 0.9,
            "color": 0.9,
            "spatial": 0.9,
            "best_image": None,
            "best_image_score": 0.9,
        }

    monkeypatch.setattr(dino_runner, "compare_loaded", fake_compare_loaded)

    result = runner._rank(None, None, None, None, "PH_test")

    assert MAX_CANDIDATES == 15
    assert len(result["candidates"]) == 15
    assert [candidate["id"] for candidate in result["candidates"]] == [
        f"f{index}" for index in range(15)
    ]

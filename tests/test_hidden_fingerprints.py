"""Hidden (archived) fingerprints must not take part in DINO or HYBRID."""

from __future__ import annotations

import numpy as np

from app.dino import runner
from app.hybrid.database import filter_active_candidates


class _FakeManager:
    def __init__(self):
        self.loaded: list[str] = []

    def list_fingerprints(self):
        return [{"id": "visible_v33"}, {"id": "hidden_v33"}]

    def load(self, fingerprint_id):
        self.loaded.append(fingerprint_id)
        return {
            "metadata": {"version": "3.3"},
            "embeddings": np.zeros((2, 768), dtype=np.float32),
        }


def test_dino_skips_hidden_fingerprints(monkeypatch):
    import app.api.fingerprints as registry

    manager = _FakeManager()
    instance = object.__new__(runner.DinoRunner)
    instance.manager = manager

    monkeypatch.setattr(
        registry, "active_fingerprint_ids", lambda: {"visible_v33"}
    )

    loaded = instance._load_fingerprints()

    assert [fingerprint_id for fingerprint_id, _data in loaded] == [
        "visible_v33"
    ]
    # A hidden fingerprint is not even read from disk.
    assert manager.loaded == ["visible_v33"]


def test_dino_keeps_the_old_behaviour_without_a_registry(monkeypatch):
    import app.api.fingerprints as registry

    instance = object.__new__(runner.DinoRunner)
    instance.manager = _FakeManager()

    monkeypatch.setattr(registry, "active_fingerprint_ids", lambda: None)

    loaded = instance._load_fingerprints()

    assert [fingerprint_id for fingerprint_id, _data in loaded] == [
        "visible_v33",
        "hidden_v33",
    ]


def test_hybrid_drops_hidden_candidates_and_their_best():
    candidates = [
        {"id": "hidden_v33", "score": 0.9},
        {"id": "visible_v33", "score": 0.8},
    ]

    kept, best = filter_active_candidates(
        candidates, "hidden_v33", {"visible_v33"}
    )

    assert kept == [{"id": "visible_v33", "score": 0.8}]
    assert best is None


def test_hybrid_keeps_everything_when_the_registry_is_unavailable():
    candidates = [{"id": "any_v33", "score": 0.9}]

    kept, best = filter_active_candidates(candidates, "any_v33", None)

    assert kept == candidates
    assert best == "any_v33"

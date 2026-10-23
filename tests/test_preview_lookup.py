"""
DINO chooses the MIDDLE preview when it exists and the original otherwise.

Mock-free and DB-free: only the filesystem layout and the fallback rule.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.dino.database import DinoWorkItem
from app.dino.runner import DinoRunner
from app.preview.generator import build_preview_paths
from app.preview.lookup import dino_input_path, middle_preview_path


def _paths(root: Path):
    return build_preview_paths(
        preview_root=root,
        photo_id="PH_" + "a" * 24,
        image_format="webp",
    )


def _write(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"preview")
    return path


def test_middle_preview_in_current_format(tmp_path):
    paths = _paths(tmp_path)
    _write(paths.middle)

    assert middle_preview_path("PH_" + "a" * 24, preview_root=tmp_path) == paths.middle


def test_middle_preview_falls_back_to_legacy_jpeg(tmp_path):
    paths = _paths(tmp_path)
    legacy = paths.middle.with_suffix(".jpg")
    _write(legacy)

    assert middle_preview_path("PH_" + "a" * 24, preview_root=tmp_path) == legacy


def test_missing_preview_returns_none(tmp_path):
    assert middle_preview_path("PH_" + "a" * 24, preview_root=tmp_path) is None
    assert middle_preview_path("", preview_root=tmp_path) is None


def test_dino_reads_preview_and_falls_back_to_source(tmp_path):
    source = _write(tmp_path / "original.jpg")
    paths = _paths(tmp_path)
    _write(paths.middle)

    assert (
        dino_input_path("PH_" + "a" * 24, source, preview_root=tmp_path)
        == paths.middle
    )

    # No preview: the original is used, the batch never waits.
    assert dino_input_path("PH_" + "b" * 24, source, preview_root=tmp_path) == source

    # An explicit opt-out ignores previews entirely.
    assert (
        dino_input_path(
            "PH_" + "a" * 24,
            source,
            use_preview=False,
            preview_root=tmp_path,
        )
        == source
    )


def test_runner_resolves_input_with_setting(tmp_path, monkeypatch):
    source = _write(tmp_path / "original.jpg")
    paths = _paths(tmp_path)
    _write(paths.middle)
    item = DinoWorkItem(
        run_id=1,
        photo_id="PH_" + "a" * 24,
        source_path=str(source),
        run_type="NORMAL",
    )

    # Point the lookup at the temporary root instead of the data directory.
    import app.preview.lookup as lookup

    monkeypatch.setattr(
        lookup,
        "middle_preview_path",
        lambda photo_id, preview_root=None: paths.middle,
    )

    enabled = SimpleNamespace(cpu_settings=SimpleNamespace(dino_use_preview=True))
    disabled = SimpleNamespace(cpu_settings=SimpleNamespace(dino_use_preview=False))

    assert DinoRunner._input_path(enabled, item) == paths.middle
    assert DinoRunner._input_path(disabled, item) == source

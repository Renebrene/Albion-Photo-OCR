from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from app.billboard import database as billboard_db
from app.billboard import pipeline
from app.billboard.detector import (
    dedup,
    iou,
    pad_bbox,
    pick_largest,
    select_billboards,
)
from app.jobs.database import JOB_TYPES


def _region(x, y, w, h, score):
    return {"bbox_x": x, "bbox_y": y, "bbox_w": w, "bbox_h": h,
            "score": score, "label": "billboard"}


def test_job_types_include_background_branch():
    assert "BILLBOARD_DETECT" in JOB_TYPES
    # Description recognition now reuses QWEN_PHOTO on the crop; the separate
    # crop job type is gone.
    assert "QWEN_CROP" not in JOB_TYPES


def test_iou_and_dedup_keep_best_of_duplicates():
    a = _region(10, 10, 100, 50, 0.9)
    b = _region(12, 11, 100, 50, 0.7)   # same target, slightly shifted
    c = _region(300, 10, 100, 50, 0.8)  # different target

    assert iou(a, b) > 0.6
    assert iou(a, c) == 0.0

    kept = dedup([b, c, a])
    assert kept == [a, c]


def test_pick_largest_ignores_score():
    small = _region(10, 10, 40, 30, 0.95)
    large = _region(100, 100, 300, 200, 0.41)

    assert pick_largest([small, large]) is large
    assert pick_largest([]) is None


def test_select_billboards_keeps_two_comparable_boxes():
    first = _region(10, 10, 300, 200, 0.9)
    second = _region(400, 10, 280, 200, 0.8)
    small = _region(800, 10, 60, 40, 0.7)  # background sign

    selected = select_billboards([small, second, first])

    assert selected == [first, second]


def test_select_billboards_ignores_small_second_box():
    first = _region(10, 10, 300, 200, 0.9)
    second = _region(400, 10, 120, 80, 0.8)  # 0.16 of the largest area

    assert select_billboards([second, first]) == [first]


def test_select_billboards_respects_limit_and_dedup():
    first = _region(10, 10, 300, 200, 0.9)
    duplicate = _region(11, 11, 300, 200, 0.95)
    second = _region(400, 10, 280, 200, 0.8)
    third = _region(800, 10, 260, 180, 0.7)

    selected = select_billboards(
        [duplicate, first, second, third],
        max_regions=2,
    )

    assert selected == [duplicate, second]


def test_pad_bbox_expands_on_both_sides():
    padded = pad_bbox(
        _region(100, 100, 100, 50, 0.8),
        ratio=0.1,
        image_width=1000,
        image_height=500,
    )

    assert (padded["bbox_x"], padded["bbox_y"]) == (90, 95)
    assert (padded["bbox_w"], padded["bbox_h"]) == (120, 60)


def test_pad_bbox_clamps_at_edges():
    padded = pad_bbox(
        _region(0, 0, 100, 50, 0.8),
        ratio=0.1,
        image_width=1000,
        image_height=500,
    )

    assert padded["bbox_x"] == 0
    assert padded["bbox_y"] == 0
    assert (padded["bbox_w"], padded["bbox_h"]) == (110, 55)


def test_write_crop_cuts_from_source_and_publishes_atomically(tmp_path):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 300), (10, 20, 30)).save(source)
    output = tmp_path / "crops" / "PH_1" / "crop_01.jpg"

    width, height = pipeline.write_crop(
        source,
        _region(100, 50, 200, 100, 0.8),
        output,
    )

    assert (width, height) == (200, 100)
    assert output.is_file()
    with Image.open(output) as image:
        assert image.size == (200, 100)
    assert not list(output.parent.glob("*.tmp-*"))


def test_write_crop_clamps_to_image_bounds(tmp_path):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 80), (1, 2, 3)).save(source)
    output = tmp_path / "crop.jpg"

    width, height = pipeline.write_crop(
        source,
        _region(80, 60, 200, 200, 0.5),
        output,
    )

    assert (width, height) == (20, 20)


def _settings():
    return {
        "enabled": True,
        "score": 0.4,
        "padding": 0.0,
        "max_side": 1920,
        "classes": ("billboard",),
        "model": "unused.pt",
        "detector": "test-detector",
        "second_ratio": 0.35,
        "max_regions": 2,
    }


def test_run_detect_writes_region(monkeypatch, tmp_path):
    photo_id = "PH_" + "12" * 12
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 300), (10, 20, 30)).save(source)

    monkeypatch.setattr(
        pipeline, "get_registered_photo",
        lambda pid: SimpleNamespace(source_path=str(source)),
    )
    monkeypatch.setattr(pipeline, "resolve_settings", _settings)
    monkeypatch.setattr(pipeline, "CROPS_ROOT", tmp_path / "crops")
    monkeypatch.setattr(
        pipeline, "detect_billboards",
        lambda path, config=None: [_region(100, 50, 200, 100, 0.8)],
    )

    saved = []

    def fake_replace(pid, rows):
        saved.append((pid, rows))
        return [7 + index for index in range(len(rows))]

    monkeypatch.setattr(billboard_db, "replace_regions", fake_replace)

    result = pipeline.run_detect(photo_id)

    assert result == {"photo_id": photo_id, "detected": True, "regions": 1,
                      "region_ids": [7], "score": 0.8}

    pid, rows = saved[0]
    assert pid == photo_id
    assert rows[0]["bbox_x"] == 100
    assert rows[0]["detector"] == "test-detector"
    assert Path(rows[0]["crop_path"]).is_file()
    assert (rows[0]["crop_width"], rows[0]["crop_height"]) == (200, 100)


def test_run_detect_writes_two_crops_for_two_billboards(monkeypatch, tmp_path):
    photo_id = "PH_" + "1a" * 12
    source = tmp_path / "source.jpg"
    Image.new("RGB", (800, 300), (10, 20, 30)).save(source)

    monkeypatch.setattr(
        pipeline, "get_registered_photo",
        lambda pid: SimpleNamespace(source_path=str(source)),
    )
    monkeypatch.setattr(pipeline, "resolve_settings", _settings)
    monkeypatch.setattr(pipeline, "CROPS_ROOT", tmp_path / "crops")
    monkeypatch.setattr(
        pipeline, "detect_billboards",
        lambda path, config=None: [
            _region(10, 50, 300, 200, 0.9),
            _region(400, 50, 280, 200, 0.8),
        ],
    )

    saved = []
    monkeypatch.setattr(
        billboard_db, "replace_regions",
        lambda pid, rows: saved.append((pid, rows)) or [7 + index for index in range(len(rows))],
    )

    result = pipeline.run_detect(photo_id)

    assert result["regions"] == 2
    assert len(saved[0][1]) == 2
    assert [row["crop_index"] for row in saved[0][1]] == [0, 1]
    directory = tmp_path / "crops" / photo_id
    assert (directory / "crop_01.jpg").is_file()
    assert (directory / "crop_02.jpg").is_file()
    assert (directory / pipeline.CROPS_MARKER).is_file()


def test_run_detect_clears_regions_when_nothing_found(monkeypatch, tmp_path):
    photo_id = "PH_" + "13" * 12
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 80), (0, 0, 0)).save(source)

    monkeypatch.setattr(
        pipeline, "get_registered_photo",
        lambda pid: SimpleNamespace(source_path=str(source)),
    )
    monkeypatch.setattr(pipeline, "resolve_settings", _settings)
    monkeypatch.setattr(pipeline, "detect_billboards", lambda path, config=None: [])

    calls = []
    monkeypatch.setattr(
        billboard_db, "replace_regions",
        lambda pid, rows: calls.append((pid, rows)) or [],
    )

    result = pipeline.run_detect(photo_id)

    assert result == {"photo_id": photo_id, "detected": False, "regions": 0,
                      "region_ids": [], "score": None}
    assert calls == [(photo_id, [])]


def test_ensure_crop_returns_existing_crop(monkeypatch, tmp_path):
    photo_id = "PH_" + "14" * 12
    monkeypatch.setattr(pipeline, "CROPS_ROOT", tmp_path)
    crop = tmp_path / photo_id / "crop_01.jpg"
    crop.parent.mkdir(parents=True)
    Image.new("RGB", (320, 180), (5, 6, 7)).save(crop)
    (crop.parent / pipeline.CROPS_MARKER).write_text('{"version": 2, "count": 1}')

    monkeypatch.setattr(
        billboard_db, "get_billboard_region",
        lambda pid: {"crop_path": str(crop)},
    )
    monkeypatch.setattr(
        pipeline, "_detect_and_store",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("must not detect")),
    )

    assert pipeline.ensure_crop(photo_id) == str(crop)


def test_ensure_crops_returns_both_cached_crops(monkeypatch, tmp_path):
    photo_id = "PH_" + "18" * 12
    monkeypatch.setattr(pipeline, "CROPS_ROOT", tmp_path)
    directory = tmp_path / photo_id
    directory.mkdir()
    first = directory / "crop_01.jpg"
    second = directory / "crop_02.jpg"
    Image.new("RGB", (320, 180), (5, 6, 7)).save(first)
    Image.new("RGB", (320, 180), (7, 6, 5)).save(second)
    (directory / pipeline.CROPS_MARKER).write_text('{"version": 2, "count": 2}')

    monkeypatch.setattr(
        billboard_db, "get_billboard_region",
        lambda pid: {"crop_path": str(first)},
    )
    monkeypatch.setattr(
        pipeline, "_detect_and_store",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("must not detect")),
    )

    assert pipeline.ensure_crops(photo_id) == [str(first), str(second)]


def test_ensure_crops_redetects_old_crop_without_marker(monkeypatch, tmp_path):
    """A crop from an older detector has no marker: re-detect once."""

    photo_id = "PH_" + "19" * 12
    monkeypatch.setattr(pipeline, "CROPS_ROOT", tmp_path)
    directory = tmp_path / photo_id
    directory.mkdir()
    old_crop = directory / "crop_01.jpg"
    Image.new("RGB", (320, 180), (5, 6, 7)).save(old_crop)

    monkeypatch.setattr(
        billboard_db, "get_billboard_region",
        lambda pid: {"crop_path": str(old_crop)},
    )
    monkeypatch.setattr(pipeline, "resolve_settings", _settings)
    monkeypatch.setattr(
        pipeline, "_detect_and_store",
        lambda pid, cfg: {"crops": ["/tmp/new_01.jpg", "/tmp/new_02.jpg"]},
    )

    assert pipeline.ensure_crops(photo_id) == ["/tmp/new_01.jpg", "/tmp/new_02.jpg"]


def test_ensure_crop_detects_on_demand(monkeypatch, tmp_path):
    crop = tmp_path / "crop_01.jpg"
    Image.new("RGB", (320, 180), (5, 6, 7)).save(crop)

    monkeypatch.setattr(billboard_db, "get_billboard_region", lambda pid: None)
    monkeypatch.setattr(pipeline, "resolve_settings", _settings)
    monkeypatch.setattr(
        pipeline, "_detect_and_store",
        lambda pid, cfg: {"detected": True, "regions": 1,
                          "region_ids": [7], "crop_path": str(crop),
                          "crops": [str(crop)]},
    )

    assert pipeline.ensure_crop("PH_" + "15" * 12) == str(crop)


def test_ensure_crop_degrades_to_full_frame(monkeypatch):
    monkeypatch.setattr(billboard_db, "get_billboard_region", lambda pid: None)
    monkeypatch.setattr(pipeline, "resolve_settings", _settings)
    monkeypatch.setattr(
        pipeline, "_detect_and_store",
        lambda pid, cfg: (_ for _ in ()).throw(RuntimeError("detector missing")),
    )

    assert pipeline.ensure_crop("PH_" + "16" * 12) is None


def test_ensure_crop_disabled_ignores_cached_crop(monkeypatch, tmp_path):
    crop = tmp_path / "cached_crop.jpg"
    Image.new("RGB", (320, 180), (5, 6, 7)).save(crop)
    monkeypatch.setattr(
        billboard_db, "get_billboard_region",
        lambda pid: {"crop_path": str(crop)},
    )
    monkeypatch.setattr(
        pipeline, "resolve_settings",
        lambda: {**_settings(), "enabled": False},
    )

    assert pipeline.ensure_crop("PH_" + "17" * 12) is None


def test_discard_crop_removes_file_and_empty_directory(monkeypatch, tmp_path):
    root = tmp_path / "crops"
    monkeypatch.setattr(pipeline, "CROPS_ROOT", root)

    crop = root / "PH_test" / "crop_01.jpg"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(b"jpeg")

    assert pipeline.discard_crop(crop) is True
    assert not crop.exists()
    assert not crop.parent.exists()


def test_discard_crops_removes_marker_with_last_crop(monkeypatch, tmp_path):
    root = tmp_path / "crops"
    monkeypatch.setattr(pipeline, "CROPS_ROOT", root)

    directory = root / "PH_test"
    directory.mkdir(parents=True)
    first = directory / "crop_01.jpg"
    second = directory / "crop_02.jpg"
    first.write_bytes(b"jpeg")
    second.write_bytes(b"jpeg")
    marker = directory / pipeline.CROPS_MARKER
    marker.write_text('{"version": 2, "count": 2}')

    pipeline.discard_crops([str(first)])

    assert not first.exists()
    assert second.exists()
    assert marker.exists()  # the set is not fully cleaned yet

    pipeline.discard_crops([str(second)])

    assert not second.exists()
    assert not marker.exists()
    assert not directory.exists()


def test_discard_crop_refuses_paths_outside_the_root(monkeypatch, tmp_path):
    root = tmp_path / "crops"
    root.mkdir()
    monkeypatch.setattr(pipeline, "CROPS_ROOT", root)

    outside = tmp_path / "secret.jpg"
    outside.write_bytes(b"data")

    assert pipeline.discard_crop(outside) is False
    assert outside.exists()

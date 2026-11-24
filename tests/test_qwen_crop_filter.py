"""
Фильтр качества кропа: «мусорные» кропы читаются последними.

Правило не меняет решение по фото — только порядок чтения: если нормальный
кроп дал описание, отложенные не читаются. Ошибочный отказ фильтра стоит
одного чтения, но реклама не теряется.
"""

from __future__ import annotations

from app.qwen import crop_quality, processor


def test_order_crops_splits_by_threshold(monkeypatch):
    monkeypatch.setattr(crop_quality, "score", lambda paths: [0.5, -0.5, 0.1])

    immediate, deferred = crop_quality.order_crops(["a.jpg", "b.jpg", "c.jpg"], 0.0)

    assert immediate == ["a.jpg", "c.jpg"]
    assert deferred == ["b.jpg"]


def test_order_crops_keeps_everything_when_filter_unavailable(monkeypatch):
    monkeypatch.setattr(crop_quality, "score", lambda paths: None)

    immediate, deferred = crop_quality.order_crops(["a.jpg", "b.jpg"], 0.0)

    assert immediate == ["a.jpg", "b.jpg"]
    assert deferred == []


def test_single_crop_is_never_deferred(monkeypatch):
    """Один кроп — откладывать нечего: он и есть единственное чтение."""

    called = []
    monkeypatch.setattr(crop_quality, "score", lambda paths: called.append(paths) or [-1.0])

    assert crop_quality.order_crops(["only.jpg"], 0.0) == (["only.jpg"], [])
    assert called == []


def test_filter_setting_defaults_to_on_and_can_be_disabled(monkeypatch):
    monkeypatch.setattr(processor, "_stored", lambda _key: None)
    assert processor.crop_filter_enabled() is True

    monkeypatch.setattr(processor, "_stored", lambda _key: False)
    assert processor.crop_filter_enabled() is False


def test_update_settings_saves_the_switch(monkeypatch):
    saved = {}
    monkeypatch.setattr(
        processor.settings_store,
        "set_value",
        lambda key, value: saved.__setitem__(key, value),
    )
    monkeypatch.setattr(
        processor,
        "public_settings",
        lambda: {"crop_filter_enabled": saved.get(processor.QWEN_CROP_FILTER_KEY)},
    )

    processor.update_settings(crop_filter=False)

    assert saved[processor.QWEN_CROP_FILTER_KEY] is False


class _CropHarness:
    """Мини-сценарий run_photo: порядок чтения кропов и результат."""

    def __init__(self, monkeypatch, readings: dict[str, str], order: list[str]):
        self.readings = readings
        self.order = order
        self.saved = {}

        monkeypatch.setattr(processor.db, "get_photo_source", lambda pid: "/tmp/source.jpg")
        monkeypatch.setattr(processor.db, "mark_running", lambda pid: None)
        monkeypatch.setattr(
            processor.db, "save_success", lambda pid, **kw: self.saved.update(kw)
        )
        monkeypatch.setattr(processor, "resolve_settings", lambda: {
            "provider": "ollama", "model": "test-model", "crop": {"mode": "off", "ratio": 1.0},
        })
        monkeypatch.setattr(processor, "analysis_input", lambda pid, src: "full.jpg")
        monkeypatch.setattr(processor, "low_priority_names", lambda: [])
        monkeypatch.setattr(processor, "forbidden_words", lambda: [])
        monkeypatch.setattr(processor, "crop_filter_enabled", lambda: True)

    def install(self, monkeypatch):
        from app.billboard import database as billboard_db
        from app.billboard import pipeline as billboard_pipeline

        monkeypatch.setattr(
            billboard_pipeline, "ensure_crops", lambda pid: list(self.readings)
        )
        monkeypatch.setattr(
            billboard_db, "get_billboard_regions", lambda pid: []
        )
        monkeypatch.setattr(
            billboard_db, "mark_qwen_running", lambda region_id: None
        )
        monkeypatch.setattr(
            billboard_db, "save_qwen_success", lambda *a, **k: None
        )
        monkeypatch.setattr(
            billboard_db, "save_qwen_failure", lambda *a, **k: None
        )

        def fake_analyze(path, config=None):
            self.order.append(path)
            text = self.readings.get(path, "")
            return ({"description": text, "client": None, "brand": None, "category": None,
                     "tags": []}, {}, 0.1)

        monkeypatch.setattr(processor, "analyze_image", fake_analyze)


def test_deferred_crop_is_not_read_when_other_crop_described(monkeypatch):
    """Мусорный кроп не читается, если нормальный дал описание."""

    harness = _CropHarness(
        monkeypatch,
        readings={"good_crop.jpg": "Реклама щита", "garbage.jpg": ""},
        order=[],
    )
    harness.install(monkeypatch)

    def fake_order(paths, threshold):
        return ["good_crop.jpg"], ["garbage.jpg"]

    monkeypatch.setattr(crop_quality, "order_crops", fake_order)

    processor.run_photo("PH_" + "ad" * 12)

    assert "good_crop.jpg" in harness.order
    assert "garbage.jpg" not in harness.order
    assert harness.saved["fields"]["description"].startswith("Реклама щита")


def test_deferred_crop_is_read_when_everything_is_empty(monkeypatch):
    """Нормальные кропы пусты — отложенный читается: реклама не теряется."""

    harness = _CropHarness(
        monkeypatch,
        readings={"main.jpg": "", "second.jpg": "Баннер «Покров»"},
        order=[],
    )
    harness.install(monkeypatch)

    monkeypatch.setattr(
        crop_quality, "order_crops", lambda paths, threshold: (["main.jpg"], ["second.jpg"])
    )

    processor.run_photo("PH_" + "bc" * 12)

    # Полный кадр читается дополнительно при нескольких кропах — это
    # правило multi_crop_full_frame, фильтр его не меняет.
    assert harness.order[:2] == ["main.jpg", "second.jpg"]
    assert harness.saved["fields"]["description"] == "Баннер «Покров»"

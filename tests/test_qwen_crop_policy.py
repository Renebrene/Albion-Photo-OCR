"""
Crop selection: one billboard for most photos, two for listed addresses.

Pure tests with injected configuration, no database.
"""

from __future__ import annotations

from app.qwen.crop_policy import multi_crop_addresses, select_crops

CROPS = ["crop_01.jpg", "crop_02.jpg"]


def test_single_crop_is_returned_as_is():
    assert select_crops("PH_1", ["crop_01.jpg"], addresses={193}) == ["crop_01.jpg"]


def test_empty_list_keeps_the_old_behaviour():
    # Policy disabled: every detected crop is analysed, as before.
    assert select_crops("PH_1", CROPS, addresses=set(), address_id=193) == CROPS


def test_listed_address_keeps_both_crops():
    assert select_crops("PH_1", CROPS, addresses={193}, address_id=193) == CROPS


def test_other_address_keeps_only_the_largest_crop():
    assert select_crops("PH_1", CROPS, addresses={193}, address_id=164) == [
        "crop_01.jpg"
    ]


def test_unknown_address_defaults_to_one_crop():
    assert select_crops("PH_1", CROPS, addresses={193}, address_id=None) == [
        "crop_01.jpg"
    ]


def test_environment_list_is_parsed(monkeypatch):
    monkeypatch.setenv("SCENE_QWEN_MULTI_CROP_ADDRESSES", "193, 164, bad, 0")
    assert multi_crop_addresses() == {193, 164}

    monkeypatch.setenv("SCENE_QWEN_MULTI_CROP_ADDRESSES", "")
    assert multi_crop_addresses() == set()

"""
Unit tests for scene-based photo selection (app/core/scene_select.py).

No model and no database: the feature maths is checked on synthetic vectors, and
the whole pipeline runs on a handful of generated JPEGs in a tmp folder.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.scene_select import (
    dedup_groups,
    hamming_matrix,
    pick_representatives,
    scene_features,
    select_scene_photos,
    target_scenes,
)


def _row(phash: int, dhash: int = 0, color: list[float] | None = None, brightness=0.5):
    return {
        "path": f"/tmp/{phash}.jpg",
        "phash": phash,
        "dhash": dhash,
        "color": color if color is not None else [1.0] * 42,
        "brightness": brightness,
    }


class TestDedupGroups:
    def test_near_identical_frames_form_one_series(self):
        # Two frames differing in one bit are one press of the shutter; the
        # third is the opposite pattern, 64 bits away.
        first = 0xAAAAAAAAAAAAAAAA
        hashes = np.array([first, first ^ 1, 0x5555555555555555], dtype=np.uint64)
        groups = dedup_groups(hamming_matrix(hashes), threshold=6)

        assert groups == [[0, 1], [2]]

    def test_distant_frames_stay_apart(self):
        hashes = np.array([0, 0xFF], dtype=np.uint64)
        groups = dedup_groups(hamming_matrix(hashes), threshold=6)

        assert groups == [[0], [1]]


class TestTargetScenes:
    def test_few_conditions_grow_to_the_working_minimum(self):
        assert target_scenes(2, 61, 20, 30) == 20

    def test_many_conditions_shrink_to_the_maximum(self):
        assert target_scenes(31, 60, 20, 30) == 30

    def test_within_the_range_is_kept(self):
        assert target_scenes(23, 55, 20, 30) == 23

    def test_never_more_than_there_are_series(self):
        # 16 distinct shots: the selection cannot invent a 17th.
        assert target_scenes(2, 16, 20, 30) == 16

    def test_forced_number_wins_but_stays_possible(self):
        assert target_scenes(2, 61, 20, 30, forced=12) == 12
        assert target_scenes(2, 10, 20, 30, forced=25) == 10


class TestSceneFeatures:
    def test_dhash_adds_a_block(self):
        rows = [_row(0xF0F0F0F0F0F0F0F0, 0x0F0F0F0F0F0F0F0F)]

        without = scene_features(rows, [0], use_dhash=False)
        with_dhash = scene_features(rows, [0], use_dhash=True)

        assert with_dhash.shape[1] == without.shape[1] + 64

    def test_bits_are_plus_minus_one(self):
        rows = [_row(0xAAAAAAAAAAAAAAAA)]
        features = scene_features(rows, [0], use_dhash=True)

        # The bit blocks (pHash + dHash + colour) are ±1; only brightness has
        # a weight of its own.
        assert set(np.unique(features[0, :170])) <= {-1.0, 1.0}


class TestPickRepresentatives:
    def test_one_photo_per_cluster_the_closest_to_the_centre(self):
        # Two clusters of three; the middle frame of each sits exactly on its
        # centre, so the pick is unambiguous.
        features = np.array(
            [
                [0.0, 0.0],
                [0.1, 0.0],
                [0.2, 0.0],
                [10.0, 10.0],
                [10.1, 10.0],
                [10.2, 10.0],
            ],
            dtype=np.float32,
        )
        rows = [_row(index) for index in range(6)]
        labels = [0, 0, 0, 1, 1, 1]

        picked = pick_representatives(
            features, labels, rows, keep=[0, 1, 2, 3, 4, 5]
        )

        assert picked == ["/tmp/1.jpg", "/tmp/4.jpg"]

    def test_single_frame_cluster_returns_that_frame(self):
        features = np.array([[1.0, 1.0], [5.0, 5.0]], dtype=np.float32)
        rows = [_row(7), _row(9)]

        picked = pick_representatives(features, [0, 1], rows, keep=[0, 1])

        assert sorted(picked) == ["/tmp/7.jpg", "/tmp/9.jpg"]

    def test_no_labels_no_picks(self):
        assert (
            pick_representatives(np.zeros((0, 2), dtype=np.float32), [], [], [])
            == []
        )


def _scene(path: Path, position: int) -> Path:
    """A black frame with a white square in one of six places."""

    image = Image.new("RGB", (96, 96), (0, 0, 0))
    left = (position % 3) * 32
    top = (position // 3) * 32

    for x in range(left, left + 32):
        for y in range(top, top + 32):
            image.putpixel((x, y), (255, 255, 255))

    image.save(path, "JPEG")

    return path


@pytest.fixture()
def photo_folder(tmp_path):
    """
    Six shooting conditions, four frames each.

    The frames inside a condition are copies (one burst), the conditions
    themselves are clearly different pictures - which is exactly what the
    series collapsing and the clustering are supposed to tell apart.
    """

    folder = tmp_path / "photos"
    folder.mkdir()

    photos = []

    for position in range(6):
        for shot in range(4):
            photos.append(_scene(folder / f"{position}_{shot}.jpg", position))

    return photos


class TestSelectScenePhotos:
    def test_bursts_collapse_into_series(self, photo_folder):
        result = select_scene_photos(photo_folder, workers=1, select_max=6)

        assert result["photos"] == 24
        assert result["hashed"] == 24
        # Four copies of each of the six conditions: 24 files, 6 series.
        assert result["series"] == 6

    def test_selection_is_one_photo_per_cluster(self, photo_folder):
        result = select_scene_photos(
            photo_folder,
            workers=1,
            select_min=6,
            select_max=9,
        )

        # Six series and a working minimum of six: every condition contributes
        # exactly one frame, so the selection is the whole folder in miniature.
        assert result["scenes"] == 6
        assert len(result["picked"]) == 6
        assert len(set(result["picked"])) == len(result["picked"])
        assert all(path.endswith(".jpg") for path in result["picked"])

    def test_working_range_is_respected(self, photo_folder):
        result = select_scene_photos(
            photo_folder,
            workers=1,
            select_min=5,
            select_max=5,
        )

        assert result["scenes"] == 5
        assert len(result["picked"]) == 5

    def test_unreadable_folder_gives_empty_selection(self, tmp_path):
        broken = tmp_path / "broken.jpg"
        broken.write_bytes(b"not an image at all")

        result = select_scene_photos([broken], workers=1)

        assert result["hashed"] == 0
        assert result["picked"] == []

    def test_dhash_changes_the_feature_space_not_the_api(self, photo_folder):
        with_dhash = select_scene_photos(photo_folder, workers=1, select_max=6)
        without = select_scene_photos(
            photo_folder, workers=1, select_max=6, use_dhash=False
        )

        assert with_dhash["picked"]
        assert without["picked"]

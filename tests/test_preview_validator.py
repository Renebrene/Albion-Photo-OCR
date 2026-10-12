"""
Unit tests for app.preview.validator.

A preview is valid only when it exists, is a regular file,
is JPEG, passes verify(), fully decodes, and matches the
expected dimensions when those are supplied.
"""

from PIL import Image

from app.preview.validator import validate_preview


def test_valid_jpeg_preview(make_jpeg):
    path = make_jpeg("PH_abc.jpg", size=(32, 20))

    result = validate_preview(path)

    assert result.valid is True
    assert result.exists is True
    assert result.format == "JPEG"
    assert (result.width, result.height) == (32, 20)
    assert result.error is None


def test_missing_preview_is_not_valid(tmp_path):
    result = validate_preview(tmp_path / "absent.jpg")

    assert result.valid is False
    assert result.exists is False
    assert result.width is None


def test_non_jpeg_preview_is_not_valid(tmp_path):
    path = tmp_path / "preview.jpg"  # PNG bytes behind a .jpg name
    Image.new("RGB", (8, 8)).save(path, format="PNG")

    result = validate_preview(path)

    assert result.valid is False
    assert result.exists is True
    assert "Unsupported preview format" in result.error


def test_expected_dimension_mismatch_is_not_valid(make_jpeg):
    path = make_jpeg("PH_abc.jpg", size=(32, 20))

    wrong_width = validate_preview(path, expected_width=100)
    wrong_height = validate_preview(path, expected_height=100)

    assert wrong_width.valid is False
    assert "Unexpected width" in wrong_width.error
    assert wrong_height.valid is False
    assert "Unexpected height" in wrong_height.error


def test_expected_dimension_match_is_valid(make_jpeg):
    path = make_jpeg("PH_abc.jpg", size=(32, 20))

    result = validate_preview(
        path,
        expected_width=32,
        expected_height=20,
    )

    assert result.valid is True
    assert (result.width, result.height) == (32, 20)

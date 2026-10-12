"""
Unit tests for app.preview.result.

PreviewFileResult validates its own invariants in __post_init__.
PreviewResult.ready is True only when both previews are valid.
"""

import pytest

from app.preview.result import (
    PREVIEW_ACTIONS,
    PreviewFileResult,
    PreviewResult,
    create_preview_result,
)


def _file(kind="SMALL", action="CREATE", valid=True, width=32, height=20, error=None):
    return PreviewFileResult(
        kind=kind,
        path=f"/preview/{kind.lower()}.jpg",
        action=action,
        valid=valid,
        width=width,
        height=height,
        error=error,
    )


def test_actions_constant():
    assert PREVIEW_ACTIONS == {"SKIP", "CREATE", "REGENERATE", "ERROR"}


def test_valid_file_result():
    result = _file()

    assert result.valid is True
    assert (result.width, result.height) == (32, 20)


def test_skip_action_is_allowed():
    assert _file(action="SKIP").action == "SKIP"


@pytest.mark.parametrize("kind", ["LARGE", "small", "", "THUMBNAIL"])
def test_bad_kind_is_rejected(kind):
    with pytest.raises(ValueError):
        _file(kind=kind)


@pytest.mark.parametrize("action", ["OK", "created", "", "DELETE"])
def test_bad_action_is_rejected(action):
    with pytest.raises(ValueError):
        _file(action=action)


def test_valid_file_requires_dimensions():
    with pytest.raises(ValueError):
        _file(valid=True, width=None)
    with pytest.raises(ValueError):
        _file(valid=True, width=0, height=10)


def test_valid_file_cannot_have_error():
    with pytest.raises(ValueError):
        _file(valid=True, error="boom")


def test_invalid_file_may_omit_dimensions():
    result = _file(valid=False, width=None, height=None, error="decode failed")

    assert result.valid is False
    assert result.error == "decode failed"


def test_ready_requires_both_valid():
    small = _file(kind="SMALL")
    middle = _file(kind="MIDDLE")
    broken = _file(kind="MIDDLE", action="ERROR", valid=False, width=None, height=None, error="x")

    assert PreviewResult(photo_id="PH_x", small=small, middle=middle).ready is True

    failed = PreviewResult(photo_id="PH_x", small=small, middle=broken)
    assert failed.ready is False
    assert failed.has_error is True


def test_create_preview_result_validates_kinds_and_id():
    small = _file(kind="SMALL")
    middle = _file(kind="MIDDLE")

    ok = create_preview_result(photo_id="PH_x", small=small, middle=middle)
    assert ok.photo_id == "PH_x"

    with pytest.raises(ValueError):
        create_preview_result(photo_id="", small=small, middle=middle)
    with pytest.raises(ValueError):
        create_preview_result(photo_id="PH_x", small=middle, middle=middle)

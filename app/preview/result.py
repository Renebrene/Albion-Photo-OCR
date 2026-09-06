from __future__ import annotations

from dataclasses import dataclass


PREVIEW_ACTIONS = {
    "SKIP",
    "CREATE",
    "REGENERATE",
    "ERROR",
}


@dataclass(frozen=True)
class PreviewFileResult:
    """
    Result of processing one preview file.

    SKIP       - existing preview was valid and was not modified.
    CREATE     - preview did not exist and was created.
    REGENERATE - existing invalid preview was replaced.
    ERROR      - preview could not be created or validated.
    """

    kind: str
    path: str

    action: str
    valid: bool

    width: int | None = None
    height: int | None = None

    error: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"SMALL", "MIDDLE"}:
            raise ValueError(
                f"Unsupported preview kind: {self.kind}"
            )

        if self.action not in PREVIEW_ACTIONS:
            raise ValueError(
                f"Unsupported preview action: {self.action}"
            )

        if not self.path:
            raise ValueError("path is required")

        if self.valid:
            if self.width is None or self.height is None:
                raise ValueError(
                    "Valid preview must have width and height"
                )

            if self.width < 1 or self.height < 1:
                raise ValueError(
                    "Preview dimensions must be >= 1"
                )

            if self.error is not None:
                raise ValueError(
                    "Valid preview cannot contain an error"
                )


@dataclass(frozen=True)
class PreviewResult:
    """
    Complete result of processing previews for one photo_id.

    A photo is considered preview-ready only when both
    SMALL and MIDDLE previews are valid.
    """

    photo_id: str

    small: PreviewFileResult
    middle: PreviewFileResult

    @property
    def ready(self) -> bool:
        """
        True only when both preview files are valid.
        """

        return self.small.valid and self.middle.valid

    @property
    def has_error(self) -> bool:
        """
        True when at least one preview failed.
        """

        return not self.ready


def create_preview_result(
    *,
    photo_id: str,
    small: PreviewFileResult,
    middle: PreviewFileResult,
) -> PreviewResult:
    """
    Assemble the final PREVIEW result for one photo.
    """

    if not photo_id:
        raise ValueError("photo_id is required")

    if small.kind != "SMALL":
        raise ValueError(
            "small result must have kind SMALL"
        )

    if middle.kind != "MIDDLE":
        raise ValueError(
            "middle result must have kind MIDDLE"
        )

    return PreviewResult(
        photo_id=photo_id,
        small=small,
        middle=middle,
    )

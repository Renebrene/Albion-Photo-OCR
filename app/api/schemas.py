"""
Pydantic response models for the read-only web API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class PhotoSummary(BaseModel):
    """Registered physical photo (current schema: photo_id + sha256 identity)."""

    photo_id: str = Field(pattern=r"^PH_[0-9a-f]{24}$")
    filename: str
    width: int
    height: int
    container_format: str


class PhotoPage(BaseModel):
    items: list[PhotoSummary]
    next_cursor: str | None = None

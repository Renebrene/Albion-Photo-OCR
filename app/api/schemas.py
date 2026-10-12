"""
Pydantic response models for the read-only web API.
"""

from __future__ import annotations

from datetime import datetime

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


class DinoBatchSummary(BaseModel):
    batch_id: int
    run_type: str
    status: str
    total_count: int
    completed_count: int
    failed_count: int
    created_at: datetime | None = None
    finished_at: datetime | None = None


class DinoBatchPage(BaseModel):
    items: list[DinoBatchSummary]
    next_cursor: int | None = None


class DinoRunSummary(BaseModel):
    run_id: int
    photo_id: str
    run_type: str
    status: str
    dino_best_id: str | None = None
    dino_score: float | None = None
    dino_confidence: str | None = None
    dino_status: str | None = None
    dino_time_sec: float | None = None
    error_message: str | None = None
    finished_at: datetime | None = None


class DinoRunPage(BaseModel):
    items: list[DinoRunSummary]
    next_cursor: int | None = None


class HybridRunSummary(BaseModel):
    hybrid_run_id: int
    dino_batch_id: int
    status: str
    total_count: int
    completed_count: int
    failed_count: int
    created_at: datetime | None = None
    finished_at: datetime | None = None


class HybridRunPage(BaseModel):
    items: list[HybridRunSummary]
    next_cursor: int | None = None

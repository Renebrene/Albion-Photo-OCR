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
    address: str | None = None
    client: str | None = None
    brand: str | None = None
    category: str | None = None


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


class DinoBatchRequest(BaseModel):
    """Request to create (and enqueue) a DINO batch."""

    run_type: str = Field(default="NORMAL", pattern=r"^(NORMAL|FORCE_RERUN)$")
    photo_ids: list[str] | None = None


class HybridRequest(BaseModel):
    """Request to create (and enqueue) a HYBRID run for a DINO batch."""

    dino_batch_id: int = Field(ge=1)


class QwenJobRequest(BaseModel):
    """Request to enqueue QWEN metadata for specific or all photos."""

    photo_ids: list[str] | None = None
    # When true, re-enqueue only photos whose QWEN row is FAILED
    # (takes precedence over photo_ids).
    only_failed: bool = False


class QwenModelRequest(BaseModel):
    """Select the QWEN (Ollama) model used for metadata extraction."""

    model: str = Field(min_length=1, max_length=128)


class CollectionSummary(BaseModel):
    collection_id: int
    name: str
    kind: str
    client: str | None = None
    scope: str
    created_at: datetime | None = None
    members: int = 0


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field(default="Моя", pattern=r"^(Моя|Клиентская)$")
    client: str | None = Field(default=None, max_length=200)
    scope: str = Field(default="photos", pattern=r"^(addresses|clients|photos)$")


class CollectionMembersRequest(BaseModel):
    member_type: str = Field(default="photo", pattern=r"^(address|client|photo)$")
    values: list[str] = Field(min_length=1)


class SelectionState(BaseModel):
    """Free-form per-manager GRID state blob."""

    state: dict = Field(default_factory=dict)


class NlSearchRequest(BaseModel):
    """Natural-language query, translated to filters by the worker."""

    query: str = Field(min_length=1, max_length=500)


class AutomationUpdate(BaseModel):
    """Partial update of the automation scheduler settings."""

    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    auto_dino: bool | None = None
    auto_qwen: bool | None = None


class SavedSearchCreate(BaseModel):
    """Named snapshot of the GRID filter state (bookmarked search)."""

    name: str = Field(min_length=1, max_length=200)
    filters: dict = Field(default_factory=dict)


class LoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(default="", max_length=200)


class UserSummary(BaseModel):
    user_id: int
    name: str
    color: str | None = None
    role: str
    active: bool


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(
        default="Менеджер",
        pattern=r"^(Администратор|Менеджер|Гость)$",
    )
    color: str | None = Field(default=None, max_length=32)
    password: str | None = Field(default=None, max_length=200)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=32)
    role: str | None = Field(
        default=None,
        pattern=r"^(Администратор|Менеджер|Гость)$",
    )
    active: bool | None = None
    password: str | None = Field(default=None, max_length=200)


class JobSummary(BaseModel):
    id: int
    job_type: str
    status: str
    attempts: int
    payload: dict
    result: dict | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobPage(BaseModel):
    items: list[JobSummary]
    next_cursor: int | None = None

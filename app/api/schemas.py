"""
Pydantic response models for the read-only web API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


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

    # INGEST metadata (schema 018). created_at is the upload/registration
    # time, taken_at the EXIF capture date (None when the file has none).
    created_at: datetime | None = None
    taken_at: datetime | None = None
    size_bytes: int | None = None

    # Address directory (schema 022), resolved from `address` (the recognised
    # fingerprint id). None until that id is mapped to an address.
    legal_address: str | None = None
    simple_address: str | None = None

    # QWEN icon in the grid: status plus whether a description actually exists
    # (a failed re-run keeps the previous description row).
    qwen_status: str | None = None
    qwen_described: bool | None = None


class PhotoPage(BaseModel):
    items: list[PhotoSummary]
    next_cursor: str | None = None


class VideoSummary(BaseModel):
    video_id: str = Field(pattern=r"^VI_[0-9a-f]{24}$")
    filename: str
    display_title: str = ""
    container_format: str
    video_codec: str
    width: int
    height: int
    duration_seconds: float
    fps: float | None = None
    frame_count: int | None = None
    size_bytes: int
    taken_at: datetime | None = None
    created_at: datetime | None = None


class VideoPage(BaseModel):
    items: list[VideoSummary]
    next_cursor: str | None = None


class VideoTitleUpdate(BaseModel):
    display_title: str = Field(max_length=300)


class VideoTranscodeRequest(BaseModel):
    profile: str = Field(pattern=r"^(strong_720p|standard_1080p|light_1440p)$")


class VideoTrimRequest(BaseModel):
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    end_seconds: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        if self.end_seconds - self.start_seconds < 0.25:
            raise ValueError("trim range must be at least 0.25 seconds")
        return self


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
    mode: str = Field(default="manual", pattern="^(manual|schedule|outofqueue)$")
    auto_hybrid: bool = False


class HybridRequest(BaseModel):
    """Request to create (and enqueue) a HYBRID run for a DINO batch."""

    dino_batch_id: int = Field(ge=1)


class MediaLinkRequest(BaseModel):
    """Upload selected media to the configured cloud storage."""

    photo_ids: list[str] = Field(default_factory=list, max_length=50)
    video_ids: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_selection(self):
        total = len(self.photo_ids) + len(self.video_ids)
        if total == 0:
            raise ValueError("at least one photo_id or video_id is required")
        if total > 50:
            raise ValueError("at most 50 media items per request")
        return self


class QwenJobRequest(BaseModel):
    """Request to enqueue QWEN metadata for specific or all photos."""

    photo_ids: list[str] | None = Field(default=None, max_length=5000)
    # When true, re-enqueue only photos whose QWEN row is FAILED
    # (takes precedence over photo_ids).
    only_failed: bool = False
    # Разовая пересборка (кнопка «Пересканировать» в карточке фото): прогнать
    # эти фото конкретным провайдером/моделью, не меняя общие настройки.
    provider: str | None = Field(default=None, pattern="^(ollama|openai)$")
    model: str | None = Field(default=None, max_length=200)


class QwenModelRequest(BaseModel):
    """Select the QWEN model used for metadata extraction."""

    model: str = Field(min_length=1, max_length=128)


class QwenSettingsUpdate(BaseModel):
    """Update QWEN provider/model/transport settings (partial)."""

    provider: str | None = Field(
        default=None, pattern=r"^(ollama|openai)$"
    )
    model: str | None = Field(default=None, min_length=1, max_length=128)
    base_url: str | None = Field(default=None, max_length=512)
    # None leaves the stored key unchanged; "" clears it.
    api_key: str | None = Field(default=None, max_length=512)
    keep_alive: str | None = Field(default=None, max_length=32)
    unload_on_idle: bool | None = None


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
    values: list[str] = Field(min_length=1, max_length=5000)


class ClientAliasRequest(BaseModel):
    """Map a raw QWEN client string to a canonical one."""

    alias: str = Field(min_length=1, max_length=200)
    canonical: str = Field(min_length=1, max_length=200)


class AddressCreate(BaseModel):
    """One address in the directory (schema/022).

    At least one name must be filled; the API rejects a blank pair.
    """

    legal_address: str | None = Field(default=None, max_length=300)
    simple_address: str | None = Field(default=None, max_length=300)
    sort_order: int | None = None


class AddressUpdate(BaseModel):
    """Partial update: omitted fields keep their stored value."""

    legal_address: str | None = Field(default=None, max_length=300)
    simple_address: str | None = Field(default=None, max_length=300)
    active: bool | None = None
    sort_order: int | None = None


class PhotoAddressRequest(BaseModel):
    """Manual legal-address correction for one photo."""

    address_id: int = Field(ge=1)


class QwenTextUpdate(BaseModel):
    """Hand-edited QWEN description of one photo."""

    description: str | None = Field(default=None, max_length=4000)
    client: str | None = Field(default=None, max_length=300)
    brand: str | None = Field(default=None, max_length=300)
    category: str | None = Field(default=None, max_length=300)
    tags: list[str] = Field(default_factory=list, max_length=20)


class AddressFingerprintsRequest(BaseModel):
    """Fingerprint ids mapped to an address (the list replaces the current one)."""

    fingerprints: list[str] = Field(default_factory=list, max_length=500)


class FingerprintBatchItem(BaseModel):
    """One fingerprint to build inside a batch."""

    fingerprint_id: str = Field(min_length=1, max_length=64)
    folder: str = Field(min_length=1, max_length=4096)


class FingerprintBatchRequest(BaseModel):
    """Build several fingerprints from folders, distributed over the workers."""

    items: list[FingerprintBatchItem] = Field(min_length=1, max_length=200)
    max_photos: int | None = Field(default=None, ge=1, le=5000)
    replace: bool = True


class FingerprintAddressRequest(BaseModel):
    """Address from the directory to map a fingerprint to (None clears it)."""

    address_id: int | None = None


class FingerprintBuildRequest(BaseModel):
    """Build (or rebuild) a fingerprint from a folder of photos."""

    fingerprint_id: str = Field(min_length=1, max_length=64)
    folder: str = Field(min_length=1, max_length=4096)
    max_photos: int | None = Field(default=None, ge=1, le=5000)
    replace: bool = True


class FingerprintUpdate(BaseModel):
    """Human fields of a fingerprint (schema/023); omitted keeps the value."""

    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    source_folder: str | None = Field(default=None, max_length=1000)
    active: bool | None = None


class SelectionState(BaseModel):
    """Free-form per-manager GRID state blob."""

    state: dict = Field(default_factory=dict)


class ArchiveItem(BaseModel):
    """One file of a ZIP download: which photo, under which name."""

    photo_id: str = Field(pattern=r"^PH_[0-9a-f]{24}$")
    # The window sends the same name it would use for a single download; it is
    # sanitised again on the server before it becomes an archive entry.
    name: str | None = Field(default=None, max_length=300)


class ArchiveRequest(BaseModel):
    items: list[ArchiveItem] = Field(default_factory=list, max_length=500)


class SourcePathRequest(BaseModel):
    """A server-side folder chosen in the UI (validated by the API)."""

    path: str = Field(min_length=1, max_length=4096)


class SourceRunRequest(BaseModel):
    """Folder for an INGEST run; omitted -> the configured working folder."""

    path: str | None = Field(default=None, max_length=4096)


class PipelineStartRequest(BaseModel):
    """Start a resumable pipeline run (Обновление базы)."""

    folder: str | None = Field(default=None, max_length=4096)
    mode: str = Field(default="manual", pattern="^(manual|schedule|outofqueue)$")


class SearchQueryRequest(BaseModel):
    """Manual media search: filters edited by the user (step two)."""

    q: str | None = Field(default=None, max_length=2000)
    client: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=200)
    # Tags edited in the window: extra free-text terms for the ranking.
    tags: list[str] | None = Field(default=None, max_length=20)


class NlSearchRequest(BaseModel):
    """Natural-language query, translated to filters by the worker."""

    query: str = Field(min_length=1, max_length=500)


class AutomationUpdate(BaseModel):
    """Partial update of the automation scheduler settings."""

    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    mode: str | None = Field(default=None, pattern="^(interval|daily)$")
    daily_time: str | None = Field(default=None, max_length=5)
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


# Only HEX colours reach CSS variables/avatars; the UI palette already sends
# HEX, this closes the API path too (no `url(...)`, `;` or named colours).
HEX_COLOR_PATTERN = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(
        default="Менеджер",
        pattern=r"^(Администратор|Менеджер|Гость)$",
    )
    color: str | None = Field(
        default=None, max_length=9, pattern=HEX_COLOR_PATTERN
    )
    password: str | None = Field(default=None, max_length=200)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(
        default=None, max_length=9, pattern=HEX_COLOR_PATTERN
    )
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

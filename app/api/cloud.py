"""
Настройки файлохранилища Albion и проверка связи.

Токен — админский секрет: чтение настроек отдаёт только маску, изменение и
проверка требуют `settings:write` (есть только у Администратора).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_scope
from app.api.schemas import CloudSettingsUpdate
from app.cloud import albion, config

read_router = APIRouter()
write_router = APIRouter()


@read_router.get(
    "/v1/cloud/settings",
    response_model=None,
    dependencies=[Depends(require_scope("read"))],
)
def get_cloud_settings():
    """Текущие настройки Albion; токен показан только маской."""

    return config.public_settings()


@write_router.put(
    "/v1/cloud/settings",
    response_model=None,
    dependencies=[Depends(require_scope("settings:write"))],
)
def update_cloud_settings(request: CloudSettingsUpdate):
    try:
        return config.update_settings(
            base_url=request.base_url,
            api_key=request.api_key,
            folder_id=request.folder_id,
            ttl_days=request.ttl_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@write_router.post(
    "/v1/cloud/verify",
    response_model=None,
    dependencies=[Depends(require_scope("settings:write"))],
)
def verify_cloud():
    """Проверить токен и его права на стороне Albion."""

    try:
        return albion.verify()
    except albion.CloudConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except albion.CloudUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

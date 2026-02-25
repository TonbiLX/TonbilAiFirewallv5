# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Servis engelleme Pydantic semalari.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BlockedServiceResponse(BaseModel):
    id: int
    service_id: str
    name: str
    group_name: str
    icon_svg: Optional[str] = None
    rules: list[str]
    domain_count: int
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceBlockedServiceResponse(BaseModel):
    service_id: str
    name: str
    group_name: str
    icon_svg: Optional[str] = None
    blocked: bool
    schedule: Optional[dict] = None

    class Config:
        from_attributes = True


class DeviceServiceToggle(BaseModel):
    """Tek servis toggle istegi."""
    service_id: str
    blocked: bool
    schedule: Optional[dict] = None


class DeviceServiceBulkUpdate(BaseModel):
    """Toplu servis güncelleme istegi."""
    blocked_service_ids: list[str]


class ServiceGroupResponse(BaseModel):
    group: str
    count: int

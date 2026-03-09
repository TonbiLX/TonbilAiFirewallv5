# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Engellenen IP Pydantic semalari.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BlockedIpCreate(BaseModel):
    ip_address: str
    reason: str = "Manuel engelleme"
    duration_minutes: Optional[int] = None  # None = kalici, 60/360/1440/10080 vb.


class BlockedIpUpdateDuration(BaseModel):
    ip_address: str
    duration_minutes: Optional[int] = None  # None = kalici yap


class BlockedIpResponse(BaseModel):
    id: Optional[int] = None
    ip_address: str
    reason: Optional[str] = None
    blocked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_manual: bool = True
    source: str = "manual"
    remaining_seconds: Optional[int] = None  # Hesaplanan kalan sure (DB + Redis)

    class Config:
        from_attributes = True


class BlockedIpUnblock(BaseModel):
    ip_address: str


class IpManagementStats(BaseModel):
    trusted_ip_count: int = 0
    blocked_ip_count: int = 0
    manual_block_count: int = 0
    auto_block_count: int = 0


class BlockedIpBulkUnblock(BaseModel):
    ip_addresses: list[str]


class BlockedIpBulkUpdateDuration(BaseModel):
    ip_addresses: list[str]
    duration_minutes: int | None = None  # None = kalici


class BulkOperationResult(BaseModel):
    success_count: int = 0
    failed_count: int = 0
    failed_ips: list[str] = []

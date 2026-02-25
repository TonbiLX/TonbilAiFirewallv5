# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Blocklist Pydantic semalari: API request/response validasyonu.
# NOT: Validator'lar sadece Create modelinde.

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class BlocklistCreate(BaseModel):
    name: str
    url: str
    description: Optional[str] = None
    format: Optional[str] = "auto"
    enabled: bool = True
    update_frequency_hours: int = 24

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('URL bos olamaz')
        if len(v) > 2048:
            raise ValueError('URL 2048 karakterden uzun olamaz')
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL http:// veya https:// ile baslamali')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Isim bos olamaz')
        if len(v) > 200:
            raise ValueError('Isim 200 karakterden uzun olamaz')
        return v

    @field_validator('update_frequency_hours')
    @classmethod
    def validate_frequency(cls, v: int) -> int:
        if v < 1 or v > 720:
            raise ValueError('Güncelleme sıklığı 1-720 saat aralığında olmali')
        return v


class BlocklistUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    enabled: Optional[bool] = None
    update_frequency_hours: Optional[int] = None


class BlocklistResponse(BaseModel):
    id: int
    name: str
    url: str
    description: Optional[str] = None
    format: Optional[str] = "auto"
    enabled: bool = True
    update_frequency_hours: int = 24
    domain_count: int = 0
    last_updated: Optional[datetime] = None
    last_error: Optional[str] = None
    content_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlocklistRefreshResponse(BaseModel):
    """Tek blocklist güncelleme sonuçu."""
    blocklist_id: int
    name: str
    previous_domain_count: int
    new_domain_count: int
    added_count: int
    removed_count: int
    status: str  # "updated", "unchanged", "error"
    error_message: Optional[str] = None


class BulkRefreshResponse(BaseModel):
    """Toplu blocklist güncelleme sonuçu."""
    total_blocklists: int
    updated_count: int
    unchanged_count: int
    failed_count: int
    total_domains_before: int
    total_domains_after: int
    new_domains_added: int
    results: List[BlocklistRefreshResponse]

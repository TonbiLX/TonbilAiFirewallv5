# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Icerik filtre kategorisi semalari.

from pydantic import BaseModel
from datetime import datetime


class BlocklistSummary(BaseModel):
    """Kategoriye bagli blocklist ozet bilgisi."""
    id: int
    name: str
    domain_count: int
    enabled: bool

    class Config:
        from_attributes = True


class ContentCategoryCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    example_domains: list[str] | None = None
    custom_domains: str | None = None
    blocklist_ids: list[int] | None = None


class ContentCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    example_domains: list[str] | None = None
    custom_domains: str | None = None
    blocklist_ids: list[int] | None = None
    enabled: bool | None = None


class ContentCategoryResponse(BaseModel):
    id: int
    key: str
    name: str
    description: str | None
    icon: str | None
    color: str | None
    example_domains: list[str] | None
    custom_domains: str | None
    domain_count: int
    enabled: bool
    blocklist_ids: list[int] = []
    blocklists: list[BlocklistSummary] = []
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True

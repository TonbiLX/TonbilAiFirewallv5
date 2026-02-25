# --- Ajan: MIMAR (THE ARCHITECT) ---
# Profile Pydantic semalari: API request/response validasyonu.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProfileBase(BaseModel):
    name: str
    profile_type: str = "adult"
    allowed_hours: Optional[dict] = None
    content_filters: Optional[list] = None
    bandwidth_limit_mbps: Optional[int] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    profile_type: Optional[str] = None
    allowed_hours: Optional[dict] = None
    content_filters: Optional[list] = None
    bandwidth_limit_mbps: Optional[int] = None


class ProfileResponse(ProfileBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

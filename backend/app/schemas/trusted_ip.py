# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Güvenilir IP Pydantic semalari.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TrustedIpCreate(BaseModel):
    ip_address: str
    description: Optional[str] = None


class TrustedIpResponse(BaseModel):
    id: int
    ip_address: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

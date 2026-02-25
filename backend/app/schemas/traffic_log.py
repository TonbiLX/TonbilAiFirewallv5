# --- Ajan: MIMAR (THE ARCHITECT) ---
# TrafficLog Pydantic semalari.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TrafficLogResponse(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    device_id: int
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    destination_domain: Optional[str] = None
    category: Optional[str] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    protocol: Optional[str] = None

    class Config:
        from_attributes = True

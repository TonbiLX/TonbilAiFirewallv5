# --- Ajan: MIMAR (THE ARCHITECT) ---
# Cihaz bağlantı logu semalari.

from pydantic import BaseModel
from datetime import datetime


class DeviceConnectionLogResponse(BaseModel):
    id: int
    device_id: int
    event_type: str
    ip_address: str | None = None
    session_duration_seconds: int | None = None
    timestamp: datetime | None = None

    class Config:
        from_attributes = True

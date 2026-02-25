# --- Ajan: ANALIST (THE ANALYST) ---
# AiInsight Pydantic semalari.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AiInsightResponse(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    severity: str
    message: str
    suggested_action: Optional[str] = None
    related_device_id: Optional[int] = None
    category: Optional[str] = None
    is_dismissed: bool = False

    class Config:
        from_attributes = True

# --- Ajan: ANALIST (THE ANALYST) ---
# AI Sohbet semalari.

from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    action_type: str | None = None
    action_result: dict | None = None


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    action_type: str | None
    action_result: str | None
    timestamp: datetime | None

    class Config:
        from_attributes = True

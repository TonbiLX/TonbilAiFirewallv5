# --- Ajan: MIMAR (THE ARCHITECT) ---
# Telegram Bot yapılandirma semalari.

from pydantic import BaseModel
from datetime import datetime


class TelegramConfigUpdate(BaseModel):
    bot_token: str | None = None
    chat_ids: str | None = None
    enabled: bool | None = None
    notify_new_device: bool | None = None
    notify_blocked_ip: bool | None = None
    notify_trusted_ip_threat: bool | None = None
    notify_ai_insight: bool | None = None


class TelegramConfigResponse(BaseModel):
    id: int
    bot_token_masked: str | None = None
    chat_ids: str | None = None
    enabled: bool
    notify_new_device: bool
    notify_blocked_ip: bool
    notify_trusted_ip_threat: bool
    notify_ai_insight: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TelegramTestRequest(BaseModel):
    message: str = "TonbilAiOS test mesaji - Bot bağlantısi başarılı!"

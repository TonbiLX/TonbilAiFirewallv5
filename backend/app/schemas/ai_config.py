# --- Ajan: ANALIST (THE ANALYST) ---
# Yapay Zeka LLM yapılandirma semalari.

from pydantic import BaseModel
from datetime import datetime


class AiConfigUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    chat_mode: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    log_analysis_enabled: bool | None = None
    log_analysis_interval_minutes: int | None = None
    log_analysis_max_logs: int | None = None
    daily_request_limit: int | None = None
    custom_system_prompt: str | None = None
    enabled: bool | None = None


class AiConfigResponse(BaseModel):
    id: int
    provider: str
    api_key_masked: str | None = None
    base_url: str | None = None
    model: str | None = None
    chat_mode: str
    temperature: float
    max_tokens: int
    log_analysis_enabled: bool
    log_analysis_interval_minutes: int
    log_analysis_max_logs: int
    daily_request_limit: int
    daily_request_count: int
    custom_system_prompt: str | None = None
    enabled: bool
    last_test_result: str | None = None
    last_test_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AiTestRequest(BaseModel):
    prompt: str = "Merhaba, sen TonbilAiOS router asistanisin. Kısa bir selamlama yap."


class AiTestResponse(BaseModel):
    success: bool
    response: str | None = None
    latency_ms: int | None = None
    model_used: str | None = None
    error: str | None = None


class AiProviderInfo(BaseModel):
    id: str
    name: str
    models: list[dict]
    requires_api_key: bool
    requires_base_url: bool
    default_base_url: str | None = None
    description: str


class AiStatsResponse(BaseModel):
    daily_request_count: int
    daily_request_limit: int
    remaining_today: int
    provider: str
    model: str | None = None
    chat_mode: str
    enabled: bool
    last_test_at: datetime | None = None

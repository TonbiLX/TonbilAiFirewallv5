# --- Ajan: ANALIST (THE ANALYST) ---
# Yapay Zeka Ayarları API: config CRUD, bağlantı testi, saglayici listesi, istatistikler.

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.ai_config import AiConfig
from app.schemas.ai_config import (
    AiConfigUpdate, AiConfigResponse, AiTestRequest, AiTestResponse,
    AiProviderInfo, AiStatsResponse,
)
from app.services import llm_service
from app.services.llm_providers import get_provider_info
from app.services import llm_cache

router = APIRouter()


def _mask_api_key(key: str | None) -> str | None:
    """API anahtarini maskele: ilk 4 ve son 4 karakter goster."""
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


def _config_to_response(config: AiConfig) -> AiConfigResponse:
    """AiConfig modelden AiConfigResponse oluştur."""
    return AiConfigResponse(
        id=config.id,
        provider=config.provider,
        api_key_masked=_mask_api_key(config.api_key),
        base_url=config.base_url,
        model=config.model,
        chat_mode=config.chat_mode,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        log_analysis_enabled=config.log_analysis_enabled,
        log_analysis_interval_minutes=config.log_analysis_interval_minutes,
        log_analysis_max_logs=config.log_analysis_max_logs,
        daily_request_limit=config.daily_request_limit,
        daily_request_count=config.daily_request_count or 0,
        custom_system_prompt=config.custom_system_prompt,
        enabled=config.enabled,
        last_test_result=config.last_test_result,
        last_test_at=config.last_test_at,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/config", response_model=AiConfigResponse)
async def get_ai_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Yapay zeka yapılandirmasini getir (API key maskelenmis)."""
    result = await db.execute(select(AiConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = AiConfig()
        db.add(config)
        await db.flush()
        await db.refresh(config)

    return _config_to_response(config)


@router.put("/config", response_model=AiConfigResponse)
async def update_ai_config(
    data: AiConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Yapay zeka yapılandirmasini güncelle/oluştur."""
    result = await db.execute(select(AiConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = AiConfig()
        db.add(config)
        await db.flush()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    await db.flush()
    await db.refresh(config)

    # Config cache'ini geçersiz kil
    llm_service.invalidate_config_cache()

    return _config_to_response(config)


@router.post("/test", response_model=AiTestResponse)
async def test_ai_connection(
    data: AiTestRequest = AiTestRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """LLM bağlantı testi yap."""
    result = await db.execute(select(AiConfig).limit(1))
    config = result.scalar_one_or_none()

    if not config or config.provider == "none":
        raise HTTPException(
            status_code=400,
            detail="Once bir AI saglayici seçin.",
        )

    # API key gerekliligi kontrol
    provider_list = get_provider_info()
    provider_meta = next((p for p in provider_list if p["id"] == config.provider), None)
    if provider_meta and provider_meta["requires_api_key"] and not config.api_key:
        raise HTTPException(
            status_code=400,
            detail=f"{provider_meta['name']} için API anahtarı gerekli.",
        )

    test_result = await llm_service.test_connection(
        provider=config.provider,
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        prompt=data.prompt,
    )

    # Test sonuçunu DB'ye kaydet
    config.last_test_result = (
        f"Başarılı ({test_result['latency_ms']}ms)"
        if test_result["success"]
        else f"Başarısız: {test_result.get('error', 'Bilinmeyen hata')}"
    )
    config.last_test_at = datetime.utcnow()
    await db.flush()

    llm_service.invalidate_config_cache()

    return AiTestResponse(**test_result)


@router.get("/providers", response_model=list[AiProviderInfo])
async def list_providers(
    current_user: User = Depends(get_current_user),
):
    """Desteklenen AI saglayicilari ve modelleri listele."""
    return [AiProviderInfo(**p) for p in get_provider_info()]


@router.get("/stats", response_model=AiStatsResponse)
async def get_ai_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Günlük kullanım istatistiklerini getir."""
    result = await db.execute(select(AiConfig).limit(1))
    config = result.scalar_one_or_none()

    if not config:
        return AiStatsResponse(
            daily_request_count=0,
            daily_request_limit=200,
            remaining_today=200,
            provider="none",
            model=None,
            chat_mode="tfidf",
            enabled=False,
        )

    # Gun degistiyse sayacı sıfırla
    today = datetime.utcnow().strftime("%Y-%m-%d")
    count = config.daily_request_count or 0
    if config.daily_reset_date != today:
        count = 0

    limit = config.daily_request_limit or 200

    return AiStatsResponse(
        daily_request_count=count,
        daily_request_limit=limit,
        remaining_today=max(0, limit - count),
        provider=config.provider,
        model=config.model,
        chat_mode=config.chat_mode,
        enabled=config.enabled,
        last_test_at=config.last_test_at,
    )


@router.post("/reset-counter")
async def reset_daily_counter(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Günlük istek sayacını sıfırla."""
    result = await db.execute(select(AiConfig).limit(1))
    config = result.scalar_one_or_none()
    if config:
        config.daily_request_count = 0
        config.daily_reset_date = None
        await db.flush()
        llm_service.invalidate_config_cache()

    return {"message": "Günlük sayaç sıfırlandı."}

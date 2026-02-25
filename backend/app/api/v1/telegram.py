# --- Ajan: MIMAR (THE ARCHITECT) ---
# Telegram Bot API: yapılandirma CRUD ve test mesaji.

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.telegram_config import TelegramConfig
from app.schemas.telegram import TelegramConfigUpdate, TelegramConfigResponse, TelegramTestRequest
from app.services import telegram_service

router = APIRouter()


def _mask_token(token: str | None) -> str | None:
    """Bot token'i maskele: ilk 10 ve son 4 karakter goster."""
    if not token:
        return None
    if len(token) <= 14:
        return "***"
    return token[:10] + "..." + token[-4:]


@router.get("/config", response_model=TelegramConfigResponse)
async def get_telegram_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Telegram yapılandirmasini getir (token maskelenmis)."""
    result = await db.execute(select(TelegramConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TelegramConfig()
        db.add(config)
        await db.flush()
        await db.refresh(config)

    return TelegramConfigResponse(
        id=config.id,
        bot_token_masked=_mask_token(config.bot_token),
        chat_ids=config.chat_ids,
        enabled=config.enabled,
        notify_new_device=config.notify_new_device,
        notify_blocked_ip=config.notify_blocked_ip,
        notify_trusted_ip_threat=config.notify_trusted_ip_threat,
        notify_ai_insight=getattr(config, "notify_ai_insight", True),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("/config", response_model=TelegramConfigResponse)
async def update_telegram_config(
    data: TelegramConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Telegram yapılandirmasini güncelle/oluştur."""
    result = await db.execute(select(TelegramConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TelegramConfig()
        db.add(config)
        await db.flush()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    await db.flush()
    await db.refresh(config)

    # Config cache'ini geçersiz kil
    telegram_service.invalidate_cache()

    return TelegramConfigResponse(
        id=config.id,
        bot_token_masked=_mask_token(config.bot_token),
        chat_ids=config.chat_ids,
        enabled=config.enabled,
        notify_new_device=config.notify_new_device,
        notify_blocked_ip=config.notify_blocked_ip,
        notify_trusted_ip_threat=config.notify_trusted_ip_threat,
        notify_ai_insight=getattr(config, "notify_ai_insight", True),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/test")
async def test_telegram(
    data: TelegramTestRequest = TelegramTestRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test mesaji gönder."""
    result = await db.execute(select(TelegramConfig).limit(1))
    config = result.scalar_one_or_none()

    if not config or not config.bot_token or not config.chat_ids:
        raise HTTPException(
            status_code=400,
            detail="Once bot token ve chat ID yapılandirin.",
        )

    chat_ids = [cid.strip() for cid in config.chat_ids.split(",") if cid.strip()]
    if not chat_ids:
        raise HTTPException(status_code=400, detail="Gecerli chat ID bulunamadı.")

    success = await telegram_service.send_message(
        f"<b>TonbilAiOS</b>\n\n{data.message}",
        bot_token=config.bot_token,
        chat_ids=chat_ids,
    )

    if success:
        return {"status": "success", "message": "Test mesaji gönderildi."}
    else:
        raise HTTPException(status_code=500, detail="Mesaj gönderilemedi. Token ve Chat ID'yi kontrol edin.")

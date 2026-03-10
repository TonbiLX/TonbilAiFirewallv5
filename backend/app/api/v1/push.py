# --- Ajan: MIMAR (THE ARCHITECT) ---
# Push Bildirim API: kanal listesi, toggle ve FCM token kaydi.
# Telegram bildirim konfigurasyon modeli uzerinden kanal tercihlerini yonetir.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.telegram_config import TelegramConfig
from app.models.user import User
from app.schemas.push import PushChannelResponse, PushRegisterRequest, PushRegisterResponse
from app.services import telegram_service

router = APIRouter()

# Kanal ID → TelegramConfig alan adi eslestirmesi
_CHANNEL_FIELD_MAP = {
    "security_threats": "notify_blocked_ip",
    "device_events": "notify_new_device",
    "trusted_ip_threats": "notify_trusted_ip_threat",
    "ai_insights": "notify_ai_insight",
}


def _build_channels(config: TelegramConfig) -> list[PushChannelResponse]:
    return [
        PushChannelResponse(
            id="security_threats",
            name="Tehdit Bildirimleri",
            description="IP engelleme ve guvenlik tehditleri",
            enabled=bool(config.notify_blocked_ip),
        ),
        PushChannelResponse(
            id="device_events",
            name="Cihaz Bildirimleri",
            description="Yeni cihaz baglantilari",
            enabled=bool(config.notify_new_device),
        ),
        PushChannelResponse(
            id="trusted_ip_threats",
            name="Guvenilir IP Tehditleri",
            description="Guvenilir IP'lerde tespit edilen tehditler",
            enabled=bool(getattr(config, "notify_trusted_ip_threat", True)),
        ),
        PushChannelResponse(
            id="ai_insights",
            name="AI Icgoruleri",
            description="Yapay zeka guvenlik analizleri",
            enabled=bool(getattr(config, "notify_ai_insight", True)),
        ),
    ]


@router.get("/channels", response_model=list[PushChannelResponse])
async def get_push_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bildirim kanallarini listele. Telegram bildirim tercihleriyle senkronize."""
    result = await db.execute(select(TelegramConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TelegramConfig()
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return _build_channels(config)


@router.post("/channels/{channel_id}/toggle", response_model=PushChannelResponse)
async def toggle_push_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Belirli bir bildirim kanalini ac/kapat."""
    field_name = _CHANNEL_FIELD_MAP.get(channel_id)
    if not field_name:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen kanal: {channel_id}")

    result = await db.execute(select(TelegramConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TelegramConfig()
        db.add(config)
        await db.flush()

    current_value = bool(getattr(config, field_name, True))
    setattr(config, field_name, not current_value)
    await db.flush()
    await db.refresh(config)

    telegram_service.invalidate_cache()

    # Guncellenen kanali dondur
    channels = _build_channels(config)
    for ch in channels:
        if ch.id == channel_id:
            return ch

    raise HTTPException(status_code=500, detail="Kanal guncellenemedi")


@router.post("/register", response_model=PushRegisterResponse)
async def register_push_token(
    data: PushRegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """FCM push token kaydi (gelecek FCM entegrasyonu icin placeholder)."""
    # Ileride: data.token ve data.device_name DB'ye kaydedilecek
    return PushRegisterResponse(success=True, message="Token kaydedildi")


@router.post("/test-notification")
async def send_test_notification(
    current_user: User = Depends(get_current_user),
):
    """Test bildirimi gonder — WebSocket uzerinden tum bagli istemcilere."""
    from app.api.v1.ws import broadcast_security_event

    await broadcast_security_event(
        event_type="ddos_attack",
        severity="critical",
        title="DDoS Saldirisi Tespit Edildi!",
        message="185.220.101.42 adresinden SYN Flood saldirisi algilandi. Saldiri otomatik engellendi.",
        data={
            "ip": "185.220.101.42",
            "attack_type": "SYN Flood",
            "packets_per_sec": 12500,
            "country": "DE",
        },
    )
    return {"success": True, "message": "Test bildirimi gonderildi"}

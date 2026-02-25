# --- Ajan: MIMAR (THE ARCHITECT) ---
# Telegram bildirim servisi: mesaj gönderme ve bildirimler.
# Config DB'den yuklenir, bellekte cache'lenir, 60 sn'de bir yenilenir.
# Tum zaman damgalari sistem ayarlarındaki saat dilimine göre gösterilir.

import asyncio
import logging

import httpx

from app.db.session import async_session_factory
from app.models.telegram_config import TelegramConfig
from app.services.timezone_service import format_local_time
from sqlalchemy import select

logger = logging.getLogger("tonbilai.telegram")

# Bellek içinde config cache
_cached_config: dict | None = None
_last_refresh: float = 0
CACHE_TTL = 60  # saniye


async def _load_config() -> dict | None:
    """DB'den Telegram yapılandirmasini yukle."""
    global _cached_config, _last_refresh
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(TelegramConfig).limit(1))
            config = result.scalar_one_or_none()
            if config and config.enabled and config.bot_token and config.chat_ids:
                _cached_config = {
                    "bot_token": config.bot_token,
                    "chat_ids": [cid.strip() for cid in config.chat_ids.split(",") if cid.strip()],
                    "notify_new_device": config.notify_new_device,
                    "notify_blocked_ip": config.notify_blocked_ip,
                    "notify_trusted_ip_threat": config.notify_trusted_ip_threat,
                    "notify_ai_insight": getattr(config, "notify_ai_insight", True),
                }
            else:
                _cached_config = None
            _last_refresh = asyncio.get_event_loop().time()
    except Exception as e:
        logger.error(f"Telegram config yüklenemedi: {e}")
        _cached_config = None
    return _cached_config


async def get_config() -> dict | None:
    """Bellekteki config'i dondur, TTL gectiyse yenile."""
    global _last_refresh
    try:
        now = asyncio.get_event_loop().time()
    except RuntimeError:
        now = _last_refresh + CACHE_TTL + 1
    if _cached_config is None or (now - _last_refresh) > CACHE_TTL:
        return await _load_config()
    return _cached_config


def invalidate_cache():
    """Config cache'ini geçersiz kil (ayar degistiginde cagrilir)."""
    global _cached_config, _last_refresh
    _cached_config = None
    _last_refresh = 0


async def send_message(text: str, bot_token: str | None = None, chat_ids: list[str] | None = None, use_html: bool = True) -> bool:
    """Tum chat_id'lere Telegram mesaji gönder. HTML hata verirse plain text dener."""
    if not bot_token or not chat_ids:
        config = await get_config()
        if not config:
            return False
        bot_token = config["bot_token"]
        chat_ids = config["chat_ids"]

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    success = False

    async with httpx.AsyncClient(timeout=10) as client:
        for chat_id in chat_ids:
            try:
                payload = {"chat_id": chat_id, "text": text}
                if use_html:
                    payload["parse_mode"] = "HTML"

                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    success = True
                    logger.info(f"Telegram mesaj gönderildi chat_id={chat_id}")
                else:
                    # HTML parse hatasi varsa plain text olarak tekrar dene
                    if use_html and "parse entities" in resp.text:
                        logger.info(f"HTML parse hatasi, plain text deneniyor chat_id={chat_id}")
                        plain_payload = {"chat_id": chat_id, "text": text}
                        resp2 = await client.post(url, json=plain_payload)
                        if resp2.status_code == 200:
                            success = True
                        else:
                            logger.warning(f"Telegram mesaj gönderilemedi chat_id={chat_id}: {resp2.text}")
                    else:
                        logger.warning(f"Telegram mesaj gönderilemedi chat_id={chat_id}: {resp.text}")
            except Exception as e:
                logger.error(f"Telegram mesaj hatasi chat_id={chat_id}: {e}")

    return success


# --- Gorsel Bildirim Fonksiyonlari ---

async def notify_new_device(
    ip: str,
    hostname: str | None,
    manufacturer: str | None,
    device_type: str | None = None,
    detected_os: str | None = None,
):
    """Yeni cihaz bildirimi gönder (gorsel format)."""
    config = await get_config()
    if not config or not config.get("notify_new_device"):
        return

    # Cihaz tipine göre emoji
    type_emoji = {
        "phone": "\U0001f4f1", "tv": "\U0001f4fa", "computer": "\U0001f4bb",
        "console": "\U0001f3ae", "iot": "\U0001f916", "vr_headset": "\U0001f576",
        "network_device": "\U0001f310", "wearable": "\u231a", "tablet": "\U0001f4f1",
        "camera": "\U0001f4f7",
    }.get(device_type or "", "\U0001f4e1")

    os_text = f"\n<b>Isletim Sistemi:</b> {detected_os}" if detected_os else ""
    type_text = f"\n<b>Cihaz Tipi:</b> {device_type}" if device_type else ""

    text = (
        f"{type_emoji} <b>Yeni Cihaz Algilandi!</b>\n"
        f"\n"
        f"\U0001f310 <b>IP:</b> <code>{ip}</code>\n"
        f"\U0001f4bb <b>Hostname:</b> {hostname or 'Bilinmiyor'}\n"
        f"\U0001f3ed <b>Uretici:</b> {manufacturer or 'Bilinmiyor'}"
        f"{os_text}{type_text}\n"
        f"\n"
        f"\U0001f552 <b>Zaman:</b> {format_local_time()}\n"
        f"\n"
        f"\U0001f6e1 <i>TonbilAiOS Güvenlik Sistemi</i>"
    )
    await send_message(text)


async def notify_ip_blocked(ip: str, reason: str | None = None):
    """IP engelleme bildirimi gönder (gorsel format)."""
    config = await get_config()
    if not config or not config.get("notify_blocked_ip"):
        return

    text = (
        f"\U0001f6a8 <b>IP Engellendi!</b>\n"
        f"\n"
        f"\U0001f310 <b>IP:</b> <code>{ip}</code>\n"
        f"\u26a0\ufe0f <b>Sebep:</b> {reason or 'Bilinmiyor'}\n"
        f"\n"
        f"\U0001f552 <b>Zaman:</b> {format_local_time()}\n"
        f"\n"
        f"\U0001f6e1 <i>TonbilAiOS Tehdit Korumasi</i>"
    )
    await send_message(text)


async def notify_trusted_ip_threat(ip: str, reason: str):
    """Güvenilir IP'den tehdit tespiti bildirimi gönder."""
    config = await get_config()
    if not config or not config.get("notify_trusted_ip_threat"):
        return

    text = (
        f"\u26a0\ufe0f <b>Güvenilir IP Tehdit Uyarısı!</b>\n"
        f"\n"
        f"\U0001f6e1 <b>IP:</b> <code>{ip}</code>\n"
        f"\U0001f50d <b>Tespit:</b> {reason}\n"
        f"\n"
        f"\U0001f4a1 <b>Not:</b> Bu IP guvenilir listesinde oldugu için "
        f"<b>engellenmedi</b>, ancak anormal aktivite tespit edildi.\n"
        f"\n"
        f"\U0001f552 <b>Zaman:</b> {format_local_time()}\n"
        f"\n"
        f"\U0001f6e1 <i>TonbilAiOS Güvenlik Sistemi</i>"
    )
    await send_message(text)


async def notify_device_isolation_suggestion(
    ip: str,
    hostname: str | None,
    device_type: str | None,
    risk_factors: list[str],
    risk_score: int,
):
    """Cihaz izolasyon onerisi bildirimi gönder (gorsel format)."""
    config = await get_config()
    if not config or not config.get("notify_blocked_ip"):
        return

    # Risk seviyesine göre emoji
    if risk_score >= 80:
        risk_emoji = "\U0001f534"  # red circle
    elif risk_score >= 60:
        risk_emoji = "\U0001f7e0"  # orange circle
    else:
        risk_emoji = "\U0001f7e1"  # yellow circle

    factors_text = "\n".join(f"  \u2022 {f}" for f in risk_factors)

    text = (
        f"\u26a0\ufe0f <b>CIHAZ IZOLASYON ONERISI</b>\n"
        f"\n"
        f"\U0001f4bb <b>Cihaz:</b> {hostname or 'Bilinmiyor'}\n"
        f"\U0001f310 <b>IP:</b> <code>{ip}</code>\n"
        f"\U0001f4e1 <b>Tip:</b> {device_type or 'Bilinmiyor'}\n"
        f"{risk_emoji} <b>Risk Skoru:</b> {risk_score}/100\n"
        f"\n"
        f"\U0001f50d <b>Risk Faktorleri:</b>\n{factors_text}\n"
        f"\n"
        f"\U0001f6e1 Izole etmek için: <code>{hostname or ip} engelle</code>\n"
        f"\n"
        f"\U0001f552 {format_local_time()}"
    )
    await send_message(text)


async def notify_ai_insight(severity: str, message: str, category: str = "security"):
    """AI Insight bildirimi gönder (tum insight'lar için merkezi bildirim)."""
    config = await get_config()
    if not config:
        logger.debug("notify_ai_insight: Telegram config bulunamadı, bildirim atlanıyor.")
        return
    if not config.get("notify_ai_insight"):
        logger.debug("notify_ai_insight: notify_ai_insight devre disi.")
        return

    # Severity'ye göre emoji
    severity_map = {
        "critical": "\U0001f534",  # red circle
        "warning": "\U0001f7e0",   # orange circle
        "info": "\U0001f535",      # blue circle
    }
    emoji = severity_map.get(severity, "\U0001f535")

    # Kategori etiketi
    cat_labels = {
        "security": "\U0001f6e1 Güvenlik",
        "trusted_ip_threat": "\U0001f91d Güvenilir IP",
        "isolation": "\U0001f6a7 Izolasyon",
        "reputation": "\U0001f50d Itibar",
        "anomaly": "\U0001f4ca Anomali",
        "optimization": "\u2699\ufe0f Optimizasyon",
    }
    cat_text = cat_labels.get(category, f"\U0001f4cb {category}")

    text = (
        f"{emoji} <b>AI Uyari ({severity.upper()})</b>\n"
        f"\n"
        f"\U0001f4cc <b>Kategori:</b> {cat_text}\n"
        f"\U0001f4dd <b>Detay:</b> {message}\n"
        f"\n"
        f"\U0001f552 <b>Zaman:</b> {format_local_time()}\n"
        f"\n"
        f"\U0001f916 <i>TonbilAiOS AI Analiz</i>"
    )
    await send_message(text)


async def notify_hourly_summary(stats: dict):
    """Saatlik DNS özet raporu gönder (gorsel format)."""
    config = await get_config()
    if not config:
        logger.debug("notify_hourly_summary: Telegram config bulunamadı, bildirim atlanıyor.")
        return

    block_rate = stats.get("block_rate", 0)
    # Engelleme oranına göre emoji
    if block_rate > 30:
        rate_emoji = "\U0001f534"
    elif block_rate > 15:
        rate_emoji = "\U0001f7e0"
    else:
        rate_emoji = "\U0001f7e2"

    text = (
        f"\U0001f4ca <b>SAATLIK DNS OZETI</b>\n"
        f"\n"
        f"\U0001f4e8 <b>Toplam Sorgu:</b> {stats.get('total_queries', 0)}\n"
        f"\U0001f6ab <b>Engellenen:</b> {stats.get('blocked_queries', 0)} "
        f"({rate_emoji} %{block_rate:.1f})\n"
        f"\U0001f4f1 <b>Aktif Cihaz:</b> {stats.get('active_devices', 0)}\n"
        f"\n"
        f"\U0001f451 <b>En Aktif Cihazlar:</b>\n{stats.get('top_devices_text', '-')}\n"
        f"\n"
        f"\U0001f6ab <b>En Çok Engellenen:</b>\n{stats.get('top_blocked_text', '-')}\n"
        f"\n"
        f"\U0001f552 {format_local_time()}\n"
        f"\U0001f6e1 <i>TonbilAiOS</i>"
    )
    await send_message(text)

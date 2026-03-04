# --- Ajan: MIMAR (THE ARCHITECT) ---
# Telegram Bot polling worker: getUpdates ile mesaj alma ve NLP motoru ile işlem.
# Sadece yetkili chat_id'lerden gelen mesajlara yanit verir.

import asyncio
import logging

import httpx

from app.db.session import async_session_factory
from app.services.telegram_service import get_config, send_message
from app.services.ai_engine import get_engine, ParsedCommand, Entity, SERVICE_DOMAINS, normalize_turkish
from app.services import llm_service
from app.models.device import Device
from app.models.profile import Profile
from app.models.content_category import ContentCategory
from app.models.chat_message import ChatMessage
from sqlalchemy import select, desc

logger = logging.getLogger("tonbilai.telegram_worker")

# Son islenen update_id
_last_update_id = 0

# Onay bekleyen islemler: chat_id -> {"action": str, "timestamp": float}
_pending_confirmations: dict[str, dict] = {}

# Telegram mesaj karakter limiti
_TELEGRAM_MAX_LENGTH = 4096


async def _build_db_context(db) -> dict:
    """NLP için DB context oluştur (chat.py ile ayni pattern)."""
    devices_result = await db.execute(select(Device))
    devices = [
        {"id": d.id, "hostname": d.hostname or "", "ip_address": d.ip_address,
         "manufacturer": d.manufacturer or "", "is_blocked": d.is_blocked}
        for d in devices_result.scalars().all()
    ]
    profiles_result = await db.execute(select(Profile))
    profiles = [
        {"id": p.id, "name": p.name, "profile_type": p.profile_type}
        for p in profiles_result.scalars().all()
    ]
    cats_result = await db.execute(select(ContentCategory))
    categories = [
        {"id": c.id, "key": c.key, "name": c.name, "enabled": c.enabled}
        for c in cats_result.scalars().all()
    ]
    return {"devices": devices, "profiles": profiles, "categories": categories}


async def _try_llm_for_telegram(
    text: str,
    db_context: dict,
    db,
) -> object | None:
    """Telegram için LLM yonlendirme. Başarılı -> response, başarısız -> None."""
    from app.api.v1.chat import execute_commands
    from app.schemas.chat import ChatResponse

    try:
        config = await llm_service.get_ai_config()
        if not config or not config["enabled"] or config["chat_mode"] == "tfidf":
            return None

        chat_mode = config["chat_mode"]

        # Son sohbet gecmisini al
        history_result = await db.execute(
            select(ChatMessage)
            .order_by(desc(ChatMessage.id))
            .limit(6)
        )
        history_msgs = list(history_result.scalars().all())
        history_msgs.reverse()
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_msgs
        ]

        result = await llm_service.chat(text, db_context, chat_history)

        if not result:
            if chat_mode == "llm":
                return ChatResponse(
                    reply="AI servisi su anda yanit veremiyor.",
                    action_type="error",
                    action_result=None,
                )
            return None

        commands_data = result.get("commands", [])
        if not commands_data:
            return None

        # direct_reply kontrolü
        first_cmd = commands_data[0]
        if first_cmd.get("direct_reply"):
            reply_text = first_cmd.get("reply", "")
            # Ham JSON Telegram'a gitmesin — JSON ile basliyorsa TF-IDF'e dusur
            if reply_text.strip().startswith(("{", "[", "```")):
                logger.warning("LLM direct_reply ham JSON iceriyor, TF-IDF fallback")
                return None
            return ChatResponse(
                reply=reply_text,
                action_type="direct_reply",
                action_result=None,
            )

        # ParsedCommand'a donustur
        parsed_commands = []
        for cmd_data in commands_data:
            entities = []
            for ent in cmd_data.get("entities", []):
                ent_type = ent.get("type", "")
                ent_value = ent.get("value", "")
                ent_meta = dict(ent.get("metadata", {}))

                # LLM service entity'lerine SERVICE_DOMAINS'tan domain listesi ekle
                if ent_type == "service" and "domains" not in ent_meta:
                    svc_key = normalize_turkish(ent_value).lower()
                    if svc_key in SERVICE_DOMAINS:
                        ent_meta["domains"] = SERVICE_DOMAINS[svc_key]
                    else:
                        for key in SERVICE_DOMAINS:
                            if svc_key in key or key in svc_key:
                                ent_meta["domains"] = SERVICE_DOMAINS[key]
                                break
                    if "domains" not in ent_meta:
                        if "." in ent_value:
                            ent_meta["domains"] = [ent_value]
                        else:
                            ent_meta["domains"] = [f"{ent_value}.com"]

                if ent_type == "domain" and "domains" not in ent_meta:
                    ent_meta["domains"] = [ent_value]

                entities.append(Entity(
                    type=ent_type,
                    value=ent_value,
                    original=ent.get("original", ent_value),
                    confidence=1.0,
                    metadata=ent_meta,
                ))
            parsed_commands.append(ParsedCommand(
                intent=cmd_data.get("intent", "unknown"),
                confidence=1.0,
                entities=entities,
                original_text=text,
            ))

        if parsed_commands:
            return await execute_commands(parsed_commands, db)
        return None

    except Exception as e:
        logger.error(f"Telegram LLM hatasi: {e}")
        return None


async def _send_long_message(text: str, bot_token: str, chat_id: str):
    """Uzun mesajlari satirdan bolerek parcalar halinde gonder."""
    if len(text) <= _TELEGRAM_MAX_LENGTH:
        await send_message(text, bot_token=bot_token, chat_ids=[chat_id], use_html=True)
        return

    # Satirlardan bol (HTML tag'larini bozmamak icin)
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > _TELEGRAM_MAX_LENGTH:
            if chunk:
                await send_message(chunk, bot_token=bot_token, chat_ids=[chat_id], use_html=True)
            chunk = line
        else:
            chunk = f"{chunk}\n{line}" if chunk else line
    if chunk:
        await send_message(chunk, bot_token=bot_token, chat_ids=[chat_id], use_html=True)


async def _handle_confirmation(text: str, chat_id: str, bot_token: str) -> bool:
    """Onay bekleyen islem varsa isle. True donerse mesaj islendi demektir."""
    import time

    if chat_id not in _pending_confirmations:
        return False

    pending = _pending_confirmations[chat_id]

    # 60 saniye timeout
    if time.time() - pending["timestamp"] > 60:
        del _pending_confirmations[chat_id]
        return False

    text_lower = text.lower().strip()

    # Onay kelimeleri
    if any(w in text_lower for w in ["evet", "onayliyorum", "onay", "tamam", "yes"]):
        action = pending["action"]
        del _pending_confirmations[chat_id]

        if action == "system_reboot":
            try:
                import subprocess
                await send_message(
                    "\u2699\ufe0f Sistem yeniden baslatiliyor...",
                    bot_token=bot_token, chat_ids=[chat_id], use_html=True,
                )
                subprocess.Popen(["sudo", "reboot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                await send_message(
                    f"\u274c Reboot hatasi: {str(e)[:200]}",
                    bot_token=bot_token, chat_ids=[chat_id],
                )
        return True

    # Iptal kelimeleri
    if any(w in text_lower for w in ["hayir", "iptal", "vazgec", "cancel", "no"]):
        del _pending_confirmations[chat_id]
        await send_message(
            "\u274c Islem iptal edildi.",
            bot_token=bot_token, chat_ids=[chat_id], use_html=True,
        )
        return True

    return False


async def _process_message(text: str, chat_id: str, bot_token: str):
    """Tek bir mesaji isle: LLM + TF-IDF fallback."""
    from app.api.v1.chat import execute_commands
    from datetime import datetime

    try:
        async with async_session_factory() as db:
            db_context = await _build_db_context(db)

            # LLM yonlendirme
            response = await _try_llm_for_telegram(text, db_context, db)

            # LLM başarısız/tfidf -> TF-IDF fallback
            if response is None:
                engine = get_engine()
                commands = engine.parse(text, db_context)
                response = await execute_commands(commands, db)

            # Mesajlari DB'ye kaydet
            user_msg = ChatMessage(
                role="user",
                content=f"[Telegram] {text}",
                timestamp=datetime.utcnow(),
            )
            db.add(user_msg)

            assistant_msg = ChatMessage(
                role="assistant",
                content=response.reply,
                action_type=response.action_type,
                timestamp=datetime.utcnow(),
            )
            db.add(assistant_msg)
            await db.commit()

            # system_reboot onay mekanizmasi
            if response.action_type == "system_reboot" and response.action_result and response.action_result.get("needs_confirmation"):
                import time
                _pending_confirmations[chat_id] = {
                    "action": "system_reboot",
                    "timestamp": time.time(),
                }

            # Telegram için HTML formatlama
            reply_text = response.reply

            # Markdown -> Telegram HTML donusumu
            from app.services.chat_formatter import markdown_to_telegram_html
            reply_text = markdown_to_telegram_html(reply_text)

            await _send_long_message(reply_text, bot_token, chat_id)

    except Exception as e:
        logger.error(f"Telegram mesaj işleme hatasi: {e}")
        await send_message(
            f"Komut islenirken hata oluştu: {str(e)[:200]}",
            bot_token=bot_token,
            chat_ids=[chat_id],
        )


async def _poll_updates(bot_token: str, allowed_chat_ids: list[str]):
    """Telegram getUpdates long-polling ile mesajlari al."""
    global _last_update_id

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {
        "timeout": 30,
        "allowed_updates": ["message"],
    }
    if _last_update_id > 0:
        params["offset"] = _last_update_id + 1

    try:
        async with httpx.AsyncClient(timeout=35) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Telegram getUpdates hatasi: {resp.status_code}")
                return

            data = resp.json()
            if not data.get("ok"):
                return

            for update in data.get("result", []):
                update_id = update.get("update_id", 0)
                if update_id > _last_update_id:
                    _last_update_id = update_id

                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat_id = str(message.get("chat", {}).get("id", ""))

                if not text or not chat_id:
                    continue

                # Yetkili chat_id kontrolü
                if chat_id not in allowed_chat_ids:
                    logger.info(f"Yetkisiz chat_id: {chat_id}, mesaj yoksayildi")
                    continue

                logger.info(f"Telegram mesaj alindi: chat_id={chat_id}, text={text[:50]}")

                # /start komutu
                if text == "/start":
                    await send_message(
                        "Merhaba! Ben <b>TonbilAiOS Router</b> asistaniyim.\n\n"
                        "Turkce komutlar ile router'inizi yonetebilirsiniz.\n"
                        "<code>yardim</code> yazarak komutlari görebilirsiniz.",
                        bot_token=bot_token,
                        chat_ids=[chat_id],
                    )
                    continue

                # Onay bekleyen islem varsa once onu isle
                if await _handle_confirmation(text, chat_id, bot_token):
                    continue

                # NLP motoru ile isle
                await _process_message(text, chat_id, bot_token)

    except httpx.ReadTimeout:
        pass  # Normal: long-polling timeout
    except Exception as e:
        logger.error(f"Telegram polling hatasi: {e}")
        await asyncio.sleep(5)  # Hata sonrası bekleme (tight loop onleme)


async def start_telegram_worker():
    """Ana Telegram polling dongusu."""
    logger.info("Telegram worker başlatiliyor...")

    _consecutive_errors = 0

    while True:
        try:
            config = await get_config()
            if config and config.get("bot_token") and config.get("chat_ids"):
                await _poll_updates(config["bot_token"], config["chat_ids"])
                _consecutive_errors = 0
            else:
                # Config yoksa veya devre disiysa 30 sn bekle
                await asyncio.sleep(30)
        except Exception as e:
            _consecutive_errors += 1
            # Exponential backoff: 10s, 20s, 40s, ... max 300s
            backoff = min(10 * (2 ** (_consecutive_errors - 1)), 300)
            logger.error(
                f"Telegram worker hatasi (ardisik #{_consecutive_errors}, "
                f"sonraki deneme {backoff}s): {e}"
            )
            await asyncio.sleep(backoff)

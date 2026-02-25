# --- Ajan: ANALIST (THE ANALYST) ---
# Ana LLM servisi: config cache, chat işleme, yanit parser, gunluk limit.
# TF-IDF ile ayni ParsedCommand yapisina donusturur.

import json
import re
import time
import logging
from datetime import datetime

from app.services.llm_providers import call_llm
from app.services.llm_prompts import build_system_prompt
from app.services import llm_cache

logger = logging.getLogger("tonbilai.llm_service")

# Config cache (30 saniye TTL)
_config_cache: dict | None = None
_config_cache_time: float = 0
_CONFIG_CACHE_TTL = 30


async def get_ai_config() -> dict | None:
    """DB'den AI config yukle (30s cache)."""
    global _config_cache, _config_cache_time

    now = time.time()
    if _config_cache and (now - _config_cache_time) < _CONFIG_CACHE_TTL:
        return _config_cache

    try:
        from app.db.session import async_session_factory
        from app.models.ai_config import AiConfig
        from sqlalchemy import select

        async with async_session_factory() as session:
            result = await session.execute(select(AiConfig).limit(1))
            config = result.scalar_one_or_none()
            if not config:
                return None

            _config_cache = {
                "provider": config.provider,
                "api_key": config.api_key,
                "base_url": config.base_url,
                "model": config.model,
                "chat_mode": config.chat_mode,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "log_analysis_enabled": config.log_analysis_enabled,
                "log_analysis_interval_minutes": config.log_analysis_interval_minutes,
                "log_analysis_max_logs": config.log_analysis_max_logs,
                "daily_request_limit": config.daily_request_limit,
                "daily_request_count": config.daily_request_count,
                "daily_reset_date": config.daily_reset_date,
                "custom_system_prompt": config.custom_system_prompt,
                "enabled": config.enabled,
            }
            _config_cache_time = now
            return _config_cache
    except Exception as e:
        logger.error(f"AI config yüklenemedi: {e}")
        return None


def invalidate_config_cache():
    """Config cache'ini temizle (PUT sonrası)."""
    global _config_cache, _config_cache_time
    _config_cache = None
    _config_cache_time = 0


async def _increment_daily_counter():
    """Gunluk istek sayacıni artir. Gun degistiyse sıfırla."""
    try:
        from app.db.session import async_session_factory
        from app.models.ai_config import AiConfig
        from sqlalchemy import select

        today = datetime.utcnow().strftime("%Y-%m-%d")

        async with async_session_factory() as session:
            result = await session.execute(select(AiConfig).limit(1))
            config = result.scalar_one_or_none()
            if not config:
                return

            if config.daily_reset_date != today:
                config.daily_request_count = 1
                config.daily_reset_date = today
            else:
                config.daily_request_count = (config.daily_request_count or 0) + 1

            await session.commit()

        invalidate_config_cache()
    except Exception as e:
        logger.error(f"Gunluk sayac güncelleme hatasi: {e}")


def _parse_llm_json(response_text: str) -> list[dict] | None:
    """LLM JSON yanitini parse et. Gemini/OpenAI/Anthropic formatlarini destekler."""
    if not response_text:
        return None

    text = response_text.strip()

    # Markdown code block kaldir (regex ile robust)
    # ```json ... ``` veya ``` ... ``` bloklarini cikar
    fence_match = re.search(r'```(?:json|python)?\s*\n?(.*?)```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    elif text.startswith("```"):
        # Fallback: kapanmamis fence
        text = re.sub(r'^```(?:json|python)?\s*\n?', '', text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    # 1) Duz JSON parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return [parsed]
        elif isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)] or None
        else:
            return None
    except (json.JSONDecodeError, ValueError):
        pass

    # 2) Metin icerisindeki JSON dizisini bul: [ ... ]
    arr_match = re.search(r'\[[\s\S]*\]', text)
    if arr_match:
        try:
            parsed = json.loads(arr_match.group(0))
            if isinstance(parsed, list):
                result = [item for item in parsed if isinstance(item, dict)]
                if result:
                    return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 3) Metin icerisindeki tek JSON nesnesini bul: { ... }
    obj_match = re.search(r'\{[\s\S]*\}', text)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(0))
            if isinstance(parsed, dict):
                return [parsed]
        except (json.JSONDecodeError, ValueError):
            pass

    logger.warning(f"LLM JSON parse hatasi: {text[:200]}")
    return None


async def chat(
    message: str,
    db_context: dict,
    chat_history: list[dict] | None = None,
) -> dict | None:
    """
    LLM ile sohbet et.
    Başarılı: {"commands": [parsed_dicts], "raw_response": str} dondurur.
    Başarısız: None dondurur (fallback için).
    """
    config = await get_ai_config()
    if not config or not config["enabled"] or config["provider"] == "none":
        return None

    # Gunluk limit kontrolü
    today = datetime.utcnow().strftime("%Y-%m-%d")
    count = config.get("daily_request_count", 0)
    limit = config.get("daily_request_limit", 200)
    reset_date = config.get("daily_reset_date")

    if reset_date == today and count >= limit:
        logger.info(f"Gunluk LLM limiti asildi ({count}/{limit}).")
        return None

    # Cache kontrol
    cache_key = llm_cache.compute_cache_key(message, config["model"] or "")
    cached = await llm_cache.get_cached(cache_key)
    if cached:
        llm_cache.record_hit()
        parsed = _parse_llm_json(cached)
        if parsed:
            return {"commands": parsed, "raw_response": cached}

    llm_cache.record_miss()

    # Sistem promptu oluştur
    system_prompt = build_system_prompt(
        db_context,
        config.get("custom_system_prompt"),
    )

    # Mesaj dizisi oluştur
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history[-6:]:  # Son 6 mesaj baglam için
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    # LLM çağrısı
    response = await call_llm(
        provider=config["provider"],
        messages=messages,
        model=config["model"] or "",
        api_key=config.get("api_key"),
        base_url=config.get("base_url"),
        temperature=config.get("temperature", 0.3),
        max_tokens=config.get("max_tokens", 1024),
    )

    if response is None:
        return None

    # Cache'e yaz
    await llm_cache.set_cached(cache_key, response)

    # Gunluk sayacı artir
    await _increment_daily_counter()

    # JSON parse
    parsed = _parse_llm_json(response)
    if parsed:
        return {"commands": parsed, "raw_response": response}

    # JSON parse başarısız - direct_reply olarak dondur
    return {
        "commands": [{
            "intent": "direct_reply",
            "entities": [],
            "reply": response,
            "direct_reply": True,
        }],
        "raw_response": response,
    }


async def test_connection(
    provider: str,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    prompt: str = "Merhaba, kısa bir selamlama yap.",
) -> dict:
    """LLM bağlantı testi yap."""
    start = time.time()

    messages = [
        {"role": "system", "content": "Sen TonbilAiOS router asistanisin. Kısa yanit ver."},
        {"role": "user", "content": prompt},
    ]

    response = await call_llm(
        provider=provider,
        messages=messages,
        model=model or "",
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
        max_tokens=256,
    )

    latency = int((time.time() - start) * 1000)

    if response:
        return {
            "success": True,
            "response": response[:500],
            "latency_ms": latency,
            "model_used": model,
            "error": None,
        }
    else:
        return {
            "success": False,
            "response": None,
            "latency_ms": latency,
            "model_used": model,
            "error": "API bağlantısi başarısız. API anahtarini ve modeli kontrol edin.",
        }

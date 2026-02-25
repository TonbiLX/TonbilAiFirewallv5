# --- Ajan: ANALIST (THE ANALYST) ---
# LLM yanit cache'i: In-memory (hizli) + Redis (kalici).
# Maliyet kontrolü için ayni soru tekrar sorulunca LLM'e gitmez.

import hashlib
import time
import logging

logger = logging.getLogger("tonbilai.llm_cache")

# In-memory cache (Pi 5 4GB RAM'de max 100 entry yeterli)
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 dakika
_CACHE_MAX = 100

# Mutasyon intent'leri cache'lenmez
NON_CACHEABLE_PREFIXES = (
    "block_", "unblock_", "assign_", "open_", "close_",
    "rename_", "pin_", "vpn_connect", "vpn_disconnect",
)


def compute_cache_key(message: str, model: str) -> str:
    """Mesaj + model'den cache key oluştur."""
    normalized = message.strip().lower()
    raw = f"{model}:{normalized}"
    return hashlib.md5(raw.encode()).hexdigest()


def is_cacheable_response(response_text: str) -> bool:
    """Yanit cache'lenebilir mi kontrol et."""
    # Mutasyon iceren yanitlari cache'leme
    for prefix in NON_CACHEABLE_PREFIXES:
        if f'"intent": "{prefix}' in response_text:
            return False
    return True


async def get_cached(key: str) -> str | None:
    """Cache'ten yanit al: once in-memory, sonra Redis."""
    # In-memory
    if key in _cache:
        response, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return response
        del _cache[key]

    # Redis
    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()
        cached = await redis.get(f"llm:cache:{key}")
        if cached:
            # In-memory'ye de ekle
            _cache[key] = (cached, time.time())
            return cached
    except Exception:
        pass

    return None


async def set_cached(key: str, response: str):
    """Yaniti cache'e yaz."""
    if not is_cacheable_response(response):
        return

    # In-memory - doluysa en eskiyi at
    if len(_cache) >= _CACHE_MAX:
        oldest_key = min(_cache, key=lambda k: _cache[k][1])
        del _cache[oldest_key]
    _cache[key] = (response, time.time())

    # Redis (10 dakika TTL)
    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()
        await redis.set(f"llm:cache:{key}", response, ex=600)
    except Exception:
        pass


# Cache istatistikleri
_stats = {"hits": 0, "misses": 0}


def record_hit():
    _stats["hits"] += 1


def record_miss():
    _stats["misses"] += 1


def get_cache_stats() -> dict:
    total = _stats["hits"] + _stats["misses"]
    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate": round(_stats["hits"] / total, 2) if total > 0 else 0.0,
        "memory_entries": len(_cache),
    }

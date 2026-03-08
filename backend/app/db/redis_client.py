# --- Ajan: MIMAR (THE ARCHITECT) ---
# Async Redis bağlantı havuzu.
# Singleton pool: tüm worker'lar aynı pool'u paylaşır.
# max_connections=50 ile bağlantı sızıntısı önlenir.
# socket_timeout + retry_on_timeout ile bağlantı kopukluklarında otomatik yeniden deneme.

import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,
)

# Singleton Redis client — her get_redis() çağrısı aynı instance'ı döndürür
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Redis istemcisi dondur (singleton)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(connection_pool=redis_pool)
    return _redis_client

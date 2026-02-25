# --- Ajan: MIMAR (THE ARCHITECT) ---
# Async Redis bağlantı havuzu.

import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


async def get_redis() -> redis.Redis:
    """Redis istemcisi dondur."""
    return redis.Redis(connection_pool=redis_pool)

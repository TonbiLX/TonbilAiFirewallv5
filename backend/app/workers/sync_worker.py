# --- Ajan: MIMAR (THE ARCHITECT) ---
# Arka plan iscisi: Redis <-> MariaDB senkronizasyonu.
# Başlangicta MariaDB -> Redis yükleme, sonra her 60 saniyede Redis -> MariaDB sync.

import asyncio
import logging

from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.redis_client import get_redis
from app.models.device import Device
from app.config import get_settings

logger = logging.getLogger("tonbilai.sync_worker")
settings = get_settings()


async def load_mariadb_to_redis():
    """Başlangicta: MariaDB kalici verisini Redis onbellegine yukle."""
    logger.info("MariaDB verisi Redis'e yukleniyor...")
    redis_client = await get_redis()

    async with async_session_factory() as session:
        result = await session.execute(select(Device))
        devices = result.scalars().all()

        for device in devices:
            key = f"device:{device.mac_address}"
            await redis_client.hset(key, mapping={
                "ip": device.ip_address or "",
                "hostname": device.hostname or "",
                "manufacturer": device.manufacturer or "",
                "is_online": str(device.is_online),
                "is_blocked": str(device.is_blocked),
                "profile_id": str(device.profile_id) if device.profile_id else "",
            })
            await redis_client.expire(key, 300)

    logger.info(f"{len(devices)} cihaz Redis'e yuklendi.")


async def sync_redis_to_mariadb():
    """Degisken Redis durumunu MariaDB'ye kalici olarak kaydet."""
    logger.info("Redis -> MariaDB senkronizasyonu basliyor...")
    redis_client = await get_redis()

    async with async_session_factory() as session:
        cursor = 0
        synced = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match="device:*", count=100)
            for key in keys:
                data = await redis_client.hgetall(key)
                mac = key.split(":", 1)[1]

                result = await session.execute(
                    select(Device).where(Device.mac_address == mac)
                )
                device = result.scalar_one_or_none()
                if device:
                    device.ip_address = data.get("ip", device.ip_address)
                    device.is_online = data.get("is_online", "True") == "True"
                    device.hostname = data.get("hostname", device.hostname)
                    synced += 1

            if cursor == 0:
                break

        await session.commit()
    logger.info(f"Redis -> MariaDB senkronizasyonu tamamlandi ({synced} cihaz).")


async def start_sync_worker():
    """Ana senkronizasyon dongusu."""
    # Başlangicta MariaDB -> Redis yukle
    try:
        await load_mariadb_to_redis()
    except Exception as e:
        logger.error(f"Başlangic yüklemesi hatasi: {e}")

    # Periyodik sync dongusu
    while True:
        await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS)
        try:
            await sync_redis_to_mariadb()
        except Exception as e:
            logger.error(f"Sync worker hatasi: {e}")

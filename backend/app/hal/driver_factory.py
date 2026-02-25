# --- Ajan: MIMAR (THE ARCHITECT) ---
# Factory fonksiyonu: ENVIRONMENT degiskenine göre dogru ag surucusunu dondurur.
# Development: MockNetworkDriver (Docker, sahte veri)
# Production:  LinuxNetworkDriver (Pi 5, gercek nftables/dnsmasq/wg)

import logging
import redis.asyncio as aioredis

from app.config import get_settings
from app.hal.base_driver import BaseNetworkDriver
from app.hal.mock_driver import MockNetworkDriver

logger = logging.getLogger("tonbilai.hal")

_driver_instance: BaseNetworkDriver | None = None


async def get_network_driver(redis_client: aioredis.Redis) -> BaseNetworkDriver:
    """Singleton pattern ile ag surucusu al.
    LinuxNetworkDriver: DHCP için gercek dnsmasq, diger moduller mock.
    """
    global _driver_instance
    if _driver_instance is None:
        try:
            from app.hal.linux_driver import LinuxNetworkDriver
            logger.info("HAL: LinuxNetworkDriver yukleniyor (DHCP: dnsmasq)")
            _driver_instance = LinuxNetworkDriver(redis_client=redis_client)
        except ImportError:
            logger.warning(
                "HAL: LinuxNetworkDriver bulunamadı, MockNetworkDriver kullanılıyor."
            )
            _driver_instance = MockNetworkDriver(redis_client=redis_client)
    return _driver_instance

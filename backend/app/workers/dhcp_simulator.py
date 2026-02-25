# --- Ajan: MIMAR (THE ARCHITECT) ---
# DHCP simulasyon iscisi: gelistirme modunda sahte DHCP olaylari uretir.
# DHCP lease yenileme, yeni cihaz bağlantısi, lease süresi dolma simule edilir.

import asyncio
import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.device import Device
from app.models.dhcp_pool import DhcpPool
from app.models.dhcp_lease import DhcpLease
from app.hal.base_driver import BaseNetworkDriver
from app.config import get_settings

logger = logging.getLogger("tonbilai.dhcp_simulator")
settings = get_settings()


async def ensure_leases_for_devices(driver: BaseNetworkDriver):
    """Tum mevcut cihazlar için DHCP lease kaydi oluştur/güncelle."""
    async with async_session_factory() as session:
        # Havuzlari HAL'a bildir
        pools = (await session.execute(select(DhcpPool))).scalars().all()
        for pool in pools:
            await driver.configure_dhcp_pool({
                "id": pool.id,
                "name": pool.name,
                "range_start": pool.range_start,
                "range_end": pool.range_end,
                "netmask": pool.netmask,
                "gateway": pool.gateway,
                "enabled": pool.enabled,
                "lease_time_seconds": pool.lease_time_seconds,
            })

        # Cihazlar için lease oluştur
        devices = (await session.execute(select(Device))).scalars().all()
        for device in devices:
            result = await session.execute(
                select(DhcpLease).where(DhcpLease.mac_address == device.mac_address)
            )
            lease = result.scalar_one_or_none()
            if not lease:
                # Yeni lease oluştur
                now = datetime.utcnow()
                lease = DhcpLease(
                    mac_address=device.mac_address,
                    ip_address=device.ip_address or f"192.168.1.{100 + device.id}",
                    hostname=device.hostname,
                    lease_start=now - timedelta(hours=random.randint(1, 20)),
                    lease_end=now + timedelta(hours=random.randint(4, 24)),
                    is_static=False,
                    device_id=device.id,
                    pool_id=pools[0].id if pools else None,
                )
                session.add(lease)

        await session.commit()
    logger.info(f"DHCP lease kayitlari {len(devices)} cihaz için oluşturuldu/dogrulandi.")


async def simulate_dhcp_events(driver: BaseNetworkDriver):
    """DHCP olaylarini simule et: lease yenileme, DHCPACK loglari."""
    async with async_session_factory() as session:
        leases = (await session.execute(select(DhcpLease))).scalars().all()

        for lease in leases:
            # %30 olasilikla lease yenile
            if random.random() < 0.3:
                now = datetime.utcnow()
                lease.lease_start = now
                if not lease.is_static:
                    lease.lease_end = now + timedelta(seconds=86400)

                driver._log_command(
                    f"dnsmasq-dhcp: DHCPACK(eth0) {lease.ip_address} "
                    f"{lease.mac_address} {lease.hostname or 'unknown'}"
                )

        await session.commit()


async def start_dhcp_simulator(driver: BaseNetworkDriver):
    """Ana DHCP simulasyon dongusu (sadece gelistirme modu)."""
    logger.info("DHCP simulatoru başlatildi (gelistirme modu).")

    # Ilk yükleme
    try:
        await ensure_leases_for_devices(driver)
    except Exception as e:
        logger.error(f"DHCP ilk yükleme hatasi: {e}")

    # Periyodik simulasyon
    while True:
        await asyncio.sleep(settings.DHCP_SIMULATOR_INTERVAL_SECONDS)
        try:
            await simulate_dhcp_events(driver)
        except Exception as e:
            logger.error(f"DHCP simulatoru hatasi: {e}")

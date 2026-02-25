# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# MAC Resolver Worker: Placeholder MAC adresli cihazlarin gercek MAC'ini
# host ARP tablosundan (/host-proc/net/arp) okuyarak cozer.
# Ayrica hostname ve manufacturer bilgilerini günceller.

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, or_, update

from app.db.session import async_session_factory
from app.models.device import Device
from app.models.dns_query_log import DnsQueryLog
from app.models.device_connection_log import DeviceConnectionLog
from app.models.device_blocked_service import DeviceBlockedService
from app.models.device_custom_rule import DeviceCustomRule
from app.models.traffic_log import TrafficLog
from app.models.ai_insight import AiInsight
from app.workers.dhcp_worker import lookup_manufacturer, detect_device_type
from app.workers.device_discovery import detect_device_from_hostname

logger = logging.getLogger("tonbilai.mac_resolver")

# Host ARP tablosu
# Docker'da /proc namespace-isolated oldugu için host ARP'si gorunmuyor.
# Cozum: Host'taki cron job ARP tablosunu paylasilan volume'a yazar.
# Docker: /var/lib/tonbilai-time:/host-time-config
# Native (prod): dogrudan /proc/net/arp
HOST_ARP_PATHS = [
    # Path("/host-time-config/arp_table"),  # Docker: devre disi (native modda gerekli degil)
    Path("/proc/net/arp"),                 # Native (prod): dogrudan okuma
]

# Cozumleme aralığı (saniye)
RESOLVE_INTERVAL = 60  # Her 60 saniyede bir

# ARP tablosu satir deseni
# IP address       HW type     Flags       HW address            Mask     Device
ARP_LINE_PATTERN = re.compile(
    r"^(\d+\.\d+\.\d+\.\d+)\s+"  # IP
    r"0x\d+\s+"                    # HW type
    r"0x(\d+)\s+"                  # Flags (2=reachable, 0=incomplete)
    r"([0-9a-fA-F:]{17})\s+"      # HW address (MAC)
    r"\*\s+"                       # Mask
    r"(\S+)"                       # Device (interface)
)


def _find_arp_file() -> Path | None:
    """Erisilebilir ARP dosyasini bul."""
    for p in HOST_ARP_PATHS:
        if p.exists():
            return p
    return None


def read_host_arp_table() -> dict[str, str]:
    """Host ARP tablosunu oku, IP -> MAC esleme dict'i dondur.
    Sadece gecerli (Flags=0x2) ve end0/eth0/eth1 arayuzundeki kayitlari al.
    """
    result: dict[str, str] = {}

    arp_file = _find_arp_file()
    if not arp_file:
        return result

    try:
        content = arp_file.read_text()
        for line in content.strip().split("\n")[1:]:  # Header'i atla
            m = ARP_LINE_PATTERN.match(line.strip())
            if not m:
                continue

            ip = m.group(1)
            flags = m.group(2)
            mac = m.group(3).upper()
            interface = m.group(4)

            # Sadece reachable (flags=2) ve bilinen arayuzler
            if flags != "2":
                continue
            if interface not in ("br0", "end0", "eth0", "eth1", "wlan0"):
                continue
            # Geçersiz MAC'leri filtrele
            if mac == "00:00:00:00:00:00":
                continue

            result[ip] = mac

    except Exception as e:
        logger.error(f"ARP tablosu okuma hatasi: {e}")

    return result


async def resolve_placeholder_macs():
    """Placeholder MAC adresli cihazlarin gercek MAC'ini ARP tablosundan coz."""
    arp_table = read_host_arp_table()
    if not arp_table:
        return

    try:
        async with async_session_factory() as session:
            session.autoflush = False

            # Placeholder MAC'li cihazlari bul
            result = await session.execute(
                select(Device).where(
                    or_(
                        Device.mac_address.like("AA:00:%"),
                        Device.mac_address.like("DD:0T:%"),
                    )
                )
            )
            devices = list(result.scalars().all())

            if not devices:
                return

            resolved_count = 0
            hostname_updated = 0
            to_delete: list[int] = []

            for device in devices:
                ip = device.ip_address
                if not ip or ip not in arp_table:
                    continue

                # Silinecek cihazlari atla
                if device.id in to_delete:
                    continue

                real_mac = arp_table[ip]
                old_mac = device.mac_address

                # Ayni MAC ile zaten baska bir cihaz var mi kontrol et
                # (duplike onleme)
                existing_result = await session.execute(
                    select(Device).where(
                        Device.mac_address == real_mac,
                        Device.id != device.id,
                    )
                )
                existing_device = existing_result.scalar_one_or_none()

                if existing_device:
                    # Gercek MAC ile zaten baska bir kayit var
                    # Mevcut kaydi güncelle, placeholder'i sonra sil
                    if existing_device.ip_address != ip:
                        existing_device.ip_address = ip
                    # NOT: is_online ve last_seen burada GUNCELLENMEZ.
                    # Online/offline durumu sadece device_discovery.py yonetir.
                    to_delete.append(device.id)
                    logger.info(
                        f"Duplike cihaz tespit edildi: {old_mac} -> "
                        f"mevcut kayit {real_mac} ({ip}) kullanilacak"
                    )
                    resolved_count += 1
                    continue

                # MAC adresini güncelle
                device.mac_address = real_mac
                resolved_count += 1

                # OUI ile manufacturer lookup
                manufacturer = lookup_manufacturer(real_mac)
                if manufacturer:
                    device_type = detect_device_type(
                        device.hostname or "", manufacturer
                    )
                    if device_type:
                        device.manufacturer = f"{manufacturer} ({device_type})"
                    else:
                        device.manufacturer = manufacturer

                # Placeholder hostname'i iyilestir
                if device.hostname and device.hostname.startswith(
                    ("client-", "dot-", "dhcp-")
                ):
                    # Hostname cihazdaki pattern'lerden tespit edilebilir mi?
                    det_os, det_type = detect_device_from_hostname(
                        device.hostname
                    )
                    # Eger hala placeholder hostname ise, manufacturer bilgisiyle
                    # daha iyi bir hostname oluştur
                    if not det_os and manufacturer:
                        ip_short = ip.split(".")[-1]
                        new_hostname = f"{manufacturer}-{ip_short}"
                        device.hostname = new_hostname
                        hostname_updated += 1

                # Cihaz tipi tespiti (detected_os / device_type alanlari)
                if device.detected_os is None and device.hostname:
                    det_os, det_type = detect_device_from_hostname(
                        device.hostname
                    )
                    if det_os:
                        device.detected_os = det_os
                    if det_type:
                        device.device_type = det_type

                logger.info(
                    f"MAC cozumlendi: {old_mac} -> {real_mac} "
                    f"({ip}, {device.hostname}, {device.manufacturer})"
                )

            # Duplike cihazlari toplu sil (iliskileri transfer et)
            if to_delete:
                for del_id in to_delete:
                    # Placeholder cihazin IP'sinden gercek cihazi bul
                    del_dev_r = await session.execute(
                        select(Device).where(Device.id == del_id)
                    )
                    del_device = del_dev_r.scalar_one_or_none()
                    if not del_device:
                        continue

                    # Gercek MAC ile eşleşen cihazi bul (transfer hedefi)
                    real_mac = arp_table.get(del_device.ip_address)
                    if real_mac:
                        target_r = await session.execute(
                            select(Device).where(
                                Device.mac_address == real_mac,
                                Device.id != del_id,
                            )
                        )
                        target = target_r.scalar_one_or_none()
                        target_id = target.id if target else None
                    else:
                        target_id = None

                    # Iliskili kayitlari transfer et veya NULL yap
                    for model, fk_col in [
                        (DnsQueryLog, "device_id"),
                        (DeviceConnectionLog, "device_id"),
                        (TrafficLog, "device_id"),
                    ]:
                        await session.execute(
                            update(model)
                            .where(getattr(model, fk_col) == del_id)
                            .values(**{fk_col: target_id})
                        )

                    # Insight'larda related_device_id transfer
                    await session.execute(
                        update(AiInsight)
                        .where(AiInsight.related_device_id == del_id)
                        .values(related_device_id=target_id)
                    )

                    # Cihaz-servis eslesmelerini sil (unique constraint)
                    await session.execute(
                        select(DeviceBlockedService).where(
                            DeviceBlockedService.device_id == del_id
                        )
                    )
                    svc_result = await session.execute(
                        select(DeviceBlockedService).where(
                            DeviceBlockedService.device_id == del_id
                        )
                    )
                    for svc in svc_result.scalars().all():
                        await session.delete(svc)

                    # Cihaz özel DNS kurallarini sil
                    rule_result = await session.execute(
                        select(DeviceCustomRule).where(
                            DeviceCustomRule.device_id == del_id
                        )
                    )
                    for rule in rule_result.scalars().all():
                        await session.delete(rule)

                    # DHCP lease'leri güncelle
                    from app.models.dhcp_lease import DhcpLease
                    await session.execute(
                        update(DhcpLease)
                        .where(DhcpLease.device_id == del_id)
                        .values(device_id=target_id)
                    )

                    # Artik guvenle silinebilir
                    await session.delete(del_device)

                logger.info(f"MAC resolver: {len(to_delete)} duplike cihaz temizlendi")

            if resolved_count > 0 or hostname_updated > 0:
                await session.commit()
                logger.info(
                    f"MAC resolver: {resolved_count} MAC cozumlendi, "
                    f"{hostname_updated} hostname güncellendi"
                )

    except Exception as e:
        logger.error(f"MAC resolver hatasi: {e}")


async def start_mac_resolver_worker():
    """MAC resolver dongusu - periyodik placeholder MAC cozumleme."""
    logger.info("MAC resolver worker başlatildi")

    arp_file = _find_arp_file()
    if not arp_file:
        logger.warning(
            f"Host ARP tablosu bulunamadı: {HOST_ARP_PATHS}. "
            "MAC resolver devre disi."
        )
        return
    logger.info(f"ARP tablosu kaynak: {arp_file}")

    # Başlangicta hemen bir kere calistir
    await resolve_placeholder_macs()

    while True:
        await asyncio.sleep(RESOLVE_INTERVAL)
        try:
            await resolve_placeholder_macs()
        except Exception as e:
            logger.error(f"MAC resolver worker hatasi: {e}")

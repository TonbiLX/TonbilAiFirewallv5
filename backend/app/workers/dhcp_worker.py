# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DHCP Worker: dnsmasq lease dosyasini periyodik olarak okur,
# DB ile senkronize eder, device tablosuna lease bilgisi yazar.
# OUI lookup ile cihaz ureticisini tespit eder.

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.dhcp_lease import DhcpLease
from app.models.dhcp_pool import DhcpPool
from app.models.device import Device
from app.hal.linux_dhcp_driver import parse_leases_file, DNSMASQ_CONF_DIR

logger = logging.getLogger("tonbilai.dhcp_worker")

SYNC_INTERVAL = 30  # 30 saniyede bir lease sync

# --- Silinen MAC takibi ---
# API'den silinen lease MAC adresleri burada tutulur.
# Sync worker bu MAC'leri atlayarak tekrar oluşturmaz.
_deleted_macs: Dict[str, float] = {}  # mac -> silme zamani (unix timestamp)
_DELETION_TTL = 1800  # 30 dakika boyunca yeniden oluşturma (cihaz agdaysa yeni lease alir)


def mark_mac_deleted(mac: str):
    """Bir MAC adresini 'silinmis' olarak isaretle (API tarafindan cagirilir)."""
    _deleted_macs[mac.upper()] = time.time()
    logger.info(f"MAC silinmis olarak isaretlendi: {mac.upper()}")


def unmark_mac_deleted(mac: str):
    """Bir MAC adresinin silinmis isaretini kaldir."""
    _deleted_macs.pop(mac.upper(), None)


def is_mac_deleted(mac: str) -> bool:
    """MAC adresi son 24 saat içinde silinmis mi kontrol et."""
    ts = _deleted_macs.get(mac.upper())
    if ts is None:
        return False
    if time.time() - ts > _DELETION_TTL:
        _deleted_macs.pop(mac.upper(), None)
        return False
    return True


def _cleanup_expired_deletions():
    """Süresi dolmus silme isaretlerini temizle."""
    now = time.time()
    expired = [mac for mac, ts in _deleted_macs.items() if now - ts > _DELETION_TTL]
    for mac in expired:
        _deleted_macs.pop(mac, None)

# --- MAC OUI Veritabani (Bilinen Ureticiler) ---
# MAC adresinin ilk 3 byte'i (OUI) -> Uretici adi
OUI_DATABASE = {
    # TP-Link
    "A8:42:A1": "TP-Link",
    "EC:BE:5F": "TP-Link",
    "00:31:92": "TP-Link",
    "34:24:3E": "TP-Link",
    "30:DE:4B": "TP-Link",
    "50:C7:BF": "TP-Link",
    "B0:BE:76": "TP-Link",
    "98:DA:C4": "TP-Link",
    "60:32:B1": "TP-Link",
    "F4:F2:6D": "TP-Link",
    "AC:84:C6": "TP-Link",
    "D4:6E:0E": "TP-Link",
    "1C:3B:F3": "TP-Link",
    # Espressif (ESP8266/ESP32 IoT)
    "84:0D:8E": "Espressif",
    "D8:F1:5B": "Espressif",
    "2C:F4:32": "Espressif",
    "A4:CF:12": "Espressif",
    "80:7D:3A": "Espressif",
    "68:C6:3A": "Espressif",
    "24:0A:C4": "Espressif",
    "24:6F:28": "Espressif",
    "30:AE:A4": "Espressif",
    "3C:61:05": "Espressif",
    "3C:71:BF": "Espressif",
    "4C:EB:D6": "Espressif",
    "A0:20:A6": "Espressif",
    "AC:67:B2": "Espressif",
    "B4:E6:2D": "Espressif",
    "BC:DD:C2": "Espressif",
    "C4:4F:33": "Espressif",
    "CC:50:E3": "Espressif",
    "D8:A0:1D": "Espressif",
    "E0:98:06": "Espressif",
    "E8:DB:84": "Espressif",
    "F0:08:D1": "Espressif",
    "08:3A:F2": "Espressif",
    "08:B6:1F": "Espressif",
    "10:52:1C": "Espressif",
    "34:85:18": "Espressif",
    "48:3F:DA": "Espressif",
    "54:32:04": "Espressif",
    "70:04:1D": "Espressif",
    "7C:DF:A1": "Espressif",
    "94:B5:55": "Espressif",
    "94:B9:7E": "Espressif",
    "A0:76:4E": "Espressif",
    "C8:2B:96": "Espressif",
    "C8:C9:A3": "Espressif",
    "D8:BC:38": "Espressif",
    "DC:4F:22": "Espressif",
    "EC:94:CB": "Espressif",
    "FC:F5:C4": "Espressif",
    # Samsung
    "2C:99:75": "Samsung",
    "00:2B:70": "Samsung",
    "00:21:19": "Samsung",
    "00:26:37": "Samsung",
    "08:21:EF": "Samsung",
    "10:D5:42": "Samsung",
    "14:49:E0": "Samsung",
    "18:3A:2D": "Samsung",
    "1C:AF:05": "Samsung",
    "28:CC:01": "Samsung",
    "30:96:FB": "Samsung",
    "34:23:BA": "Samsung",
    "38:01:46": "Samsung",
    "40:4E:36": "Samsung",
    "50:01:BB": "Samsung",
    "50:B7:C3": "Samsung",
    "54:40:AD": "Samsung",
    "58:C3:8B": "Samsung",
    "5C:49:7D": "Samsung",
    "60:AF:6D": "Samsung",
    "6C:F3:73": "Samsung",
    "78:47:1D": "Samsung",
    "78:BD:BC": "Samsung",
    "84:25:DB": "Samsung",
    "84:38:35": "Samsung",
    "8C:77:12": "Samsung",
    "90:18:7C": "Samsung",
    "94:01:C2": "Samsung",
    "94:35:0A": "Samsung",
    "98:52:B1": "Samsung",
    "A0:82:1F": "Samsung",
    "A4:08:EA": "Samsung",
    "A8:7C:01": "Samsung",
    "B0:72:BF": "Samsung",
    "B4:3A:28": "Samsung",
    "BC:44:86": "Samsung",
    "C0:97:27": "Samsung",
    "C4:73:1E": "Samsung",
    "C8:14:79": "Samsung",
    "CC:07:AB": "Samsung",
    "D0:22:BE": "Samsung",
    "D0:87:E2": "Samsung",
    "D4:88:90": "Samsung",
    "D8:90:E8": "Samsung",
    "E4:7C:F9": "Samsung",
    "E8:50:8B": "Samsung",
    "F0:25:B7": "Samsung",
    "F4:42:8F": "Samsung",
    "FC:A8:9A": "Samsung",
    # Xiaomi
    "78:DF:72": "Xiaomi",
    "04:CF:8C": "Xiaomi",
    "0C:1D:AF": "Xiaomi",
    "10:2A:B3": "Xiaomi",
    "14:F6:5A": "Xiaomi",
    "18:59:36": "Xiaomi",
    "20:34:FB": "Xiaomi",
    "28:6C:07": "Xiaomi",
    "34:CE:00": "Xiaomi",
    "3C:BD:3E": "Xiaomi",
    "44:23:7C": "Xiaomi",
    "50:64:2B": "Xiaomi",
    "58:44:98": "Xiaomi",
    "64:09:80": "Xiaomi",
    "64:CC:2E": "Xiaomi",
    "68:AB:BC": "Xiaomi",
    "74:23:44": "Xiaomi",
    "7C:1C:68": "Xiaomi",
    "84:F3:EB": "Xiaomi",
    "8C:DE:F9": "Xiaomi",
    "98:FA:E3": "Xiaomi",
    "9C:99:A0": "Xiaomi",
    "A4:77:33": "Xiaomi",
    "AC:C1:EE": "Xiaomi",
    "B0:D5:9D": "Xiaomi",
    "C4:0B:CB": "Xiaomi",
    "D4:61:DA": "Xiaomi",
    "F0:B4:29": "Xiaomi",
    "F8:A4:5F": "Xiaomi",
    "FC:64:BA": "Xiaomi",
    # Raspberry Pi
    "2C:CF:67": "Raspberry Pi",
    "D8:3A:DD": "Raspberry Pi",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    # Apple
    "00:03:93": "Apple",
    "00:0A:95": "Apple",
    "00:0D:93": "Apple",
    "00:1C:B3": "Apple",
    "00:25:BC": "Apple",
    "04:0C:CE": "Apple",
    "14:99:E2": "Apple",
    "18:AF:8F": "Apple",
    "20:78:F0": "Apple",
    "28:6A:BA": "Apple",
    "34:36:3B": "Apple",
    "3C:22:FB": "Apple",
    "40:A6:D9": "Apple",
    "48:D7:05": "Apple",
    "54:4E:45": "Apple",
    "5C:F7:E6": "Apple",
    "68:AE:20": "Apple",
    "6C:70:9F": "Apple",
    "78:7B:8A": "Apple",
    "80:BE:05": "Apple",
    "8C:85:90": "Apple",
    "98:01:A7": "Apple",
    "A4:83:E7": "Apple",
    "AC:BC:32": "Apple",
    "B8:E8:56": "Apple",
    "C4:2A:D0": "Apple",
    "D0:03:4B": "Apple",
    "DC:A9:04": "Apple",
    "E4:CE:8F": "Apple",
    "F0:18:98": "Apple",
    "F4:5C:89": "Apple",
    # Huawei / Honor
    "00:9A:CD": "Huawei",
    "00:E0:FC": "Huawei",
    "04:B0:E7": "Huawei",
    "10:47:80": "Huawei",
    "20:A6:80": "Huawei",
    "24:09:95": "Huawei",
    "28:3C:E4": "Huawei",
    "34:12:98": "Huawei",
    "48:AD:08": "Huawei",
    "54:A5:1B": "Huawei",
    "5C:09:79": "Huawei",
    "70:8A:09": "Huawei",
    "80:D0:9B": "Huawei",
    "88:28:B3": "Huawei",
    "CC:A2:23": "Huawei",
    "E0:24:7F": "Huawei",
    "F4:C7:14": "Huawei",
    "F8:4A:BF": "Huawei",
    # Lenovo
    "A0:51:0B": "Lenovo",
    "00:09:2D": "Lenovo",
    "28:D2:44": "Lenovo",
    "54:E1:AD": "Lenovo",
    "6C:C2:17": "Lenovo",
    "98:FA:9B": "Lenovo",
    "C8:5B:76": "Lenovo",
    "E8:6A:64": "Lenovo",
    "F0:03:8C": "Lenovo",
    # Intel (Laptop WiFi)
    "00:1E:64": "Intel",
    "00:1F:3B": "Intel",
    "08:D4:0C": "Intel",
    "34:02:86": "Intel",
    "48:51:B7": "Intel",
    "5C:87:9C": "Intel",
    "68:17:29": "Intel",
    "7C:B2:7D": "Intel",
    "8C:8D:28": "Intel",
    "A4:34:D9": "Intel",
    "B4:6B:FC": "Intel",
    "D4:3B:04": "Intel",
    # LG
    "00:1C:62": "LG",
    "00:22:A9": "LG",
    "10:68:3F": "LG",
    "20:3D:BD": "LG",
    "34:4D:F7": "LG",
    "58:A2:B5": "LG",
    "A8:16:B2": "LG",
    "C4:36:6C": "LG",
    "CC:FA:00": "LG",
    # Google
    "3C:5A:B4": "Google",
    "54:60:09": "Google",
    "F4:F5:D8": "Google",
    "A4:77:33": "Google",
    # Amazon (Echo, Fire, etc.)
    "00:FC:8B": "Amazon",
    "0C:47:C9": "Amazon",
    "14:91:82": "Amazon",
    "34:D2:70": "Amazon",
    "44:65:0D": "Amazon",
    "68:54:FD": "Amazon",
    "74:C2:46": "Amazon",
    "A0:02:DC": "Amazon",
    "FC:65:DE": "Amazon",
}


def lookup_manufacturer(mac: str) -> str:
    """MAC adresinin OUI'sine göre uretici adi dondur."""
    if not mac or len(mac) < 8:
        return ""
    oui = mac[:8].upper()
    return OUI_DATABASE.get(oui, "")


def detect_device_type(hostname: str, manufacturer: str) -> str:
    """Hostname ve ureticiden cihaz tipi tahmin et."""
    h = (hostname or "").lower()
    m = (manufacturer or "").lower()

    # Hostname bazli tahminler
    if "deco" in h:
        return "WiFi Mesh AP"
    if h.startswith("esp_") or h.startswith("esp-"):
        return "IoT Cihaz"
    if "lamp" in h or "light" in h or "bulb" in h:
        return "Akilli Aydinlatma"
    if "cam" in h or "chuangmi" in h or "ipc" in h:
        return "IP Kamera"
    if "tv" in h or "samsung-led" in h or "smarttv" in h:
        return "Akilli TV"
    if "phone" in h or "iphone" in h or "galaxy" in h:
        return "Telefon"
    if "ipad" in h or "tab" in h:
        return "Tablet"
    if "macbook" in h or "laptop" in h or "lenovo" in h or "thinkpad" in h:
        return "Dizustu Bilgisayar"
    if "desktop" in h or "pc" in h:
        return "Masaustu Bilgisayar"
    if "echo" in h or "alexa" in h:
        return "Akilli Hoparlor"
    if "printer" in h or "print" in h:
        return "Yazici"
    if "switch" in h or "plug" in h or "socket" in h:
        return "Akilli Priz"
    if "vacuum" in h or "roborock" in h:
        return "Robot Supurge"
    if "android" in h:
        return "Android Cihaz"

    # Manufacturer bazli tahminler
    if "espressif" in m:
        return "IoT Cihaz"
    if "raspberry" in m:
        return "Mini Bilgisayar"
    if "tp-link" in m:
        return "Ag Cihazi"

    return ""


async def sync_leases_to_db():
    """dnsmasq lease dosyasindan okunan lease'leri DB ile senkronize et."""
    raw_leases = parse_leases_file()
    if not raw_leases:
        return

    try:
        async with async_session_factory() as session:
            session.autoflush = False

            # Mevcut pool'u bul (ilk aktif pool)
            pool_result = await session.execute(
                select(DhcpPool).where(DhcpPool.enabled == True).limit(1)  # noqa: E712
            )
            pool = pool_result.scalar_one_or_none()
            pool_id = pool.id if pool else None

            # Süresi dolmus silme isaretlerini temizle
            _cleanup_expired_deletions()

            # --- Expired lease temizligi: suresi dolan dinamik lease'leri DB'den sil ---
            expired_result = await session.execute(
                select(DhcpLease).where(
                    DhcpLease.lease_end.isnot(None),
                    DhcpLease.lease_end < datetime.utcnow(),
                    DhcpLease.is_static == False,  # noqa: E712
                )
            )
            expired_leases = expired_result.scalars().all()
            if expired_leases:
                for exp_lease in expired_leases:
                    await session.delete(exp_lease)
                logger.info(f"Expired lease temizligi: {len(expired_leases)} suresi dolan lease silindi")

            synced = 0
            for lease_data in raw_leases:
                if lease_data.get("is_expired"):
                    continue

                mac = lease_data["mac_address"]
                ip = lease_data["ip_address"]
                hostname = lease_data["hostname"]
                lease_end = lease_data.get("lease_end")

                # Kullanıcı tarafindan silinen lease'i yeniden oluşturma
                if is_mac_deleted(mac):
                    continue

                # --- LEASE TABLOSU SYNC ---
                # Once MAC ile ara
                result = await session.execute(
                    select(DhcpLease).where(DhcpLease.mac_address == mac)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.ip_address = ip
                    existing.hostname = hostname or existing.hostname
                    existing.lease_end = lease_end
                    existing.pool_id = pool_id
                else:
                    # MAC bulunamadı - IP ile ara (duplicate IP onleme)
                    ip_result = await session.execute(
                        select(DhcpLease).where(DhcpLease.ip_address == ip)
                    )
                    existing_by_ip = ip_result.scalar_one_or_none()

                    if existing_by_ip:
                        # Ayni IP farkli MAC - güncelle (cihaz degismis)
                        if not existing_by_ip.is_static:
                            existing_by_ip.mac_address = mac
                            existing_by_ip.hostname = hostname or existing_by_ip.hostname
                            existing_by_ip.lease_end = lease_end
                            existing_by_ip.pool_id = pool_id
                        # Statik lease ise dokunma
                    else:
                        # Tamamen yeni lease
                        new_lease = DhcpLease(
                            mac_address=mac,
                            ip_address=ip,
                            hostname=hostname or "",
                            lease_start=datetime.utcnow(),
                            lease_end=lease_end,
                            is_static=False,
                            pool_id=pool_id,
                        )
                        session.add(new_lease)
                        synced += 1

                # --- DEVICE TABLOSU SYNC ---
                # OUI lookup ile uretici bilgisi
                oui_manufacturer = lookup_manufacturer(mac)
                device_type = detect_device_type(hostname, oui_manufacturer)

                # Zenginlestirilmis manufacturer etiketi
                if oui_manufacturer and device_type:
                    rich_manufacturer = f"{oui_manufacturer} ({device_type})"
                elif oui_manufacturer:
                    rich_manufacturer = oui_manufacturer
                elif device_type:
                    rich_manufacturer = device_type
                else:
                    rich_manufacturer = "DHCP Kesfedildi"

                # Once gercek MAC ile ara
                dev_result = await session.execute(
                    select(Device).where(Device.mac_address == mac)
                )
                device = dev_result.scalar_one_or_none()

                if not device and ip:
                    # MAC ile bulunamadı - IP ile ara
                    # (DNS discovery placeholder MAC ile oluşturmus olabilir)
                    dev_result = await session.execute(
                        select(Device).where(Device.ip_address == ip)
                    )
                    device = dev_result.scalar_one_or_none()

                if device:
                    if device.mac_address != mac:
                        # DHCP lease farkli MAC gosteriyor — IP baska cihaza atanmis
                        if device.mac_address.startswith(("AA:00:", "DD:0T:")):
                            # Placeholder MAC → gercek DHCP MAC ile degistir
                            logger.info(
                                f"Cihaz MAC güncellendi (placeholder): "
                                f"{device.mac_address} -> {mac} (IP: {ip})"
                            )
                            device.mac_address = mac
                        else:
                            # Gercek MAC uyumsuzlugu — eski cihazi bu IP'den ayir
                            logger.warning(
                                f"DHCP MAC uyumsuzlugu: IP {ip} device "
                                f"{device.mac_address} ({device.hostname}), "
                                f"DHCP MAC {mac}. Eski cihaz IP'den ayrildi."
                            )
                            device.ip_address = None
                            device.is_online = False
                            # Yeni MAC icin yeni device olustur
                            new_device = Device(
                                mac_address=mac,
                                ip_address=ip,
                                hostname=hostname or f"dhcp-{ip}",
                                manufacturer=rich_manufacturer,
                                is_blocked=False,
                                is_online=False,
                                first_seen=datetime.now(),
                                last_seen=datetime.now(),
                            )
                            session.add(new_device)
                            # Bu lease icin islem tamam, sonrakine gec
                            continue
                    else:
                        # MAC eslesiyor — IP degistiyse güncelle
                        if device.ip_address != ip:
                            device.ip_address = ip
                    # NOT: is_online ve last_seen burada GUNCELLENMEZ.
                    # Online/offline durumu sadece device_discovery.py
                    # tarafindan ip neigh + ping ile yonetilir.
                    # DHCP lease'in var olmasi cihazin agda oldugu anlamina gelmez.
                    # Placeholder hostname'i DHCP hostname ile güncelle
                    if hostname and device.hostname and device.hostname.startswith(
                        ("client-", "dot-", "dhcp-")
                    ):
                        device.hostname = hostname
                    # Manufacturer etiketini zenginlestir
                    if device.manufacturer in (
                        "Otomatik Kesfedildi",
                        "DoT (Private DNS)",
                        "DHCP Kesfedildi",
                    ):
                        device.manufacturer = rich_manufacturer
                elif ip:
                    # Ne MAC ne IP ile bulundu - tamamen yeni cihaz
                    new_device = Device(
                        mac_address=mac,
                        ip_address=ip,
                        hostname=hostname or f"dhcp-{ip}",
                        manufacturer=rich_manufacturer,
                        is_blocked=False,
                        is_online=True,
                        first_seen=datetime.now(),
                        last_seen=datetime.now(),
                    )
                    session.add(new_device)

            await session.commit()
            if synced > 0:
                logger.info(f"DHCP lease sync: {synced} yeni lease eklendi")

    except Exception as e:
        logger.error(f"DHCP lease sync hatasi: {e}")


async def start_dhcp_worker():
    """DHCP worker dongusu - periyodik lease senkronizasyonu."""
    logger.info("DHCP worker başlatildi")

    # Config dizini var mi kontrol et
    if not DNSMASQ_CONF_DIR.exists():
        logger.warning(
            f"dnsmasq config dizini bulunamadı: {DNSMASQ_CONF_DIR}. "
            "DHCP fonksiyonlari devre disi."
        )
        return

    while True:
        await asyncio.sleep(SYNC_INTERVAL)
        try:
            await sync_leases_to_db()
        except Exception as e:
            logger.error(f"DHCP worker hatasi: {e}")

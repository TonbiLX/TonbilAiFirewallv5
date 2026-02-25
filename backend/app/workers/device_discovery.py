# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Otomatik Cihaz Kesfi: DNS sorgularindan gelen IP adreslerini
# izleyerek yeni cihazlari otomatik kaydeder.
# Hostname pattern'inden cihaz tipi ve OS otomatik tespit eder.
# Redis'e IP->device_id cache yazar (servis engelleme için gerekli).

import asyncio
import logging
import re
import socket
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select, or_

from app.db.session import async_session_factory
from app.db.redis_client import get_redis
from app.models.device import Device
from app.models.device_connection_log import DeviceConnectionLog
from app.services.telegram_service import notify_new_device

logger = logging.getLogger("tonbilai.device_discovery")

# Güncelleme onbellegi - ayni IP için surekli DB sorgusu yapmamak için
_known_ips: dict[str, datetime] = {}
_UPDATE_INTERVAL = 30  # 30 saniyede bir güncelle
_FAILED_IPS: dict[str, int] = {}  # Hata sayacı - başarısız IP'ler için
_MAX_RETRIES = 3

# Hostname cozumleme için thread pool (timeout desteği ile)
_hostname_executor = ThreadPoolExecutor(max_workers=2)

# Gateway (modem/router) IP cache — cihaz olarak kaydedilmemeli
_gateway_ip_cache: str = ""
_gateway_ip_cache_time: float = 0


def _get_gateway_ip() -> str:
    """Default gateway IP adresini `ip route` komutundan oku.
    5 dakika boyunca cache'ler. Gateway, cihaz olarak izlenmemeli."""
    global _gateway_ip_cache, _gateway_ip_cache_time
    import time as _time
    now = _time.monotonic()
    if _gateway_ip_cache and (now - _gateway_ip_cache_time) < 300:
        return _gateway_ip_cache
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5,
        )
        for part in result.stdout.split():
            if part.count(".") == 3:
                _gateway_ip_cache = part
                _gateway_ip_cache_time = now
                return part
    except Exception:
        pass
    return _gateway_ip_cache or "192.168.1.1"


# --- Hostname-Tabanli Cihaz Tipi Tespiti ---
# (detected_os, device_type) dondurecek kurallar
HOSTNAME_RULES: list[tuple[re.Pattern, str | None, str]] = [
    # Apple
    (re.compile(r"(?i)iphone"), "iOS", "phone"),
    (re.compile(r"(?i)ipad"), "iPadOS", "tablet"),
    (re.compile(r"(?i)apple.?watch|iwatch"), "watchOS", "wearable"),
    (re.compile(r"(?i)apple.?tv"), "tvOS", "tv"),
    (re.compile(r"(?i)macbook|imac|mac.?pro|mac.?mini|mac.?studio"), "macOS", "computer"),

    # Samsung TV (Samsung phone'dan ONCE olmali)
    (re.compile(r"(?i)samsung.*led|samsung.*tv|samsung.*uhd|tizen"), "Tizen", "tv"),

    # Android / Samsung
    (re.compile(r"(?i)galaxy|SM-[A-Z]\d{3}|samsung(?!.*(?:led|tv|uhd))"), "Android (Samsung)", "phone"),
    (re.compile(r"(?i)pixel|nexus"), "Android (Google)", "phone"),
    (re.compile(r"(?i)huawei|honor|HUAWEI"), "Android (Huawei)", "phone"),
    (re.compile(r"(?i)xiaomi|redmi|poco|POCO"), "Android (Xiaomi)", "phone"),
    (re.compile(r"(?i)oppo|realme|oneplus"), "Android (OPPO)", "phone"),
    (re.compile(r"(?i)android"), "Android", "phone"),

    # TV / Streaming
    (re.compile(r"(?i)tizen|samsung.?tv|smart.?tv"), "Tizen", "tv"),
    (re.compile(r"(?i)LG.?TV|webOS|LG.?Smart"), "webOS", "tv"),
    (re.compile(r"(?i)roku"), "Roku OS", "tv"),
    (re.compile(r"(?i)fire.?tv|fire.?stick|AFTM"), "Fire OS", "tv"),
    (re.compile(r"(?i)chromecast|google.?tv"), "Android TV", "tv"),
    (re.compile(r"(?i)sony.?bravia"), "Android TV", "tv"),

    # Oyun Konsollari
    (re.compile(r"(?i)playstation|PS[345]"), "PlayStation", "console"),
    (re.compile(r"(?i)xbox"), "Xbox", "console"),
    (re.compile(r"(?i)nintendo|switch"), "Nintendo", "console"),

    # PC / Laptop
    (re.compile(r"(?i)windows|DESKTOP-|WIN-|LAPTOP-"), "Windows", "computer"),
    (re.compile(r"(?i)ubuntu|debian|fedora|arch|linux|raspberrypi"), "Linux", "computer"),

    # IoT
    (re.compile(r"(?i)^ESP[_-]|espressif|ESP32|ESP8266"), "ESP-IDF", "iot"),
    (re.compile(r"(?i)tasmota|sonoff"), "Tasmota", "iot"),
    (re.compile(r"(?i)shelly"), "Shelly", "iot"),
    (re.compile(r"(?i)tuya|smart.?life"), "Tuya", "iot"),
    (re.compile(r"(?i)hue.?bridge|philips.?hue"), "Philips Hue", "iot"),

    # Kameralar
    (re.compile(r"(?i)IPC[-_]|camera|cam[-_]|hikvision|dahua|reolink|EWLK"), None, "camera"),

    # Ag Cihazlari
    (re.compile(r"(?i)deco|tp.?link|tplink"), "TP-Link", "network_device"),
    (re.compile(r"(?i)unifi|ubiquiti"), "Ubiquiti", "network_device"),
    (re.compile(r"(?i)mikrotik"), "RouterOS", "network_device"),

    # Yazicilar
    (re.compile(r"(?i)printer|epson|canon|brother|HP.?LaserJet|HP.?DeskJet"), None, "printer"),
]


def detect_device_from_hostname(hostname: str) -> tuple[str | None, str | None]:
    """Hostname'den cihaz tipi ve OS tespit et.
    Returns: (detected_os, device_type) veya (None, None)
    """
    if not hostname:
        return None, None

    for pattern, detected_os, device_type in HOSTNAME_RULES:
        if pattern.search(hostname):
            return detected_os, device_type

    return None, None


def _resolve_hostname_with_timeout(ip: str, timeout: float = 2.0) -> str:
    """Reverse DNS ile hostname cozumleme (timeout destekli)."""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except (socket.herror, socket.gaierror, OSError, socket.timeout):
        return ""
    finally:
        socket.setdefaulttimeout(old_timeout)


def _read_mac_from_arp(ip: str) -> str:
    """ARP tablosundan (/proc/net/arp) verilen IP'nin gercek MAC adresini oku.
    Bulunamazsa bos string dondurur."""
    arp_path = Path("/proc/net/arp")
    if not arp_path.exists():
        return ""
    try:
        content = arp_path.read_text()
        for line in content.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            arp_ip = parts[0]
            flags = parts[2]
            mac = parts[3].upper()
            interface = parts[5]
            # Sadece reachable ve bilinen arayuzler
            if arp_ip == ip and flags == "0x2" and interface in ("br0", "end0", "eth0", "eth1", "wlan0"):
                if mac != "00:00:00:00:00:00":
                    return mac
    except Exception:
        pass
    return ""


def _read_hostname_from_dhcp_leases(ip: str) -> tuple[str, str]:
    """dnsmasq lease dosyasindan verilen IP'nin hostname ve MAC'ini oku.
    Returns: (hostname, mac) - bulunamazsa ("", "")"""
    lease_path = Path("/var/lib/misc/dnsmasq.leases")
    if not lease_path.exists():
        return "", ""
    try:
        content = lease_path.read_text()
        for line in content.strip().split("\n"):
            parts = line.split()
            if len(parts) < 4:
                continue
            # Format: expire_time mac ip hostname client_id
            lease_mac = parts[1].upper()
            lease_ip = parts[2]
            lease_hostname = parts[3] if parts[3] != "*" else ""
            if lease_ip == ip:
                return lease_hostname, lease_mac
    except Exception:
        pass
    return "", ""


def _is_docker_ip(ip: str) -> bool:
    """Docker ag IP'si mi kontrol et (172.16-31.x.x aralığı)."""
    if not ip:
        return False
    if ip.startswith("172."):
        try:
            second_octet = int(ip.split(".")[1])
            if 16 <= second_octet <= 31:
                return True
        except (ValueError, IndexError):
            pass
    return False


def _is_discoverable_ip(ip: str) -> bool:
    """Kesfedilebilir IP mi kontrol et. Sadece RFC1918 özel IP'leri kabul et.
    Docker ag IP'leri (172.16-31.x) filtrelenir."""
    if not ip:
        return False
    if _is_docker_ip(ip):
        return False
    if ip.startswith("192.168."):
        return True
    if ip.startswith("10."):
        return True
    return False


def _is_locally_administered_mac(mac: str) -> bool:
    """MAC adresinin locally administered (randomize) olup olmadigini kontrol et.
    Modern telefonlar (Samsung, iPhone vb.) WiFi bağlantısinda rastgele MAC kullanir.
    Locally administered MAC: ilk oktetin bit 1'i set edilmis (x2:, x6:, xA:, xE:)."""
    if not mac or len(mac) < 2:
        return False
    try:
        first_octet = int(mac[:2], 16)
        return bool(first_octet & 0x02)
    except ValueError:
        return False


def _get_arp_active_ips() -> tuple[set, set]:
    """ip neigh show ile aktif cihazlari tespit et.
    Returns: (reachable_ips, stale_ips)
    - reachable_ips: Kesinlikle agda (REACHABLE/DELAY/PROBE)
    - stale_ips: Belirsiz, ping ile dogrulanmali (STALE)
    """
    reachable_ips = set()
    stale_ips = set()
    try:
        result = subprocess.run(
            ["ip", "neigh", "show", "dev", "br0"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return reachable_ips, stale_ips
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) < 1:
                continue
            ip = parts[0]
            # Son kelime durumu gosterir: REACHABLE, STALE, DELAY, PROBE, FAILED, INCOMPLETE
            state = parts[-1].upper()
            if state in ("REACHABLE", "DELAY", "PROBE"):
                reachable_ips.add(ip)
            elif state == "STALE":
                stale_ips.add(ip)
            # FAILED, INCOMPLETE, NONE → her iki sete de eklenmez
    except Exception:
        pass
    return reachable_ips, stale_ips


def _ping_check(ip: str, timeout: int = 1) -> bool:
    """Tek ping ile cihazin agda olup olmadigini dogrula."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), ip],
            capture_output=True, timeout=timeout + 2,
        )
        return result.returncode == 0
    except Exception:
        return False


async def discover_device(client_ip: str, is_dot: bool = False):
    """DNS sorgusu yapan bir IP adresini cihaz olarak kaydet/güncelle.
    Ayrica Redis'e IP->device_id cache yazar.

    NOT: DoT sunuculari (Google, Cloudflare vb.) artik cihaz olarak
    kaydedilmiyor. Sadece yerel ag cihazlari kaydedilir.
    """
    # Docker IP'lerini her durumda filtrele
    if _is_docker_ip(client_ip):
        return

    # SADECE private (yerel ag) IP'leri cihaz olarak kaydet
    # DoT sunuculari ve dis IP'ler cihaz DEGILDIR
    if not _is_discoverable_ip(client_ip):
        return

    # Gateway (modem) IP'sini filtrele — ag gecidi cihaz olarak izlenmemeli
    if client_ip == _get_gateway_ip():
        return

    now = datetime.now()

    # Onbellekten kontrol - sik güncellemeyi onle
    last_update = _known_ips.get(client_ip)
    if last_update and (now - last_update).total_seconds() < _UPDATE_INTERVAL:
        return

    # Cok fazla hata almis IP'leri atla (ama periyodik olarak tekrar dene)
    fail_count = _FAILED_IPS.get(client_ip, 0)
    if fail_count >= _MAX_RETRIES:
        # Her 5 dakikada bir tekrar dene
        if last_update and (now - last_update).total_seconds() < 300:
            return
        _FAILED_IPS[client_ip] = 0  # Sayacı sıfırla

    # Race condition onlemi: cache'i HEMEN güncelle (DB işleminden once)
    _known_ips[client_ip] = now

    try:
        async with async_session_factory() as session:
            # Once IP ile cihaz ara
            result = await session.execute(
                select(Device).where(Device.ip_address == client_ip)
            )
            device = result.scalar_one_or_none()

            if device:
                # Mevcut cihaz - MAC dogrulamasi yap (IP baska cihaza atanmis olabilir)
                real_mac_check = ""
                if _is_discoverable_ip(client_ip):
                    loop_check = asyncio.get_event_loop()
                    real_mac_check = await loop_check.run_in_executor(
                        _hostname_executor, _read_mac_from_arp, client_ip
                    )

                if real_mac_check and real_mac_check != device.mac_address:
                    # IP baska bir cihaza atanmis! Eski cihazi bu IP'den ayir.
                    logger.warning(
                        f"MAC uyumsuzlugu: IP {client_ip} device kaydi "
                        f"{device.mac_address} ({device.hostname}), "
                        f"ARP gercek MAC {real_mac_check}. Eski cihaz ayrildi."
                    )
                    device.ip_address = None
                    device.is_online = False
                    if device.last_online_start:
                        session_seconds = int(
                            (now - device.last_online_start).total_seconds()
                        )
                        device.total_online_seconds = (
                            device.total_online_seconds or 0
                        ) + session_seconds
                        device.last_online_start = None
                    await session.commit()

                    # Yeni MAC ile mevcut device var mi? (IP degismis olabilir)
                    existing_new = await session.execute(
                        select(Device).where(Device.mac_address == real_mac_check)
                    )
                    device_new = existing_new.scalar_one_or_none()
                    if device_new:
                        # Bu MAC zaten baska bir device kaydinda — IP guncelle
                        device_new.ip_address = client_ip
                        device_new.last_seen = now
                        device_new.is_online = True
                        if not device_new.is_online:
                            device_new.last_online_start = now
                        # DHCP hostname al
                        dhcp_hn, _ = await asyncio.get_event_loop().run_in_executor(
                            _hostname_executor,
                            _read_hostname_from_dhcp_leases,
                            client_ip,
                        )
                        if dhcp_hn and device_new.hostname and \
                                device_new.hostname.startswith(("client-", "dot-", "dhcp-")):
                            device_new.hostname = dhcp_hn
                        await session.commit()
                        try:
                            redis_client = await get_redis()
                            await redis_client.set(
                                f"dns:ip_to_device:{client_ip}",
                                str(device_new.id), ex=600,
                            )
                        except Exception:
                            pass
                        _known_ips[client_ip] = now
                        _FAILED_IPS.pop(client_ip, None)
                        return
                    else:
                        # Yeni MAC icin device yok — device=None birak,
                        # asagidaki "yeni cihaz" blogu olusturacak
                        device = None
                else:
                    # MAC eslesiyor veya ARP okunamadi — mevcut davranis
                    was_offline = not device.is_online
                    device.last_seen = now
                    device.is_online = True

                    # Hostname degistiyse cihaz tipini tekrar kontrol et
                    if device.detected_os is None and device.hostname:
                        det_os, det_type = detect_device_from_hostname(device.hostname)
                        if det_os:
                            device.detected_os = det_os
                        if det_type:
                            device.device_type = det_type

                    # Eger offline'dan geliyorsa bağlantı logu yaz
                    if was_offline:
                        device.last_online_start = now
                        conn_log = DeviceConnectionLog(
                            device_id=device.id,
                            event_type="connect",
                            ip_address=client_ip,
                        )
                        session.add(conn_log)

            if not device:
                # Yeni cihaz kesfedildi!
                # 1) ONCE ARP tablosundan gercek MAC'i al (cihaz az once DNS
                #    sorgusu yapti, ARP tablosunda olmali)
                real_mac = ""
                dhcp_hostname = ""
                dhcp_mac = ""

                if _is_discoverable_ip(client_ip):
                    # ARP tablosundan MAC oku
                    loop_arp = asyncio.get_event_loop()
                    real_mac = await loop_arp.run_in_executor(
                        _hostname_executor, _read_mac_from_arp, client_ip
                    )

                    # DHCP lease dosyasindan hostname + MAC oku
                    dhcp_hostname, dhcp_mac = await loop_arp.run_in_executor(
                        _hostname_executor,
                        _read_hostname_from_dhcp_leases,
                        client_ip,
                    )

                    # ARP bos ama DHCP'de MAC varsa onu kullan
                    if not real_mac and dhcp_mac:
                        real_mac = dhcp_mac

                # 2) Gercek MAC bulunduysa, bu MAC ile mevcut cihaz var mi kontrol et
                #    (IP degismis olabilir - duplike onleme)
                if real_mac:
                    existing_by_mac = await session.execute(
                        select(Device).where(Device.mac_address == real_mac)
                    )
                    device_by_mac = existing_by_mac.scalar_one_or_none()
                    if device_by_mac:
                        # Bu MAC ile zaten bir cihaz var - IP'sini güncelle
                        was_offline = not device_by_mac.is_online
                        device_by_mac.ip_address = client_ip
                        device_by_mac.last_seen = now
                        device_by_mac.is_online = True
                        if was_offline:
                            device_by_mac.last_online_start = now
                            conn_log = DeviceConnectionLog(
                                device_id=device_by_mac.id,
                                event_type="connect",
                                ip_address=client_ip,
                            )
                            session.add(conn_log)
                        # DHCP hostname ile placeholder hostname'i güncelle
                        if dhcp_hostname and device_by_mac.hostname and \
                                device_by_mac.hostname.startswith(("client-", "dot-", "dhcp-")):
                            device_by_mac.hostname = dhcp_hostname
                        await session.commit()
                        try:
                            redis_client = await get_redis()
                            await redis_client.set(
                                f"dns:ip_to_device:{client_ip}",
                                str(device_by_mac.id),
                                ex=600,
                            )
                        except Exception:
                            pass
                        _known_ips[client_ip] = now
                        _FAILED_IPS.pop(client_ip, None)
                        return

                # 3) Hostname cozumleme (reverse DNS + DHCP)
                loop = asyncio.get_event_loop()
                try:
                    hostname = await asyncio.wait_for(
                        loop.run_in_executor(
                            _hostname_executor,
                            _resolve_hostname_with_timeout,
                            client_ip,
                        ),
                        timeout=3.0,
                    )
                except (asyncio.TimeoutError, Exception):
                    hostname = ""

                # DHCP hostname öncelikli (daha guvenilir)
                if dhcp_hostname:
                    hostname = dhcp_hostname

                # 3.5) MAC Randomization Birlestirme
                # Ayni hostname'e sahip mevcut cihaz varsa VE yeni MAC randomize ise,
                # yeni kayit oluşturmak yerine mevcut kaydi güncelle.
                # Bu sayede Samsung, iPhone vb. cihazlarin WiFi Private Address
                # özelligi yuzunden olusacak kopya kayitlar onlenir.
                merge_hostname = hostname or dhcp_hostname
                if merge_hostname and not merge_hostname.startswith(("client-", "dot-", "dhcp-")):
                    existing_by_hostname = await session.execute(
                        select(Device).where(
                            Device.hostname == merge_hostname,
                            Device.ip_address.like("192.168.%"),
                        )
                    )
                    hostname_matches = existing_by_hostname.scalars().all()
                    if hostname_matches and real_mac and _is_locally_administered_mac(real_mac):
                        # Randomize MAC ile ayni hostname -> mevcut cihazi güncelle
                        target_device = hostname_matches[0]
                        old_mac = target_device.mac_address
                        was_offline = not target_device.is_online

                        # MAC adresini güncelle (yeni randomize MAC)
                        target_device.mac_address = real_mac
                        target_device.ip_address = client_ip
                        target_device.last_seen = now
                        target_device.is_online = True

                        if was_offline:
                            target_device.last_online_start = now
                            conn_log = DeviceConnectionLog(
                                device_id=target_device.id,
                                event_type="connect",
                                ip_address=client_ip,
                            )
                            session.add(conn_log)

                        await session.commit()
                        logger.info(
                            f"MAC randomization birlestirme: {merge_hostname} "
                            f"({old_mac} -> {real_mac}, IP: {client_ip})"
                        )
                        try:
                            redis_client = await get_redis()
                            await redis_client.set(
                                f"dns:ip_to_device:{client_ip}",
                                str(target_device.id),
                                ex=600,
                            )
                        except Exception:
                            pass
                        _known_ips[client_ip] = now
                        _FAILED_IPS.pop(client_ip, None)
                        return

                # 4) MAC adresi belirle
                if real_mac:
                    # Gercek MAC bulundu - OUI ile manufacturer belirle
                    from app.workers.dhcp_worker import lookup_manufacturer, detect_device_type
                    oui_manufacturer = lookup_manufacturer(real_mac)
                    device_type_label = detect_device_type(hostname or "", oui_manufacturer)
                    if oui_manufacturer and device_type_label:
                        device_manufacturer = f"{oui_manufacturer} ({device_type_label})"
                    elif oui_manufacturer:
                        device_manufacturer = oui_manufacturer
                    else:
                        device_manufacturer = "Otomatik Kesfedildi"
                    final_mac = real_mac
                    device_hostname = hostname or f"client-{client_ip}"
                else:
                    # Son care: sentetik MAC (ARP ve DHCP'de bulunamadı)
                    ip_parts = client_ip.split(".")
                    final_mac = "AA:00:{:02X}:{:02X}:{:02X}:{:02X}".format(
                        *[int(p) % 256 for p in (ip_parts + ["0", "0", "0", "0"])[:4]]
                    )
                    device_hostname = hostname or f"client-{client_ip}"
                    device_manufacturer = "Otomatik Kesfedildi"

                # Hostname'den cihaz tipi tespit et
                det_os, det_type = detect_device_from_hostname(device_hostname)

                device = Device(
                    mac_address=final_mac,
                    ip_address=client_ip,
                    hostname=device_hostname,
                    manufacturer=device_manufacturer,
                    is_blocked=False,
                    is_online=True,
                    first_seen=now,
                    last_seen=now,
                    detected_os=det_os,
                    device_type=det_type,
                )
                session.add(device)
                await session.flush()

                # Bağlantı logu kaydet
                conn_log = DeviceConnectionLog(
                    device_id=device.id,
                    event_type="connect",
                    ip_address=client_ip,
                )
                session.add(conn_log)

                # Online sure takibi başlat
                device.last_online_start = now

                logger.info(
                    f"Yeni cihaz kesfedildi: {client_ip} "
                    f"(hostname: {device_hostname}, "
                    f"OS: {det_os or '-'}, tip: {det_type or '-'})"
                )

                # Commit ONCE telegram bildirimi - cihaz DB'de var olsun
                await session.commit()

                # Telegram bildirimi gönder (await ile - fire-and-forget degil)
                try:
                    await notify_new_device(
                        ip=client_ip,
                        hostname=device_hostname,
                        manufacturer=device_manufacturer,
                        device_type=det_type,
                        detected_os=det_os,
                    )
                except Exception as e:
                    logger.warning(f"Telegram yeni cihaz bildirimi gönderilemedi: {e}")

                # Commit zaten yapildi, ikinci commit gereksiz ama session context'i için
                # Redis cache'e ekle
                try:
                    redis_client = await get_redis()
                    await redis_client.set(
                        f"dns:ip_to_device:{client_ip}",
                        str(device.id),
                        ex=600,
                    )
                except Exception as e:
                    logger.debug(f"Redis IP cache hatasi: {e}")

                # Başarılı - cache'e ekle
                _known_ips[client_ip] = now
                _FAILED_IPS.pop(client_ip, None)
                return  # Yeni cihaz için erken donus (commit zaten yapildi)

            await session.commit()

            # Başarılı - device_id'yi Redis'e cache'le
            try:
                redis_client = await get_redis()
                await redis_client.set(
                    f"dns:ip_to_device:{client_ip}",
                    str(device.id),
                    ex=600,
                )
            except Exception as e:
                logger.debug(f"Redis IP cache hatasi: {e}")

        # Başarılı - cache'e ekle
        _known_ips[client_ip] = now
        _FAILED_IPS.pop(client_ip, None)

    except Exception as e:
        # Hata - cache'e EKLEME, bir sonraki sorguda tekrar dene
        _FAILED_IPS[client_ip] = _FAILED_IPS.get(client_ip, 0) + 1
        logger.error(f"Cihaz kesfi hatasi ({client_ip}): {e}")


async def update_existing_devices_fingerprint():
    """Mevcut cihazlarin hostname'lerinden cihaz tipini tespit et (toplu güncelleme).
    Başlangicta bir kere çalışır - detected_os/device_type NULL olan cihazlari günceller.
    """
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Device).where(
                    Device.detected_os.is_(None),
                    Device.hostname.isnot(None),
                )
            )
            devices = result.scalars().all()
            updated = 0
            for device in devices:
                det_os, det_type = detect_device_from_hostname(device.hostname or "")
                if det_os or det_type:
                    if det_os:
                        device.detected_os = det_os
                    if det_type:
                        device.device_type = det_type
                    updated += 1

            if updated:
                await session.commit()
                logger.info(f"Hostname-tabanli fingerprint: {updated} cihaz güncellendi.")
    except Exception as e:
        logger.error(f"Toplu fingerprint güncelleme hatasi: {e}")


async def mark_offline_devices():
    """Son 5 dakikada DNS sorgusu yapmayan cihazlari offline yap.
    ip neigh show ile gercek erisim durumu dogrulanir:
    - REACHABLE/DELAY/PROBE → online tut
    - STALE → ping ile dogrula, basarisiz ise offline yap
    - FAILED/yok → offline yap
    Ayrica offline olan ama REACHABLE gorunen cihazlari tekrar online yapar."""
    try:
        threshold = datetime.now() - timedelta(minutes=5)

        # ip neigh show ile aktif ve belirsiz cihazlari oku
        loop = asyncio.get_event_loop()
        reachable_ips, stale_ips = await loop.run_in_executor(
            _hostname_executor, _get_arp_active_ips
        )

        # Gateway IP'sini ARP setlerinden cikar
        gw_ip = _get_gateway_ip()
        reachable_ips.discard(gw_ip)
        stale_ips.discard(gw_ip)

        async with async_session_factory() as session:
            # --- 1. Online ama sessiz cihazlari kontrol et ---
            result = await session.execute(
                select(Device).where(
                    Device.is_online == True,  # noqa: E712
                    Device.last_seen < threshold,
                )
            )
            stale_devices = result.scalars().all()
            offline_devices = []
            kept_online = 0

            for device in stale_devices:
                ip = device.ip_address
                if not ip:
                    device.is_online = False
                    offline_devices.append(device)
                    continue

                # REACHABLE → kesinlikle agda, online tut
                if ip in reachable_ips:
                    device.last_seen = datetime.now()
                    kept_online += 1
                    continue

                # STALE → belirsiz, ping ile dogrula
                if ip in stale_ips:
                    is_alive = await loop.run_in_executor(
                        _hostname_executor, _ping_check, ip
                    )
                    if is_alive:
                        device.last_seen = datetime.now()
                        kept_online += 1
                        continue

                # FAILED / yok / ping basarisiz → offline yap
                device.is_online = False
                offline_devices.append(device)

                # Online sure hesapla ve kaydet
                if device.last_online_start:
                    session_seconds = int(
                        (datetime.now() - device.last_online_start).total_seconds()
                    )
                    device.total_online_seconds = (
                        device.total_online_seconds or 0
                    ) + session_seconds
                    device.last_online_start = None

                    # Disconnect logu kaydet
                    conn_log = DeviceConnectionLog(
                        device_id=device.id,
                        event_type="disconnect",
                        ip_address=ip,
                        session_duration_seconds=session_seconds,
                    )
                    session.add(conn_log)

            if offline_devices:
                logger.info(
                    f"{len(offline_devices)} cihaz offline olarak isaretlendi."
                )
            if kept_online > 0:
                logger.debug(
                    f"{kept_online} cihaz agda dogrulandi, online tutuldu."
                )

            # Once mevcut degisiklikleri kaydet (autoflush sorunu onleme)
            await session.commit()

        # --- 2. Offline ama REACHABLE/STALE cihazlari tekrar online yap ---
        # MAC dogrulamasi: ARP'deki MAC, device kaydindaki MAC ile eslesmeli
        # STALE IP'ler icin ping dogrulamasi yapilir
        revive_candidate_ips = reachable_ips | stale_ips
        if revive_candidate_ips:
            async with async_session_factory() as session2:
                offline_result = await session2.execute(
                    select(Device).where(
                        Device.is_online == False,  # noqa: E712
                        Device.ip_address.in_(revive_candidate_ips),
                    )
                )
                revived_devices = offline_result.scalars().all()
                revived_count = 0
                for device in revived_devices:
                    # STALE IP ise ping ile dogrula
                    if device.ip_address in stale_ips and device.ip_address not in reachable_ips:
                        is_alive = await loop.run_in_executor(
                            _hostname_executor, _ping_check, device.ip_address
                        )
                        if not is_alive:
                            continue  # Ping basarisiz - online yapma

                    # ARP'deki gercek MAC'i kontrol et
                    arp_mac = await loop.run_in_executor(
                        _hostname_executor, _read_mac_from_arp, device.ip_address
                    )
                    if arp_mac and arp_mac != device.mac_address:
                        # Baska bir cihaz bu IP'de — online yapMA
                        logger.info(
                            f"Revive engellendi: {device.ip_address} device MAC "
                            f"{device.mac_address}, ARP MAC {arp_mac}. "
                            f"IP baska cihaza ait."
                        )
                        device.ip_address = None  # IP artik bu cihazin degil
                        continue

                    now = datetime.now()
                    device.is_online = True
                    device.last_seen = now
                    device.last_online_start = now
                    conn_log = DeviceConnectionLog(
                        device_id=device.id,
                        event_type="connect",
                        ip_address=device.ip_address,
                    )
                    session2.add(conn_log)
                    revived_count += 1
                if revived_count:
                    logger.info(
                        f"{revived_count} offline cihaz agda tespit edildi, "
                        f"tekrar online yapildi."
                    )
                await session2.commit()
    except Exception as e:
        logger.error(f"Offline isaretleme hatasi: {e}")


async def _active_network_scan():
    """192.168.1.0/24 subnet'ini tarayarak agdaki tum cihazlari kesfet.
    Broadcast ping ile ARP tablosunu canlandirir, sonra ip neigh'den
    yeni REACHABLE IP'leri bulup discover_device() cagirir."""
    try:
        loop = asyncio.get_event_loop()

        # 1. Broadcast ping - ARP tablosunu canlandir (ICMP echo request)
        await loop.run_in_executor(
            _hostname_executor,
            lambda: subprocess.run(
                ["ping", "-c", "1", "-W", "1", "-b", "192.168.1.255"],
                capture_output=True, timeout=5,
            ),
        )

        # Kisa bekleme - ARP tablolarinin guncellenmesi icin
        await asyncio.sleep(2)

        # 2. ip neigh show ile REACHABLE ve STALE IP'leri tespit et
        reachable_ips, stale_ips = await loop.run_in_executor(
            _hostname_executor, _get_arp_active_ips
        )

        if not reachable_ips and not stale_ips:
            return

        # Gateway IP'sini her iki setten cikar (modem cihaz olarak izlenmemeli)
        gw_ip = _get_gateway_ip()
        reachable_ips.discard(gw_ip)
        stale_ips.discard(gw_ip)

        # STALE IP'leri ping ile dogrula, basarili olanlari reachable'a ekle
        if stale_ips:
            # Sadece DB'de kayitli olan STALE IP'leri ping et (performans icin)
            async with async_session_factory() as stale_session:
                stale_result = await stale_session.execute(
                    select(Device.ip_address).where(
                        Device.ip_address.in_(stale_ips)
                    )
                )
                db_stale_ips = {row[0] for row in stale_result.all()}

            for ip in db_stale_ips:
                if _is_discoverable_ip(ip):
                    is_alive = await loop.run_in_executor(
                        _hostname_executor, _ping_check, ip
                    )
                    if is_alive:
                        reachable_ips.add(ip)

        if not reachable_ips:
            return

        # 3. DB'de kayitli olmayan IP'ler icin cihaz kesfet
        async with async_session_factory() as session:
            result = await session.execute(
                select(Device.ip_address).where(
                    Device.ip_address.isnot(None)
                )
            )
            known_ips = {row[0] for row in result.all()}

        new_ips = reachable_ips - known_ips
        if new_ips:
            logger.info(
                f"Aktif ag taramasi: {len(new_ips)} yeni IP kesfedildi: "
                f"{', '.join(sorted(new_ips)[:5])}"
                f"{'...' if len(new_ips) > 5 else ''}"
            )
            for ip in new_ips:
                if _is_discoverable_ip(ip):
                    await discover_device(ip)
        else:
            logger.debug(
                f"Aktif ag taramasi: {len(reachable_ips)} REACHABLE IP, "
                f"yeni cihaz yok."
            )

        # 4. Mevcut cihazlarin MAC, hostname ve online durumunu dogrula
        existing_ips = reachable_ips & known_ips
        if existing_ips:
            verified = 0
            fixed = 0
            async with async_session_factory() as session:
                for ip in existing_ips:
                    if not _is_discoverable_ip(ip):
                        continue
                    # ARP'den gercek MAC oku
                    arp_mac = await loop.run_in_executor(
                        _hostname_executor, _read_mac_from_arp, ip
                    )
                    if not arp_mac:
                        continue

                    result = await session.execute(
                        select(Device).where(Device.ip_address == ip)
                    )
                    device = result.scalar_one_or_none()
                    if not device:
                        continue

                    if device.mac_address != arp_mac:
                        # MAC uyumsuzlugu - eski cihazi bu IP'den ayir
                        logger.warning(
                            f"Tarama MAC dogrulamasi: {ip} device={device.mac_address} "
                            f"({device.hostname}), ARP={arp_mac}. Eski cihaz ayrildi."
                        )
                        device.ip_address = None
                        device.is_online = False
                        if device.last_online_start:
                            session_seconds = int(
                                (datetime.now() - device.last_online_start).total_seconds()
                            )
                            device.total_online_seconds = (
                                device.total_online_seconds or 0
                            ) + session_seconds
                            device.last_online_start = None
                        await session.commit()

                        # Yeni MAC icin discover_device cagir
                        _known_ips.pop(ip, None)  # Cache'den cikar
                        await discover_device(ip)
                        fixed += 1
                    else:
                        # MAC dogru - online durumunu ve last_seen guncelle
                        now = datetime.now()
                        if not device.is_online:
                            device.is_online = True
                            device.last_online_start = now
                        device.last_seen = now

                        # DHCP hostname ile placeholder hostname guncelle
                        dhcp_hn, _ = await loop.run_in_executor(
                            _hostname_executor, _read_hostname_from_dhcp_leases, ip
                        )
                        if dhcp_hn and device.hostname and \
                                device.hostname.startswith(("client-", "dot-", "dhcp-")):
                            device.hostname = dhcp_hn
                        verified += 1

                await session.commit()
            if fixed or verified:
                logger.info(
                    f"Tarama dogrulamasi: {verified} cihaz dogrulandi, "
                    f"{fixed} MAC uyumsuzlugu duzeltildi."
                )
    except Exception as e:
        logger.error(f"Aktif ag taramasi hatasi: {e}")


async def rebuild_ip_device_cache():
    """Başlangicta tum cihazlarin IP->device_id cache'ini Redis'e yukle."""
    try:
        redis_client = await get_redis()
        async with async_session_factory() as session:
            result = await session.execute(
                select(Device).where(Device.ip_address.isnot(None))
            )
            devices = result.scalars().all()
            count = 0
            for device in devices:
                if device.ip_address and not _is_docker_ip(device.ip_address):
                    await redis_client.set(
                        f"dns:ip_to_device:{device.ip_address}",
                        str(device.id),
                        ex=600,
                    )
                    count += 1
            logger.info(f"IP->device cache: {count} cihaz Redis'e yuklendi.")
    except Exception as e:
        logger.error(f"IP-device cache oluşturma hatasi: {e}")


async def start_device_discovery_worker():
    """Periyodik olarak offline cihazlari isaretleyen, aktif ag taramasi
    yapan ve IP cache'i yenileyen worker."""
    logger.info("Cihaz kesfi worker başlatildi.")

    # Başlangicta IP->device cache'ini oluştur
    await rebuild_ip_device_cache()

    # Mevcut cihazlarin hostname'lerinden cihaz tipini tespit et
    await update_existing_devices_fingerprint()

    # Baslangicta bir kere aktif ag taramasi yap
    await _active_network_scan()

    scan_counter = 0
    while True:
        await asyncio.sleep(60)  # Her dakika
        scan_counter += 1

        await mark_offline_devices()

        # Her 3 dakikada aktif ag taramasi
        if scan_counter % 3 == 0:
            try:
                await _active_network_scan()
            except Exception as e:
                logger.error(f"Aktif ag taramasi hatasi: {e}")

        # Her 5 dakikada IP cache'i tazele
        # (TTL 10dk, 5dk'da bir yenileyerek kaybolmamasini sagla)
        if scan_counter % 5 == 0:
            try:
                await rebuild_ip_device_cache()
            except Exception as e:
                logger.error(f"IP cache yenileme hatasi: {e}")

        # Eski hata sayaclarini temizle
        now = datetime.now()
        stale = [ip for ip, t in _known_ips.items()
                 if (now - t).total_seconds() > 600]
        for ip in stale:
            _known_ips.pop(ip, None)
            _FAILED_IPS.pop(ip, None)

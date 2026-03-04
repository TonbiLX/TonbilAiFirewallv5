# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Linux DHCP Driver: dnsmasq konfigurasyonu ve lease yönetimi
# Config dosyalarini host'taki /etc/dnsmasq.d/tonbilai/ dizinine yazar
# Lease dosyasini /var/lib/misc/dnsmasq.leases'ten okur
# systemd path unit config degisıklığı algilayinca dnsmasq'i otomatik reload eder

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("tonbilai.linux_dhcp_driver")

# Native yollar (Docker yok)
DNSMASQ_CONF_DIR = Path("/etc/dnsmasq.d")
DNSMASQ_LEASES_FILE = Path("/var/lib/misc/dnsmasq.leases")


def _lease_time_str(seconds: int) -> str:
    """Lease süresini dnsmasq formatina cevir (orn: 24h, 12h, 1h)."""
    if seconds >= 86400 and seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60}m"
    return str(seconds)


def generate_pool_config(pool: Dict[str, Any]) -> str:
    """Bir DHCP havuzu için dnsmasq konfigurasyon satirlari uret."""
    lines = [
        f"# Pool: {pool.get('name', 'unnamed')} (ID: {pool.get('id', '?')})",
    ]

    if not pool.get("enabled", True):
        lines.append(f"# DEVRE DISI - pool {pool.get('id')} kapali")
        return "\n".join(lines)

    range_start = pool.get("range_start", "")
    range_end = pool.get("range_end", "")
    netmask = pool.get("netmask", "255.255.255.0")
    lease_time = _lease_time_str(pool.get("lease_time_seconds", 86400))

    # DHCP range
    lines.append(f"dhcp-range={range_start},{range_end},{netmask},{lease_time}")

    # Gateway (option 3)
    gateway = pool.get("gateway", "")
    if gateway:
        lines.append(f"dhcp-option=3,{gateway}")

    # DNS sunuculari (option 6) - bizim DNS proxy'yi isaret et
    dns_servers = pool.get("dns_servers", [])
    if dns_servers:
        lines.append(f"dhcp-option=6,{','.join(dns_servers)}")

    # /32 netmask: Classless Static Routes (RFC 3442) — gateway'e host route + default route
    # Cihazlar /32 mask ile diger cihazlara dogrudan ulasamaz, tum trafik Pi uzerinden gecer
    if netmask == "255.255.255.255" and gateway:
        # Option 121: RFC 3442 classless static routes
        lines.append(f"dhcp-option=121,{gateway}/32,0.0.0.0,0.0.0.0/0,{gateway}")
        # Option 249: Microsoft classless routes (eski Windows uyumlulugu)
        lines.append(f"dhcp-option=249,{gateway}/32,0.0.0.0,0.0.0.0/0,{gateway}")

    return "\n".join(lines)


import re

_SAFE_HOSTNAME_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$')


def _sanitize_hostname(hostname: str) -> str:
    """Hostname'i dnsmasq config enjeksiyonuna karsi temizle.
    Newline, semicolon, comma karakterlerini kaldir ve regex ile dogrula."""
    # Tehlikeli karakterleri temizle
    hostname = hostname.replace('\n', '').replace('\r', '').replace(';', '').replace(',', '')
    hostname = hostname.strip()[:63]  # Max 63 karakter (RFC 1035)
    if not hostname or not _SAFE_HOSTNAME_RE.match(hostname):
        return ""
    return hostname


_MAC_VALID_RE = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')


def _sanitize_config_value(val: str) -> str:
    """Config enjeksiyonunu onle: newline, semicolon, comma temizle."""
    return val.replace('\n', '').replace('\r', '').replace(';', '').replace(',', '').strip()


def generate_static_leases_config(static_leases: List[Dict[str, Any]]) -> str:
    """Statik IP atamalari için dnsmasq konfigurasyon satirlari uret."""
    lines = ["# Statik IP atamalari"]
    for lease in static_leases:
        mac = _sanitize_config_value(lease.get("mac_address", ""))
        ip = _sanitize_config_value(lease.get("ip_address", ""))
        hostname = _sanitize_hostname(lease.get("hostname", ""))
        # MAC ve IP format dogrulamasi
        if not mac or not _MAC_VALID_RE.match(mac):
            continue
        try:
            import ipaddress
            ipaddress.ip_address(ip)
        except (ValueError, TypeError):
            continue
        if hostname:
            lines.append(f"dhcp-host={mac},{ip},{hostname}")
        else:
            lines.append(f"dhcp-host={mac},{ip}")
    return "\n".join(lines)


def write_pool_config(pool_id: int, config_content: str) -> bool:
    """Tek havuz için config dosyasi yaz."""
    try:
        conf_file = DNSMASQ_CONF_DIR / f"pool-{pool_id}.conf"
        conf_file.write_text(config_content + "\n")
        logger.info(f"DHCP pool config yazildi: {conf_file}")
        return True
    except Exception as e:
        logger.error(f"Config yazma hatasi: {e}")
        return False


def remove_pool_config(pool_id: int) -> bool:
    """Havuz config dosyasini sil."""
    try:
        conf_file = DNSMASQ_CONF_DIR / f"pool-{pool_id}.conf"
        if conf_file.exists():
            conf_file.unlink()
            logger.info(f"DHCP pool config silindi: {conf_file}")
        return True
    except Exception as e:
        logger.error(f"Config silme hatasi: {e}")
        return False


def write_static_leases_config(static_leases: List[Dict[str, Any]]) -> bool:
    """Statik lease config dosyasi yaz."""
    try:
        conf_file = DNSMASQ_CONF_DIR / "static-leases.conf"
        content = generate_static_leases_config(static_leases)
        conf_file.write_text(content + "\n")
        logger.info(f"Statik lease config yazildi: {conf_file}")
        return True
    except Exception as e:
        logger.error(f"Statik lease config hatasi: {e}")
        return False


def trigger_reload():
    """dnsmasq reload tetikle (systemd path unit algiliyor)."""
    try:
        # Config dizinine bir trigger dosyasi yaz
        # systemd PathChanged bu degisıklığı algilar ve dnsmasq'i reload eder
        trigger = DNSMASQ_CONF_DIR / ".reload-trigger"
        trigger.write_text(str(time.time()))
        logger.info("dnsmasq reload tetiklendi")
    except Exception as e:
        logger.error(f"Reload tetikleme hatasi: {e}")


def parse_leases_file() -> List[Dict[str, Any]]:
    """dnsmasq lease dosyasini parse et.
    Format: <expire_time> <mac> <ip> <hostname> <client_id>
    expire_time: Unix timestamp (0 = statik/infinite)
    """
    leases = []
    if not DNSMASQ_LEASES_FILE.exists():
        return leases

    try:
        content = DNSMASQ_LEASES_FILE.read_text()
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 4:
                continue

            expire_ts = int(parts[0])
            mac = parts[1].upper()
            ip = parts[2]
            hostname = parts[3] if parts[3] != "*" else ""

            # Expire zamanini hesapla (her ikisi de UTC olmali!)
            if expire_ts == 0:
                lease_end = None  # Statik/infinite
                is_expired = False
            else:
                lease_end = datetime.utcfromtimestamp(expire_ts)
                is_expired = datetime.utcnow() > lease_end

            leases.append({
                "mac_address": mac,
                "ip_address": ip,
                "hostname": hostname,
                "lease_end": lease_end,
                "is_expired": is_expired,
                "expire_timestamp": expire_ts,
            })
    except Exception as e:
        logger.error(f"Lease dosyasi parse hatasi: {e}")

    return leases


def remove_lease_from_file(mac: str) -> bool:
    """dnsmasq lease dosyasindan belirli bir MAC'in lease'ini sil.
    Dosya okunduktan sonra, ilgili satir cikarilarak yeniden yazilir.
    dnsmasq çalışırken lease dosyasini okumaz (sadece başlangıçta okur),
    ama bu sayede sync worker'in dosyadan tekrar okumasini onleriz.
    """
    if not DNSMASQ_LEASES_FILE.exists():
        return False

    try:
        mac_upper = mac.upper()
        content = DNSMASQ_LEASES_FILE.read_text()
        lines = content.strip().split("\n")
        new_lines = []
        removed = False
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4 and parts[1].upper() == mac_upper:
                removed = True
                logger.info(f"Lease dosyasindan silindi: {mac_upper} ({parts[2]})")
                continue
            new_lines.append(line)

        if removed:
            DNSMASQ_LEASES_FILE.write_text("\n".join(new_lines) + "\n" if new_lines else "")
        return removed
    except Exception as e:
        logger.error(f"Lease dosyasindan silme hatasi: {e}")
        return False


def is_dnsmasq_running() -> bool:
    """dnsmasq process'inin calisiyor olup olmadigini kontrol et."""
    pid_file = Path("/run/dnsmasq/dnsmasq.pid")
    if not pid_file.exists():
        # PID dosyasi yoksa /proc ile kontrol et
        try:
            for entry in os.listdir("/proc"):
                if entry.isdigit():
                    try:
                        cmdline = Path(f"/proc/{entry}/cmdline").read_text()
                        if "dnsmasq" in cmdline:
                            return True
                    except (PermissionError, FileNotFoundError):
                        pass
        except Exception:
            pass
        return False

    try:
        pid = int(pid_file.read_text().strip())
        # PID'nin hala aktif olup olmadigini kontrol et
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Sistem Yönetimi Servisi: servis durumu, restart, reboot, boot counter,
# safe mode, watchdog durumu, journal okuma.

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("tonbilai.system_management")

BOOT_COUNT_FILE = Path("/var/lib/tonbilai/boot-count")
SAFE_MODE_FLAG = Path("/var/lib/tonbilai/safe-mode")
MAX_BOOTS_THRESHOLD = 5

# Yonetilebilir servisler — whitelist
MANAGED_SERVICES = [
    {"name": "tonbilaios-backend", "label": "TonbilAi Backend", "critical": True},
    {"name": "nginx", "label": "Nginx Web Sunucu", "critical": True},
    {"name": "ssh", "label": "SSH Sunucu", "critical": True},
    {"name": "mariadb", "label": "MariaDB Veritabani", "critical": True},
    {"name": "redis-server", "label": "Redis Cache", "critical": True},
    {"name": "nftables", "label": "nftables Firewall", "critical": True},
    {"name": "systemd-resolved", "label": "DNS Resolver", "critical": False},
    {"name": "systemd-timesyncd", "label": "NTP Zaman Esitleme", "critical": False},
    {"name": "wg-quick@wg0", "label": "WireGuard VPN", "critical": False},
]

# Hizli erişim için isim seti
_ALLOWED_NAMES = {s["name"] for s in MANAGED_SERVICES}
# Durdurulamaz servisler
_NO_STOP = {"ssh"}


# ============================================================================
# Yardimci — subprocess
# ============================================================================

async def _run_cmd(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Shell komutu calistir, (returncode, stdout, stderr) dondur."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return -1, "", "timeout"
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


def _validate_service_name(name: str) -> str:
    """Servis adini dogrula — sadece whitelist'tekiler kabul edilir."""
    if name not in _ALLOWED_NAMES:
        raise ValueError(f"Bilinmeyen servis: {name}")
    return name


# ============================================================================
# Servis Durumu
# ============================================================================

async def get_service_status(service_name: str) -> dict:
    """systemctl show ile servis durumu oku."""
    _validate_service_name(service_name)

    props = "ActiveState,SubState,MainPID,MemoryCurrent,ActiveEnterTimestamp,NRestarts"
    rc, out, _ = await _run_cmd([
        "systemctl", "show", service_name,
        f"--property={props}",
    ])

    info = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v

    # Servis meta bilgisi
    svc_meta = next((s for s in MANAGED_SERVICES if s["name"] == service_name), {})

    # PID
    pid = None
    try:
        p = int(info.get("MainPID", "0"))
        if p > 0:
            pid = p
    except ValueError:
        pass

    # Memory (byte → MB)
    memory_mb = None
    mem_raw = info.get("MemoryCurrent", "")
    if mem_raw and mem_raw != "[not set]" and mem_raw.isdigit():
        memory_mb = round(int(mem_raw) / (1024 * 1024), 1)

    # Uptime (ActiveEnterTimestamp → saniye)
    uptime_seconds = None
    ts_raw = info.get("ActiveEnterTimestamp", "")
    if ts_raw and ts_raw not in ("", "n/a"):
        try:
            # Format: "Wed 2026-02-19 14:30:00 +03" gibi
            # Basitlestirme: sadece tarih+saat al
            ts_clean = re.sub(r'^[A-Za-z]+ ', '', ts_raw).strip()
            # +03 gibi TZ offset'i kaldir
            ts_clean = re.sub(r'\s+[+-]\d+$', '', ts_clean)
            ts_clean = re.sub(r'\s+[A-Z]{2,5}$', '', ts_clean)
            dt = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")
            uptime_seconds = int((datetime.now() - dt).total_seconds())
            if uptime_seconds < 0:
                uptime_seconds = 0
        except Exception:
            pass

    # Restart count
    restart_count = None
    try:
        restart_count = int(info.get("NRestarts", "0"))
    except ValueError:
        pass

    return {
        "name": service_name,
        "label": svc_meta.get("label", service_name),
        "active_state": info.get("ActiveState", "unknown"),
        "sub_state": info.get("SubState", "unknown"),
        "pid": pid,
        "memory_mb": memory_mb,
        "uptime_seconds": uptime_seconds,
        "critical": svc_meta.get("critical", False),
        "restart_count": restart_count,
    }


async def get_all_services_status() -> list[dict]:
    """Tum yonetilen servislerin durumunu paralel getir."""
    tasks = [get_service_status(s["name"]) for s in MANAGED_SERVICES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    statuses = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            svc = MANAGED_SERVICES[i]
            statuses.append({
                "name": svc["name"],
                "label": svc["label"],
                "active_state": "error",
                "sub_state": str(r),
                "pid": None,
                "memory_mb": None,
                "uptime_seconds": None,
                "critical": svc["critical"],
                "restart_count": None,
            })
        else:
            statuses.append(r)
    return statuses


# ============================================================================
# Servis Kontrol
# ============================================================================

async def restart_service(service_name: str) -> dict:
    """Servisi yeniden başlat."""
    _validate_service_name(service_name)

    # Backend kendini restart ediyorsa gecikmeli yap
    if service_name == "tonbilaios-backend":
        rc, _, err = await _run_cmd([
            "sudo", "systemd-run", "--on-active=2s",
            "--unit=tonbilai-mgmt-restart",
            "systemctl", "restart", "tonbilaios-backend",
        ])
        return {
            "success": rc == 0,
            "message": "Backend 2 saniye içinde yeniden başlatilacak" if rc == 0 else f"Hata: {err}",
        }

    rc, _, err = await _run_cmd(["sudo", "systemctl", "restart", service_name])
    return {
        "success": rc == 0,
        "message": f"{service_name} yeniden başlatildi" if rc == 0 else f"Hata: {err}",
    }


async def start_service(service_name: str) -> dict:
    """Servisi başlat."""
    _validate_service_name(service_name)

    rc, _, err = await _run_cmd(["sudo", "systemctl", "start", service_name])
    return {
        "success": rc == 0,
        "message": f"{service_name} başlatildi" if rc == 0 else f"Hata: {err}",
    }


async def stop_service(service_name: str) -> dict:
    """Servisi durdur. SSH ve kritik servisler durdurulamaz."""
    _validate_service_name(service_name)

    if service_name in _NO_STOP:
        return {"success": False, "message": f"{service_name} durdurulamaz (güvenlik kisitlamasi)"}

    rc, _, err = await _run_cmd(["sudo", "systemctl", "stop", service_name])
    return {
        "success": rc == 0,
        "message": f"{service_name} durduruldu" if rc == 0 else f"Hata: {err}",
    }


# ============================================================================
# Sistem Genel Durum
# ============================================================================

async def get_system_overview() -> dict:
    """Uptime, boot count, safe mode, watchdog durumu, hostname."""
    # Uptime
    uptime_seconds = 0.0
    try:
        raw = Path("/proc/uptime").read_text().strip()
        uptime_seconds = float(raw.split()[0])
    except Exception:
        pass

    # Hostname
    hostname = "unknown"
    try:
        hostname = Path("/etc/hostname").read_text().strip()
    except Exception:
        pass

    # Boot count
    boot_count = _read_boot_count()

    # Safe mode
    safe_mode = SAFE_MODE_FLAG.exists()

    # Watchdog durumu
    watchdog_active = False
    try:
        rc, out, _ = await _run_cmd(["wdctl", "/dev/watchdog0"])
        if rc == 0 and "Timeleft" in out:
            watchdog_active = True
    except Exception:
        pass

    # Son boot zamani
    boot_time = ""
    try:
        rc, out, _ = await _run_cmd(["uptime", "-s"])
        if rc == 0:
            boot_time = out.strip()
    except Exception:
        pass

    return {
        "uptime_seconds": round(uptime_seconds),
        "boot_time": boot_time,
        "boot_count": boot_count,
        "safe_mode": safe_mode,
        "watchdog_active": watchdog_active,
        "hostname": hostname,
    }


# ============================================================================
# Boot Bilgisi & Safe Mode
# ============================================================================

def _read_boot_count() -> int:
    """Boot sayacıni oku."""
    try:
        if BOOT_COUNT_FILE.exists():
            return int(BOOT_COUNT_FILE.read_text().strip())
    except (ValueError, OSError):
        pass
    return 0


async def get_boot_info() -> dict:
    """Boot sayacı, safe mode, son boot zamanlari."""
    boot_count = _read_boot_count()
    safe_mode = SAFE_MODE_FLAG.exists()

    # Watchdog
    watchdog_active = False
    try:
        rc, out, _ = await _run_cmd(["wdctl", "/dev/watchdog0"])
        if rc == 0 and "Timeleft" in out:
            watchdog_active = True
    except Exception:
        pass

    # Son 5 boot zamani (journalctl)
    recent_boots: list[str] = []
    try:
        rc, out, _ = await _run_cmd([
            "journalctl", "--list-boots", "-n", "5", "--no-pager",
        ])
        if rc == 0 and out:
            for line in out.splitlines():
                parts = line.strip().split()
                # Format: index boot_id timestamp...
                if len(parts) >= 4:
                    # Tarih+saat kismi (3. ve 4. eleman genelde)
                    ts = " ".join(parts[2:5]) if len(parts) >= 5 else " ".join(parts[2:])
                    recent_boots.append(ts)
    except Exception:
        pass

    return {
        "boot_count": boot_count,
        "safe_mode": safe_mode,
        "max_boots_threshold": MAX_BOOTS_THRESHOLD,
        "watchdog_active": watchdog_active,
        "recent_boots": recent_boots,
    }


async def reset_safe_mode() -> dict:
    """Safe mode'dan cik: flag sil, sayac sıfırla, servisleri başlat."""
    try:
        # Sayacı sıfırla
        BOOT_COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
        BOOT_COUNT_FILE.write_text("0")

        # Safe mode flag sil
        if SAFE_MODE_FLAG.exists():
            SAFE_MODE_FLAG.unlink()

        # Servisleri başlat
        await _run_cmd(["sudo", "systemctl", "start", "tonbilaios-backend"])
        await _run_cmd(["sudo", "systemctl", "start", "nginx"])

        logger.info("Safe mode sıfırlandi, servisler başlatildi")
        return {"success": True, "message": "Safe mode sıfırlandi, servisler başlatildi"}
    except Exception as e:
        logger.error(f"Safe mode sıfırlama hatasi: {e}")
        return {"success": False, "message": f"Hata: {e}"}


# ============================================================================
# Sistem Yeniden Başlatma / Kapatma
# ============================================================================

async def reboot_system() -> dict:
    """Sistemi 3 saniye içinde yeniden başlat."""
    try:
        rc, _, err = await _run_cmd([
            "sudo", "systemd-run", "--on-active=3s",
            "--unit=tonbilai-reboot",
            "systemctl", "reboot",
        ])
        if rc == 0:
            logger.warning("Sistem 3 saniye içinde yeniden başlatilacak!")
            return {"success": True, "message": "Sistem 3 saniye içinde yeniden başlatilacak"}
        return {"success": False, "message": f"Reboot zamanlanamadi: {err}"}
    except Exception as e:
        return {"success": False, "message": f"Hata: {e}"}


async def shutdown_system() -> dict:
    """Sistemi 3 saniye içinde kapat."""
    try:
        rc, _, err = await _run_cmd([
            "sudo", "systemd-run", "--on-active=3s",
            "--unit=tonbilai-shutdown",
            "systemctl", "poweroff",
        ])
        if rc == 0:
            logger.warning("Sistem 3 saniye içinde kapanacak!")
            return {"success": True, "message": "Sistem 3 saniye içinde kapanacak"}
        return {"success": False, "message": f"Shutdown zamanlanamadi: {err}"}
    except Exception as e:
        return {"success": False, "message": f"Hata: {e}"}


# ============================================================================
# Sistem Journal
# ============================================================================

async def get_systemd_journal_recent(lines: int = 50) -> list[str]:
    """Son N satir journal kaydi (systemd-journald)."""
    lines = max(10, min(200, lines))

    rc, out, _ = await _run_cmd([
        "journalctl", "-n", str(lines), "--no-pager",
        "-o", "short-iso",
    ], timeout=10)

    if rc != 0 or not out:
        return []

    return out.splitlines()

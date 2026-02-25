# --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
# Saat & Tarih API: timezone değiştirme, NTP ayarları, anlik senkronizasyon.
# Native mod: timedatectl komutlari dogrudan subprocess ile calistirilir.
# Docker trigger-file pattern'i artik kullanilmiyor.

import json
import logging
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import available_timezones

from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("tonbilai.system_time")

# Cache dosyasi (timezone_service tarafindan okunur)
TIME_CONFIG_DIR = Path("/var/lib/tonbilai-time")
STATUS_FILE = TIME_CONFIG_DIR / "time-status.json"

TIMEDATECTL = "/usr/bin/timedatectl"
TIMESYNCD_DROP_IN_DIR = Path("/etc/systemd/timesyncd.conf.d")
TIMESYNCD_DROP_IN = TIMESYNCD_DROP_IN_DIR / "tonbilai-ntp.conf"


# --- Pydantic modelleri ---

class SetTimezoneRequest(BaseModel):
    timezone: str

class SetNtpServerRequest(BaseModel):
    ntp_server: str

class TimeStatusResponse(BaseModel):
    current_time: str
    timezone: str
    ntp_enabled: bool
    ntp_server: Optional[str] = None
    ntp_synced: bool = False
    utc_offset: Optional[str] = None

class TimezoneListResponse(BaseModel):
    timezones: dict[str, list[str]]

class NtpServerListResponse(BaseModel):
    servers: list[dict[str, str]]


# --- Yardimci fonksiyonlar ---

def _run_timedatectl(*args, check: bool = True, timeout: int = 10) -> subprocess.CompletedProcess:
    """timedatectl komutunu güvenli sekilde calistir (shell=False)."""
    cmd = ["sudo", TIMEDATECTL] + list(args)
    logger.debug(f"Calistiriliyor: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        if check and result.returncode != 0:
            logger.error(f"timedatectl hatasi (rc={result.returncode}): {result.stderr.strip()}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"timedatectl zaman asimi: {' '.join(cmd)}")
        raise
    except FileNotFoundError:
        logger.error("timedatectl bulunamadı")
        raise


def _read_status() -> dict:
    """timedatectl show ciktisini parse ederek sistem durumunu oku."""
    try:
        result = _run_timedatectl("show", check=True)
        props = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()

        tz = props.get("Timezone", "UTC")
        ntp_enabled = props.get("NTP", "no").lower() == "yes"
        ntp_synced = props.get("NTPSynchronized", "no").lower() == "yes"

        # UTC offset hesapla
        utc_offset = None
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(tz))
            offset = now.utcoffset()
            if offset is not None:
                total_seconds = int(offset.total_seconds())
                hours, remainder = divmod(abs(total_seconds), 3600)
                minutes = remainder // 60
                sign = "+" if total_seconds >= 0 else "-"
                utc_offset = f"UTC{sign}{hours:02d}:{minutes:02d}"
        except Exception:
            pass

        # NTP sunucu bilgisini timesyncd config'den oku
        ntp_server = _read_ntp_server_from_config()

        return {
            "timezone": tz,
            "ntp_enabled": ntp_enabled,
            "ntp_synced": ntp_synced,
            "ntp_server": ntp_server,
            "utc_offset": utc_offset,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning(f"timedatectl show okunamadi: {e}")
        # Fallback: eski status dosyasini dene
        if STATUS_FILE.exists():
            try:
                return json.loads(STATUS_FILE.read_text())
            except Exception:
                pass
        return {}


def _read_ntp_server_from_config() -> Optional[str]:
    """timesyncd drop-in config'den NTP sunucu adresini oku."""
    if TIMESYNCD_DROP_IN.exists():
        try:
            content = TIMESYNCD_DROP_IN.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("NTP="):
                    server = line[4:].strip()
                    if server:
                        return server
        except Exception:
            pass
    return None


def _write_status_cache(status: dict):
    """timezone_service için cache dosyasini güncelle."""
    try:
        TIME_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps(status, indent=2))
        logger.debug("time-status.json cache güncellendi")
    except Exception as e:
        logger.warning(f"time-status.json yazilamadi: {e}")


def _read_host_timezone() -> str:
    """Host timezone bilgisini oku."""
    # Öncelik: timedatectl show
    try:
        result = _run_timedatectl("show", "--property=Timezone", "--value", check=True)
        tz = result.stdout.strip()
        if tz:
            return tz
    except Exception:
        pass

    # Fallback: status cache dosyasi
    if STATUS_FILE.exists():
        try:
            data = json.loads(STATUS_FILE.read_text())
            tz = data.get("timezone", "").strip()
            if tz:
                return tz
        except Exception:
            pass

    # Fallback: /etc/timezone
    tz_file = Path("/etc/timezone")
    if tz_file.exists():
        try:
            return tz_file.read_text().strip()
        except Exception:
            pass

    return "UTC"


def _sanitize_timezone(tz: str) -> str:
    """Timezone stringini dogrula - sadece güvenli karakterler."""
    if not re.match(r'^[A-Za-z0-9/_+-]+$', tz):
        raise ValueError(f"Geçersiz timezone formati: {tz}")
    return tz


def _sanitize_ntp_server(server: str) -> str:
    """NTP sunucu adresini dogrula - sadece güvenli karakterler."""
    server = server.strip()
    if not re.match(r'^[A-Za-z0-9._-]+$', server):
        raise ValueError(f"Geçersiz NTP sunucu adresi: {server}")
    if len(server) > 253:
        raise ValueError("NTP sunucu adresi cok uzun")
    return server


# --- Onceden tanimli NTP sunuculari ---

PREDEFINED_NTP_SERVERS = [
    {"id": "pool.ntp.org", "name": "NTP Pool (Global)", "address": "pool.ntp.org"},
    {"id": "time.google.com", "name": "Google Time", "address": "time.google.com"},
    {"id": "time.cloudflare.com", "name": "Cloudflare Time", "address": "time.cloudflare.com"},
    {"id": "ntp.ubuntu.com", "name": "Ubuntu NTP", "address": "ntp.ubuntu.com"},
    {"id": "tr.pool.ntp.org", "name": "NTP Pool (Turkiye)", "address": "tr.pool.ntp.org"},
    {"id": "europe.pool.ntp.org", "name": "NTP Pool (Avrupa)", "address": "europe.pool.ntp.org"},
]


# --- API Endpointleri ---

@router.get("/status", response_model=TimeStatusResponse)
async def get_time_status(
    current_user: User = Depends(get_current_user),
):
    """Mevcut saat, timezone, NTP durumu."""
    from app.services.timezone_service import now_local
    status = _read_status()
    tz = status.get("timezone") or _read_host_timezone()
    local_now = now_local()

    return TimeStatusResponse(
        current_time=local_now.isoformat(),
        timezone=tz,
        ntp_enabled=status.get("ntp_enabled", True),
        ntp_server=status.get("ntp_server"),
        ntp_synced=status.get("ntp_synced", False),
        utc_offset=status.get("utc_offset"),
    )


@router.get("/timezones", response_model=TimezoneListResponse)
async def list_timezones(
    current_user: User = Depends(get_current_user),
):
    """Tum IANA timezone listesi (bolgeye göre gruplanmis)."""
    all_tz = sorted(available_timezones())
    grouped: dict[str, list[str]] = {}

    for tz in all_tz:
        if "/" in tz:
            region = tz.split("/")[0]
        else:
            region = "Other"
        grouped.setdefault(region, []).append(tz)

    return TimezoneListResponse(timezones=grouped)


@router.get("/ntp-servers", response_model=NtpServerListResponse)
async def list_ntp_servers(
    current_user: User = Depends(get_current_user),
):
    """Onceden tanimli NTP sunuculari."""
    return NtpServerListResponse(servers=PREDEFINED_NTP_SERVERS)


@router.post("/set-timezone")
async def set_timezone(
    req: SetTimezoneRequest,
    current_user: User = Depends(get_current_user),
):
    """Timezone değiştir (timedatectl ile dogrudan)."""
    all_tz = available_timezones()
    if req.timezone not in all_tz:
        raise HTTPException(status_code=400, detail=f"Geçersiz timezone: {req.timezone}")

    tz = _sanitize_timezone(req.timezone)

    try:
        _run_timedatectl("set-timezone", tz, check=True)
        logger.info(f"Timezone ayarlandi: {tz}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Timezone ayarlanamadi: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Timezone ayarlanamadi: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="timedatectl zaman asimina ugradi")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="timedatectl bulunamadı")

    # timezone_service cache'i için status dosyasini güncelle
    status = _read_status()
    status["timezone"] = tz
    status["timestamp"] = datetime.now(timezone.utc).isoformat()
    _write_status_cache(status)

    return {
        "success": True,
        "message": f"Timezone '{tz}' olarak ayarlandi.",
        "timezone": tz,
    }


@router.post("/set-ntp-server")
async def set_ntp_server(
    req: SetNtpServerRequest,
    current_user: User = Depends(get_current_user),
):
    """NTP sunucusu değiştir (timesyncd drop-in config)."""
    if not req.ntp_server.strip():
        raise HTTPException(status_code=400, detail="NTP sunucu adresi bos olamaz.")

    try:
        server = _sanitize_ntp_server(req.ntp_server)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # timesyncd drop-in config yaz
    drop_in_content = f"[Time]\nNTP={server}\n"
    try:
        # sudo ile drop-in dizinini oluştur ve dosyayi yaz
        subprocess.run(
            ["sudo", "mkdir", "-p", str(TIMESYNCD_DROP_IN_DIR)],
            capture_output=True, text=True, timeout=5, shell=False, check=True,
        )
        subprocess.run(
            ["sudo", "tee", str(TIMESYNCD_DROP_IN)],
            input=drop_in_content,
            capture_output=True, text=True, timeout=5, shell=False, check=True,
        )
        logger.info(f"NTP sunucu config yazildi: {server}")
    except subprocess.CalledProcessError as e:
        logger.error(f"NTP config yazilamadi: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"NTP config yazilamadi: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="NTP config yazma zaman asimi")

    # systemd-timesyncd servisini yeniden başlat
    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", "systemd-timesyncd"],
            capture_output=True, text=True, timeout=10, shell=False, check=True,
        )
        logger.info("systemd-timesyncd yeniden başlatildi")
    except subprocess.CalledProcessError as e:
        logger.error(f"timesyncd yeniden başlatilamadi: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"NTP sunucusu ayarlandi ama timesyncd yeniden başlatilamadi: {e.stderr.strip()}",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="timesyncd restart zaman asimi")

    # Cache güncelle
    status = _read_status()
    status["ntp_server"] = server
    status["timestamp"] = datetime.now(timezone.utc).isoformat()
    _write_status_cache(status)

    return {
        "success": True,
        "message": f"NTP sunucusu '{server}' olarak ayarlandi.",
        "ntp_server": server,
    }


@router.post("/sync-now")
async def sync_now(
    current_user: User = Depends(get_current_user),
):
    """Anlik NTP senkronizasyonu."""
    errors = []

    # NTP'yi aktif et
    try:
        _run_timedatectl("set-ntp", "true", check=True)
        logger.info("NTP etkinlestirildi")
    except subprocess.CalledProcessError as e:
        msg = f"NTP etkinlestirilemedi: {e.stderr.strip()}"
        logger.error(msg)
        errors.append(msg)
    except subprocess.TimeoutExpired:
        errors.append("timedatectl set-ntp zaman asimi")

    # timesync-status kontrol et (bilgi amacli, hata olursa yoksay)
    timesync_info = None
    try:
        result = subprocess.run(
            ["sudo", TIMEDATECTL, "timesync-status"],
            capture_output=True, text=True, timeout=10, shell=False,
        )
        if result.returncode == 0:
            timesync_info = result.stdout.strip()
            logger.debug(f"timesync-status: {timesync_info}")
    except Exception as e:
        logger.debug(f"timesync-status alinamadi (önemli degil): {e}")

    if errors:
        raise HTTPException(status_code=500, detail="; ".join(errors))

    # Guncel durumu oku ve cache'e yaz
    status = _read_status()
    _write_status_cache(status)

    return {
        "success": True,
        "message": "NTP senkronizasyonu tetiklendi.",
        "ntp_synced": status.get("ntp_synced", False),
        "timesync_info": timesync_info,
    }

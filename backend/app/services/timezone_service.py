# --- Ajan: MIMAR (THE ARCHITECT) ---
# Merkezi saat dilimi servisi: Sistem ayarlarından timezone okur,
# tum modullerde tutarli yerel saat gosterimi saglar.
#
# Kullanım:
#   from app.services.timezone_service import now_local, format_local_time
#   now_local()               -> datetime (yerel saat)
#   format_local_time()       -> "21:30:15 15/02/2026"
#   to_local(utc_dt)          -> datetime (UTC'den yerel saate cevir)

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger("tonbilai.timezone")

# Cache: saat dilimi bilgisi her 60 saniyede bir yenilenir
_cached_tz_name: str | None = None
_cached_tz_offset: timezone | None = None
_last_tz_check: float = 0
_TZ_CACHE_TTL = 60  # saniye

# Bilinen timezone -> UTC offset eslesmesi (zoneinfo olmadan çalışır)
# Docker container'da zoneinfo veritabani olmayabilir
_TIMEZONE_OFFSETS: dict[str, float] = {
    "Europe/Istanbul": 3, "Europe/London": 0, "Europe/Berlin": 1,
    "Europe/Paris": 1, "Europe/Moscow": 3, "Europe/Athens": 2,
    "Europe/Rome": 1, "Europe/Madrid": 1, "Europe/Amsterdam": 1,
    "Europe/Zurich": 1, "Europe/Warsaw": 1, "Europe/Budapest": 1,
    "Europe/Prague": 1, "Europe/Vienna": 1, "Europe/Helsinki": 2,
    "Europe/Bucharest": 2, "Europe/Sofia": 2, "Europe/Kiev": 2,
    "Europe/Stockholm": 1, "Europe/Oslo": 1, "Europe/Copenhagen": 1,
    "Asia/Tokyo": 9, "Asia/Shanghai": 8, "Asia/Seoul": 9,
    "Asia/Dubai": 4, "Asia/Kolkata": 5.5, "Asia/Singapore": 8,
    "Asia/Bangkok": 7, "Asia/Jakarta": 7, "Asia/Riyadh": 3,
    "Asia/Tehran": 3.5, "Asia/Baku": 4, "Asia/Tbilisi": 4,
    "America/New_York": -5, "America/Chicago": -6,
    "America/Denver": -7, "America/Los_Angeles": -8,
    "America/Sao_Paulo": -3, "America/Toronto": -5,
    "US/Eastern": -5, "US/Central": -6, "US/Mountain": -7, "US/Pacific": -8,
    "Pacific/Auckland": 12, "Australia/Sydney": 11,
    "Africa/Cairo": 2, "Africa/Johannesburg": 2,
    "UTC": 0, "GMT": 0,
}


def _read_system_timezone() -> str:
    """Sistemde ayarlanan timezone'u oku.
    Öncelik sirasi:
    1. /host-time-config/time-status.json (system_time API tarafindan yazilir)
    2. /host-timezone dosyasi (Docker volume mount)
    3. TZ ortam degiskeni
    4. Fallback: Europe/Istanbul
    """
    import json
    import os

    # 1. Status dosyasindan oku (API ile ayarlanan)
    status_file = Path("/var/lib/tonbilai-time/time-status.json")
    if status_file.exists():
        try:
            data = json.loads(status_file.read_text())
            tz = data.get("timezone", "").strip()
            if tz:
                return tz
        except Exception:
            pass

    # 2. Host timezone dosyasindan oku
    tz_file = Path("/etc/timezone")
    if tz_file.exists():
        try:
            tz = tz_file.read_text().strip()
            if tz:
                return tz
        except Exception:
            pass

    # 3. TZ ortam degiskeni
    tz_env = os.environ.get("TZ", "").strip()
    if tz_env:
        return tz_env

    # 4. Fallback
    return "Europe/Istanbul"


def _get_tz_offset(tz_name: str) -> timezone:
    """Timezone isminden UTC offset oluştur."""
    # Bilinen timezone tablosundan bak
    offset_hours = _TIMEZONE_OFFSETS.get(tz_name)
    if offset_hours is not None:
        return timezone(timedelta(hours=offset_hours))

    # zoneinfo kullanmayi dene (varsa)
    try:
        from zoneinfo import ZoneInfo
        zi = ZoneInfo(tz_name)
        # Simdi için offset hesapla
        offset = datetime.now(zi).utcoffset()
        if offset:
            return timezone(offset)
    except Exception:
        pass

    # Son care: UTC
    logger.warning(f"Bilinmeyen timezone: {tz_name}, UTC kullanılıyor.")
    return timezone.utc


def _refresh_cache():
    """Timezone cache'ini yenile."""
    global _cached_tz_name, _cached_tz_offset, _last_tz_check
    import time

    now = time.monotonic()
    if _cached_tz_offset and (now - _last_tz_check) < _TZ_CACHE_TTL:
        return

    tz_name = _read_system_timezone()
    if tz_name != _cached_tz_name:
        _cached_tz_offset = _get_tz_offset(tz_name)
        _cached_tz_name = tz_name
        logger.info(f"Sistem saat dilimi: {tz_name} (offset: {_cached_tz_offset})")

    _last_tz_check = now


def get_timezone() -> timezone:
    """Mevcut sistem saat dilimi offset'ini dondur."""
    _refresh_cache()
    return _cached_tz_offset or timezone.utc


def get_timezone_name() -> str:
    """Mevcut sistem saat dilimi adini dondur."""
    _refresh_cache()
    return _cached_tz_name or "UTC"


def now_local() -> datetime:
    """Yerel saati dondur (sistem timezone'unda)."""
    return datetime.now(get_timezone())


def format_local_time(fmt: str = "%H:%M:%S %d/%m/%Y") -> str:
    """Yerel saati formatli string olarak dondur."""
    return now_local().strftime(fmt)


def to_local(utc_dt: datetime) -> datetime:
    """UTC datetime'i yerel saate cevir."""
    if utc_dt is None:
        return None
    # Eger timezone-naive ise UTC varsay
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(get_timezone())


def format_dt(utc_dt: datetime, fmt: str = "%H:%M:%S %d/%m/%Y") -> str:
    """UTC datetime'i yerel saat olarak formatla."""
    if utc_dt is None:
        return "?"
    return to_local(utc_dt).strftime(fmt)

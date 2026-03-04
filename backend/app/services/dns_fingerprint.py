# --- Ajan: ANALIST (THE ANALYST) ---
# DNS Fingerprinting Servisi: DNS sorgu pattern'lerinden cihaz tipini otomatik tespit eder.
# Ornek: connectivitycheck.gstatic.com -> Android, captive.apple.com -> iOS
# Redis'te IP bazli sorgu gecmisi tutar, pattern eslestirmesi yapar.

import asyncio
import logging
from datetime import datetime

from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.models.device import Device

logger = logging.getLogger("tonbilai.dns_fingerprint")

# --- Fingerprint Kural Tablosu ---
# Her kural: (indicator_domains, detected_os, device_type, confidence)
# confidence: 0.0-1.0 arasi guven skoru, 0.7+ ise DB'ye yazilir
FINGERPRINT_RULES = [
    # Apple cihazlar
    (["captive.apple.com", "gs.apple.com", "mesu.apple.com",
      "gsp-ssl.ls.apple.com", "configuration.apple.com",
      "albert.apple.com", "xp.apple.com"], "iOS", "phone", 0.9),
    (["swscan.apple.com", "osxapps.itunes.apple.com"], "macOS", "computer", 0.85),

    # Android cihazlar
    (["connectivitycheck.gstatic.com", "play.googleapis.com",
      "mtalk.google.com", "android.googleapis.com",
      "android.clients.google.com"], "Android", "phone", 0.85),

    # Samsung özel
    (["lcprd1.samsungcloudsolution.net", "samsungcloudsolution.net",
      "samsungads.com", "samsungelectronics.com",
      "tv-api2.samsungapps.com", "gpm.samsungqbe.com"], "Tizen", "tv", 0.95),
    (["prd-euw1-ucs.aibixby.com", "samsungcloud.com",
      "push.samsungosp.com"], "Android (Samsung)", "phone", 0.8),

    # Windows
    (["www.msftconnecttest.com", "dns.msftncsi.com",
      "settings-win.data.microsoft.com", "login.live.com",
      "windowsupdate.com", "ctldl.windowsupdate.com"], "Windows", "computer", 0.85),

    # Linux
    (["ntp.ubuntu.com", "changelogs.ubuntu.com",
      "security.ubuntu.com"], "Linux (Ubuntu)", "computer", 0.7),

    # Meta/Oculus VR
    (["graph.oculus.com", "oculus.com", "oculuscdn.com",
      "fbcdn.net"], "Meta Quest", "vr_headset", 0.85),

    # Oyun konsollari
    (["ps5.np.playstation.net", "psn.net", "playstation.com"], "PlayStation", "console", 0.9),
    (["xboxlive.com", "xsts.auth.xboxlive.com"], "Xbox", "console", 0.9),
    (["ctest.cdn.nintendo.net", "conntest.nintendowifi.net"], "Nintendo", "console", 0.9),

    # IoT - Espressif (ESP32/ESP8266)
    (["espressif.com"], "ESP-IDF", "iot", 0.9),

    # IoT - Cin firmwari
    (["baidu.com", "qq.com", "taobao.com", "weixin.qq.com"], "Chinese Firmware", "iot", 0.6),

    # Ag cihazlari
    (["tplinkcloud.com", "tplinkdns.com"], "TP-Link", "network_device", 0.85),

    # Genel IoT (sadece NTP - dusuk confidence)
    (["pool.ntp.org", "time.google.com", "time.cloudflare.com"], None, "iot", 0.25),
]

# Redis key TTL (1 saat pencere - daha fazla domain birikimi)
FINGERPRINT_TTL = 3600
# Minimum eşleşen domain sayısı (daha guclu kanit)
MIN_MATCHES_FOR_UPDATE = 1
# DB güncelleme aralığı (ayni cihaz için 5 dk'da bir)
UPDATE_COOLDOWN = 300

# NOT: Yukaridaki sabitler fallback degerleridir.
# Runtime'da Redis security:config HASH'ten dinamik okunur.

# Bellek ici cooldown - ayni IP için tekrar tekrar DB güncelleme yapma
_update_cooldowns: dict[str, float] = {}


async def analyze_fingerprint(client_ip: str, domain: str, qtype_name: str):
    """DNS sorgusundan cihaz fingerprint'i güncelle.

    Her sorgu için:
    1. Domain'i Redis SET'e ekle (IP bazli, 10 dk TTL)
    2. Pattern eslestirmesi yap
    3. Yeterli confidence varsa Device tablosunu güncelle
    """
    try:
        redis = await get_redis()

        # Domain'i normalize et
        normalized = domain.rstrip(".").lower()

        # Redis'ten dinamik TTL oku
        try:
            _fp_ttl_val = await redis.hget("security:config", "fingerprint_ttl")
            _fp_ttl = int(_fp_ttl_val) if _fp_ttl_val else FINGERPRINT_TTL
        except Exception:
            _fp_ttl = FINGERPRINT_TTL

        # Redis'e ekle (IP bazli domain gecmisi)
        fp_key = f"dns:fp:{client_ip}:domains"
        await redis.sadd(fp_key, normalized)

        # Ilk ekleme ise TTL ayarla
        ttl = await redis.ttl(fp_key)
        if ttl == -1:
            await redis.expire(fp_key, _fp_ttl)

        # Qtype istatistigi
        qt_key = f"dns:fp:{client_ip}:qtypes"
        await redis.hincrby(qt_key, qtype_name, 1)
        qt_ttl = await redis.ttl(qt_key)
        if qt_ttl == -1:
            await redis.expire(qt_key, _fp_ttl)

        # Cooldown kontrolü - ayni IP için cok sik güncelleme yapma
        import time
        now = time.monotonic()
        try:
            _upd_cd_val = await redis.hget("security:config", "fingerprint_update_cooldown")
            _upd_cd = int(_upd_cd_val) if _upd_cd_val else UPDATE_COOLDOWN
        except Exception:
            _upd_cd = UPDATE_COOLDOWN
        last_update = _update_cooldowns.get(client_ip, 0)
        if now - last_update < _upd_cd:
            return

        # Pattern eslestirmesi
        cached_domains = await redis.smembers(fp_key)
        # bytes -> str donusumu
        domain_set = {
            d.decode() if isinstance(d, bytes) else d
            for d in cached_domains
        }

        best_match = None
        best_confidence = 0.0
        best_matches = 0

        for indicators, detected_os, device_type, base_confidence in FINGERPRINT_RULES:
            matches = sum(1 for ind in indicators if ind in domain_set)
            if matches > 0:
                # Daha fazla eşleşen domain = daha yuksek confidence
                confidence = min(base_confidence + (matches - 1) * 0.05, 1.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = (detected_os, device_type)
                    best_matches = matches

        # Yeterli confidence varsa DB güncelle
        try:
            _min_m_val = await redis.hget("security:config", "fingerprint_min_matches")
            _min_matches = int(_min_m_val) if _min_m_val else MIN_MATCHES_FOR_UPDATE
        except Exception:
            _min_matches = MIN_MATCHES_FOR_UPDATE
        if best_match and best_confidence >= 0.7 and best_matches >= _min_matches:
            detected_os, device_type = best_match
            await _update_device_fingerprint(client_ip, detected_os, device_type)
            _update_cooldowns[client_ip] = now

    except Exception as e:
        logger.debug(f"Fingerprint analiz hatasi: {e}")


async def _update_device_fingerprint(
    client_ip: str,
    detected_os: str | None,
    device_type: str | None,
):
    """Device tablosundaki fingerprint alanlarini güncelle."""
    try:
        from sqlalchemy import select, update as sql_update

        async with async_session_factory() as session:
            result = await session.execute(
                select(Device).where(Device.ip_address == client_ip)
            )
            device = result.scalar_one_or_none()

            if not device:
                return

            changed = False

            # Hostname-tabanli tespit zaten yapilmissa ve farkli bir OS geliyorsa ezme
            # (hostname tespiti daha guvenilir: "iPhone" -> iOS, DNS fingerprint yanlislikla
            #  Google servisleri yuzunden Android diyebilir)
            if detected_os and not device.detected_os:
                device.detected_os = detected_os
                changed = True

            if device_type and not device.device_type:
                device.device_type = device_type
                changed = True

            if changed:
                await session.commit()
                logger.info(
                    f"Fingerprint güncellendi: {client_ip} -> "
                    f"OS={detected_os}, Tip={device_type}"
                )

    except Exception as e:
        logger.debug(f"Fingerprint DB güncelleme hatasi: {e}")


def cleanup_cooldowns():
    """Eski cooldown kayitlarini temizle."""
    import time
    now = time.monotonic()
    stale = [k for k, t in _update_cooldowns.items() if now - t > UPDATE_COOLDOWN * 2]
    for k in stale:
        _update_cooldowns.pop(k, None)

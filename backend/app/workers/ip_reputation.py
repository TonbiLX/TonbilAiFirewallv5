# --- Ajan: DEDEKTIF (THE DETECTIVE) ---
# IP Reputation Worker: AbuseIPDB ve GeoIP (ip-api.com) uzerinden
# aktif baglantilardaki dis IP adreslerinin itibar skorunu kontrol eder.
# Supheli IP'ler icin AiInsight yazar ve Telegram bildirimi gonderir.
#
# Calisma akisi:
#   - 180s baslangic gecikmesi (diger worker'lar hazir olsun)
#   - Her 300s: Redis'ten aktif flow IP'lerini topla
#   - Redis cache'de yoksa: AbuseIPDB + GeoIP sorgula (max 10/dongu)
#   - Skor >= 50: warning, skor >= 80: critical AiInsight + Telegram

import asyncio
import ipaddress
import json
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy import select, text

from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.models.ai_insight import AiInsight, Severity
from app.models.ip_reputation_check import IpReputationCheck
from app.models.ip_blacklist_entry import IpBlacklistEntry
from app.services.telegram_service import notify_ai_insight
from app.services.timezone_service import now_local, format_local_time
from app.workers.threat_analyzer import auto_block_ip

logger = logging.getLogger("tonbilai.ip_reputation")

# ─── Yapilandirma ───────────────────────────────────────────────────────────
STARTUP_DELAY        = 180   # saniye - baslangic gecikmesi
CHECK_INTERVAL       = 300   # saniye - dongu araligi
MAX_CHECKS_PER_CYCLE = 10    # dongu basina max IP kontrolu
DAILY_LIMIT          = 900   # AbuseIPDB gunluk limit tamponu (max 1000, 100 tampon)
CACHE_TTL            = 86400 # saniye - meta/sayac cache suresi (24 saat)
HTTP_TIMEOUT         = 10    # saniye - HTTP istek zaman asimi

ABUSEIPDB_URL       = "https://api.abuseipdb.com/api/v2/check"
ABUSEIPDB_CHECK_BLOCK_URL = "https://api.abuseipdb.com/api/v2/check-block"
GEOIP_URL       = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,isp,org,as,query"
GEOIP_BATCH_URL = "http://ip-api.com/batch"

# Redis anahtarlari
REDIS_KEY_API_KEY       = "reputation:abuseipdb_key"
REDIS_KEY_DAILY_CHECKS  = "reputation:daily_checks"
REDIS_KEY_IP_PREFIX     = "reputation:ip:"
REDIS_KEY_ACTIVE_IDS    = "flow:active_ids"
REDIS_KEY_FLOW_PREFIX   = "flow:live:"
REDIS_KEY_ENABLED       = "reputation:enabled"
REDIS_KEY_COUNTRIES     = "reputation:blocked_countries"

# Blacklist sabitleri
ABUSEIPDB_BLACKLIST_URL         = "https://api.abuseipdb.com/api/v2/blacklist"
BLACKLIST_MAX_DAILY             = 5       # AbuseIPDB blacklist gunluk limit (ucretsiz)
BLACKLIST_FETCH_INTERVAL        = 86400   # 24 saat (saniye)
REDIS_KEY_BLACKLIST_IPS         = "reputation:blacklist_ips"
REDIS_KEY_BLACKLIST_DATA_PREFIX = "reputation:blacklist_data:"
REDIS_KEY_BLACKLIST_LAST_FETCH  = "reputation:blacklist_last_fetch"
REDIS_KEY_BLACKLIST_COUNT       = "reputation:blacklist_count"
REDIS_KEY_BLACKLIST_DAILY       = "reputation:blacklist_daily_fetches"
REDIS_KEY_BLACKLIST_AUTO_BLOCK  = "reputation:blacklist_auto_block"
REDIS_KEY_BLACKLIST_MIN_SCORE   = "reputation:blacklist_min_score"
REDIS_KEY_BLACKLIST_LIMIT       = "reputation:blacklist_limit"

# Check-block (subnet analizi) sabitleri
ABUSEIPDB_CHECK_BLOCK_URL       = "https://api.abuseipdb.com/api/v2/check-block"
REDIS_KEY_CHECK_BLOCK_RESULTS   = "reputation:check_block_results"
REDIS_KEY_CHECK_BLOCK_PREFIX    = "reputation:check_block:"
CHECK_BLOCK_CACHE_TTL           = 86400   # 24 saat
CHECK_BLOCK_AUTO_THRESHOLD      = 3       # Subnet'te bu kadar kotu IP varsa otomatik subnet engelle
CHECK_BLOCK_MIN_SCORE           = 50      # Kotu IP sayimi icin esik skor


# ─── Yardimci fonksiyonlar ───────────────────────────────────────────────────

def is_public_ip(ip_str: str) -> bool:
    """Ozel/rezerve IP araliklarini filtrele — sadece genel IP'leri kabul et."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    # IPv6 loopback / link-local / ULA
    if addr.version == 6:
        return not (addr.is_private or addr.is_loopback or addr.is_link_local
                    or addr.is_multicast or addr.is_reserved or addr.is_unspecified)

    # IPv4 ozel araliklar
    private_networks = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),   # link-local
        ipaddress.ip_network("100.64.0.0/10"),    # shared address space
        ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
        ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
        ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
        ipaddress.ip_network("224.0.0.0/4"),      # multicast
        ipaddress.ip_network("240.0.0.0/4"),      # rezerve
        ipaddress.ip_network("255.255.255.255/32"),
    ]
    return not any(addr in net for net in private_networks)


async def check_abuseipdb(ip: str, api_key: str) -> dict | None:
    """AbuseIPDB API'sini sorgula. Hata durumunda None dondur."""
    try:
        from app.services.http_pool import get_client
        client = await get_client("abuseipdb", timeout=HTTP_TIMEOUT)
        response = await client.get(
            ABUSEIPDB_URL,
            headers={"Key": api_key, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90},
        )
            if response.status_code == 200:
                body = response.json()
                data = body.get("data", {})

                # AbuseIPDB gercek rate limit degerlerini Redis'e kaydet (1 saatlik TTL)
                try:
                    redis = await get_redis()
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    limit = response.headers.get("X-RateLimit-Limit")
                    if remaining is not None:
                        await redis.set("reputation:abuseipdb_remaining", str(remaining), ex=CACHE_TTL)
                    if limit is not None:
                        await redis.set("reputation:abuseipdb_limit", str(limit), ex=CACHE_TTL)
                except Exception as cache_exc:
                    logger.debug(f"Rate limit header kaydedilemedi: {cache_exc}")

                return {
                    "abuse_score": data.get("abuseConfidenceScore", 0),
                    "total_reports": data.get("totalReports", 0),
                    "country": data.get("countryCode", "??"),
                }
            elif response.status_code == 429:
                logger.warning("AbuseIPDB rate limit asild — gunluk kota dolmus olabilir.")
            else:
                logger.debug(f"AbuseIPDB {ip} yaniti: HTTP {response.status_code}")
    except httpx.TimeoutException:
        logger.debug(f"AbuseIPDB {ip} sorgusu zaman asimina ugradi.")
    except Exception as exc:
        logger.debug(f"AbuseIPDB {ip} hatasi: {exc}")
    return None


async def check_geoip(ip: str) -> dict | None:
    """ip-api.com uzerinden GeoIP bilgisi al. Hata durumunda None dondur."""
    try:
        from app.services.http_pool import get_client
        client = await get_client("geoip", timeout=HTTP_TIMEOUT)
        response = await client.get(GEOIP_URL.format(ip=ip))
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "country":      data.get("country", ""),
                    "country_code": data.get("countryCode", "??"),
                    "city":         data.get("city", ""),
                    "isp":          data.get("isp", ""),
                    "org":          data.get("org", ""),
                    "asn":          data.get("as", ""),
                }
        logger.debug(f"GeoIP {ip} yaniti: HTTP {response.status_code}")
    except httpx.TimeoutException:
        logger.debug(f"GeoIP {ip} sorgusu zaman asimina ugradi.")
    except Exception as exc:
        logger.debug(f"GeoIP {ip} hatasi: {exc}")
    return None


async def check_geoip_batch(ips: list[str]) -> dict[str, dict]:
    """ip-api.com batch API — 100 IP tek istekte sorgula."""
    if not ips:
        return {}
    try:
        from app.services.http_pool import get_client
        client = await get_client("geoip", timeout=HTTP_TIMEOUT)
        payload = [
            {"query": ip, "fields": "status,country,countryCode,city,isp,org,as,query"}
            for ip in ips[:100]
        ]
        response = await client.post(GEOIP_BATCH_URL, json=payload)
        if response.status_code == 200:
            results = {}
            for item in response.json():
                if item.get("status") == "success":
                    results[item["query"]] = {
                        "country":      item.get("country", ""),
                        "country_code": item.get("countryCode", "??"),
                        "city":         item.get("city", ""),
                        "isp":          item.get("isp", ""),
                        "org":          item.get("org", ""),
                        "asn":          item.get("as", ""),
                    }
            logger.info(f"GeoIP batch: {len(ips)} IP sorgulanacak, {len(results)} sonuc")
            return results
        logger.debug(f"GeoIP batch yaniti: HTTP {response.status_code}")
    except Exception as exc:
        logger.warning(f"GeoIP batch hatasi: {exc}")
    return {}


def _get_cache_ttl(abuse_score: int) -> int:
    """Skor bazli dinamik cache suresi (saniye)."""
    if abuse_score >= 80:
        return 6 * 3600      # 6 saat — kritik, sik guncelle
    elif abuse_score >= 50:
        return 12 * 3600     # 12 saat
    elif abuse_score > 0:
        return 24 * 3600     # 24 saat
    else:
        return 7 * 86400     # 7 gun — temiz IP


async def get_reputation_summary() -> dict:
    """
    Tum cache'li IP itibar verilerinin ozetini dondur.
    API endpoint tarafindan kullanilmak uzere tasarlandi.
    """
    redis = await get_redis()
    summary = {
        "total_checked": 0,
        "flagged_critical": 0,
        "flagged_warning":  0,
        "daily_checks_used": 0,
        "ips": [],
    }
    try:
        daily = await redis.get(REDIS_KEY_DAILY_CHECKS)
        summary["daily_checks_used"] = int(daily) if daily else 0

        # Tum reputation:ip:* anahtarlarini tara
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=f"{REDIS_KEY_IP_PREFIX}*", count=200)
            for key in keys:
                data = await redis.hgetall(key)
                if not data:
                    continue
                ip_addr = key.removeprefix(REDIS_KEY_IP_PREFIX)
                score = int(data.get("abuse_score", 0))
                entry = {
                    "ip":           ip_addr,
                    "abuse_score":  score,
                    "total_reports": int(data.get("total_reports", 0)),
                    "country":      data.get("country", ""),
                    "city":         data.get("city", ""),
                    "isp":          data.get("isp", ""),
                    "checked_at":   data.get("checked_at", ""),
                }
                summary["ips"].append(entry)
                summary["total_checked"] += 1
                if score >= 80:
                    summary["flagged_critical"] += 1
                elif score >= 50:
                    summary["flagged_warning"] += 1
            if cursor == 0:
                break

        # Skora gore sirala (en yuksek once)
        summary["ips"].sort(key=lambda x: x["abuse_score"], reverse=True)
    except Exception as exc:
        logger.error(f"get_reputation_summary hatasi: {exc}")
    return summary


# ─── Temel is mantigi ────────────────────────────────────────────────────────

async def _get_active_external_ips() -> set[str]:
    """Redis'teki aktif flow'lardan dis IP adreslerini topla."""
    redis = await get_redis()
    external_ips: set[str] = set()
    try:
        flow_ids = await redis.smembers(REDIS_KEY_ACTIVE_IDS)
        for flow_id in flow_ids:
            try:
                flow_data = await redis.hgetall(f"{REDIS_KEY_FLOW_PREFIX}{flow_id}")
                # dst_ip → outbound baglantilarda hedef
                dst_ip = flow_data.get("dst_ip", "")
                if dst_ip and is_public_ip(dst_ip):
                    external_ips.add(dst_ip)
                # src_ip → inbound baglantilarda kaynak
                src_ip = flow_data.get("src_ip", "")
                if src_ip and is_public_ip(src_ip):
                    external_ips.add(src_ip)
            except Exception:
                continue
    except Exception as exc:
        logger.error(f"Aktif IP listesi alinamadi: {exc}")
    return external_ips


async def _increment_daily_counter(redis) -> int:
    """Gunluk AbuseIPDB sayacini artir ve mevcut degeri dondur."""
    try:
        count = await redis.incr(REDIS_KEY_DAILY_CHECKS)
        # Her artirmada TTL kontrolu — gun sinirini gecmemek icin
        ttl = await redis.ttl(REDIS_KEY_DAILY_CHECKS)
        if ttl == -1:
            # TTL yok (manuel reset veya eski veri) — yeniden ayarla
            await redis.expire(REDIS_KEY_DAILY_CHECKS, CACHE_TTL)
        return count
    except Exception:
        return DAILY_LIMIT  # Hata durumunda limiti as gibi davran


async def _write_ai_insight(severity: Severity, message: str, action: str, category: str = "reputation") -> None:
    """AiInsight modeline yaz ve Telegram bildirimi gonder."""
    try:
        async with async_session_factory() as session:
            insight = AiInsight(
                severity=severity,
                message=message,
                suggested_action=action,
                category=category,
            )
            session.add(insight)
            await session.commit()
        await notify_ai_insight(severity.value, message, category)
    except Exception as exc:
        logger.error(f"AiInsight yazma hatasi: {exc}")


async def _process_ip(ip: str, api_key: str | None, redis, geo_data: dict | None = None) -> bool:
    """
    Tek bir IP adresini kontrol et, sonuclari cache'le ve gerekirse uyari olustur.
    True dondururse AbuseIPDB kullanildi (sayac artirimi icin).

    geo_data: Batch GeoIP'den onhazir veri (verilmisse tek IP sorgusu yapilmaz).
    """
    abuse_data: dict | None = None
    used_abuseipdb = False

    # ── AbuseIPDB kontrolu (API anahtari varsa ve kota dolmadiysa) ──
    if api_key:
        daily_count = await _increment_daily_counter(redis)
        # Gercek AbuseIPDB kalan hak sayisini kontrol et (X-RateLimit-Remaining header'dan)
        api_remaining = await redis.get("reputation:abuseipdb_remaining")
        api_has_quota = api_remaining is not None and int(api_remaining) > 0

        if daily_count <= DAILY_LIMIT or api_has_quota:
            abuse_data = await check_abuseipdb(ip, api_key)
            used_abuseipdb = True
            # Basarili cagri sonrasi yerel sayaci gercek API verisiyle senkronize et
            if abuse_data:
                try:
                    real_remaining = await redis.get("reputation:abuseipdb_remaining")
                    real_limit = await redis.get("reputation:abuseipdb_limit")
                    if real_remaining is not None and real_limit is not None:
                        synced_count = int(real_limit) - int(real_remaining)
                        await redis.set(REDIS_KEY_DAILY_CHECKS, str(synced_count))
                        # TTL yoksa yeniden ayarla
                        ttl = await redis.ttl(REDIS_KEY_DAILY_CHECKS)
                        if ttl == -1:
                            await redis.expire(REDIS_KEY_DAILY_CHECKS, CACHE_TTL)
                        logger.debug(
                            f"Yerel sayac senkronize edildi: {synced_count}/{int(real_limit)} "
                            f"(AbuseIPDB kalan: {real_remaining})"
                        )
                except Exception:
                    pass
        else:
            logger.debug(f"AbuseIPDB gunluk kota doldu ({daily_count}/{DAILY_LIMIT}), {ip} atlanıyor.")
            # Sayaci geri al (bosu bosuna arttirdik)
            await redis.decr(REDIS_KEY_DAILY_CHECKS)

    # ── GeoIP kontrolu (batch'ten gelmediyse tek sorgu yap) ──
    if geo_data is None:
        geo_data = await check_geoip(ip)

    # ── Sonuclari birlestir ──
    abuse_score    = int((abuse_data or {}).get("abuse_score", 0))
    total_reports  = int((abuse_data or {}).get("total_reports", 0))
    country        = (abuse_data or geo_data or {}).get("country", "")
    country_code   = (abuse_data or {}).get("country", (geo_data or {}).get("country_code", "??"))
    city           = (geo_data or {}).get("city", "")
    isp            = (geo_data or {}).get("isp", "")
    org            = (geo_data or {}).get("org", "")
    checked_at     = format_local_time()

    # ── Redis cache ──
    cache_key = f"{REDIS_KEY_IP_PREFIX}{ip}"
    cache_payload = {
        "abuse_score":   str(abuse_score),
        "total_reports": str(total_reports),
        "country":       country,
        "country_code":  country_code,
        "city":          city,
        "isp":           isp,
        "org":           org,
        "checked_at":    checked_at,
    }
    try:
        await redis.hset(cache_key, mapping=cache_payload)
        ttl = _get_cache_ttl(abuse_score)
        await redis.expire(cache_key, ttl)
    except Exception as exc:
        logger.warning(f"Redis cache yazma hatasi {ip}: {exc}")

    # ── SQL kalici kayit (UPSERT) ──
    try:
        async with async_session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO ip_reputation_checks "
                    "(ip_address, abuse_score, total_reports, country, country_code, city, isp, org, checked_at) "
                    "VALUES (:ip, :score, :reports, :country, :cc, :city, :isp, :org, NOW()) "
                    "ON DUPLICATE KEY UPDATE "
                    "abuse_score=:score, total_reports=:reports, country=:country, country_code=:cc, "
                    "city=:city, isp=:isp, org=:org, checked_at=NOW()"
                ),
                {"ip": ip, "score": abuse_score, "reports": total_reports,
                 "country": country, "cc": country_code, "city": city, "isp": isp, "org": org},
            )
            await session.commit()
    except Exception as sql_exc:
        logger.warning(f"SQL UPSERT hatasi {ip}: {sql_exc}")

    # ── Uyari olusturma ──
    location_str = ", ".join(filter(None, [city, country]))
    isp_str = isp or org or "Bilinmiyor"

    if abuse_score >= 80:
        message = (
            f"KRITIK IP tehdidi tespit edildi: {ip} "
            f"(Skor: {abuse_score}/100, Raporlar: {total_reports}, "
            f"Konum: {location_str}, ISP: {isp_str})"
        )
        action = (
            f"'{ip}' adresini guvenim duvarinda engelleyin. "
            f"Bu IP icin {total_reports} abus raporu bulunuyor."
        )
        logger.warning(f"[KRITIK] {message}")
        await _write_ai_insight(Severity.CRITICAL, message, action)
        # OTOMATIK ENGELLEME
        await auto_block_ip(ip, f"AbuseIPDB kritik skor: {abuse_score}/100, raporlar: {total_reports}")
        # OTOMATIK SUBNET KONTROLU — kritik IP'nin /24 blogu analiz edilir
        if api_key:
            asyncio.create_task(_check_block_for_critical_ip(ip, api_key))

    elif abuse_score >= 50:
        message = (
            f"Supheli IP tespit edildi: {ip} "
            f"(Skor: {abuse_score}/100, Raporlar: {total_reports}, "
            f"Konum: {location_str}, ISP: {isp_str})"
        )
        action = (
            f"'{ip}' adresini izleyin. "
            f"Gerekirse guvenim duvarinda engelleyin."
        )
        logger.info(f"[UYARI] {message}")
        await _write_ai_insight(Severity.WARNING, message, action)

    elif geo_data:
        # Tehdit yok ama GeoIP bilgisi alindi, sadece loglama
        logger.debug(f"[OK] {ip} — skor: {abuse_score}, konum: {location_str}, ISP: {isp_str}")

    return used_abuseipdb


async def fetch_abuseipdb_blacklist(force: bool = False) -> dict:
    """
    AbuseIPDB blacklist endpoint'inden en tehlikeli IP'leri indir.
    Gunluk 5 sorgu limiti var (ucretsiz hesap).
    Returns: {"status": "ok"/"error", "count": N, "blocked": M, "message": "..."}
    """
    redis = await get_redis()

    # API key kontrolu
    api_key = await redis.get(REDIS_KEY_API_KEY)
    if not api_key or not api_key.strip():
        return {"status": "error", "count": 0, "blocked": 0, "message": "API anahtari ayarlanmamis"}
    api_key = api_key.strip()

    # Gunluk fetch limiti kontrolu
    if not force:
        daily_raw = await redis.get(REDIS_KEY_BLACKLIST_DAILY)
        daily_fetches = int(daily_raw) if daily_raw else 0
        if daily_fetches >= BLACKLIST_MAX_DAILY:
            return {"status": "error", "count": 0, "blocked": 0, "message": f"Gunluk blacklist limiti doldu ({daily_fetches}/{BLACKLIST_MAX_DAILY})"}

    # Ayarlari oku
    min_score_raw = await redis.get(REDIS_KEY_BLACKLIST_MIN_SCORE)
    limit_raw = await redis.get(REDIS_KEY_BLACKLIST_LIMIT)
    auto_block_raw = await redis.get(REDIS_KEY_BLACKLIST_AUTO_BLOCK)

    min_score = int(min_score_raw) if min_score_raw else 100
    limit = int(limit_raw) if limit_raw else 10000
    auto_block = (auto_block_raw != "0") if auto_block_raw is not None else True

    # API cagirisi
    try:
        from app.services.http_pool import get_client
        client = await get_client("abuseipdb", timeout=30)
        response = await client.get(
            ABUSEIPDB_BLACKLIST_URL,
            headers={"Key": api_key, "Accept": "application/json"},
            params={"confidenceMinimum": min_score, "limit": limit},
        )

        if response.status_code != 200:
            msg = f"AbuseIPDB blacklist hatasi: HTTP {response.status_code}"
            logger.warning(msg)
            return {"status": "error", "count": 0, "blocked": 0, "message": msg}

        # Blacklist API rate limit header'larini kaydet
        try:
            bl_remaining = response.headers.get("X-RateLimit-Remaining")
            bl_limit = response.headers.get("X-RateLimit-Limit")
            if bl_remaining is not None:
                await redis.set("reputation:blacklist_api_remaining", str(bl_remaining), ex=86400)
            if bl_limit is not None:
                await redis.set("reputation:blacklist_api_limit", str(bl_limit), ex=86400)
            if bl_remaining is not None and bl_limit is not None:
                logger.info(f"AbuseIPDB blacklist rate limit: {bl_remaining}/{bl_limit}")
        except Exception as rl_exc:
            logger.debug(f"Blacklist rate limit header kaydi basarisiz: {rl_exc}")

        body = response.json()
        ip_list = body.get("data", [])

        # Eski blacklist verisini temizle
        old_ips = await redis.smembers(REDIS_KEY_BLACKLIST_IPS)
        if old_ips:
            pipe = redis.pipeline()
            for old_ip in old_ips:
                pipe.delete(f"{REDIS_KEY_BLACKLIST_DATA_PREFIX}{old_ip}")
            pipe.delete(REDIS_KEY_BLACKLIST_IPS)
            await pipe.execute()

        # Yeni verileri kaydet
        blocked_count = 0
        if ip_list:
            pipe = redis.pipeline()
            for item in ip_list:
                ip_addr = item.get("ipAddress", "")
                if not ip_addr:
                    continue
                pipe.sadd(REDIS_KEY_BLACKLIST_IPS, ip_addr)
                pipe.hset(f"{REDIS_KEY_BLACKLIST_DATA_PREFIX}{ip_addr}", mapping={
                    "ip": ip_addr,
                    "abuse_score": str(item.get("abuseConfidenceScore", 0)),
                    "country": item.get("countryCode", ""),
                    "last_reported_at": item.get("lastReportedAt", ""),
                })
                pipe.expire(f"{REDIS_KEY_BLACKLIST_DATA_PREFIX}{ip_addr}", BLACKLIST_FETCH_INTERVAL * 2)
            await pipe.execute()

        count = len(ip_list)

        # ── SQL kalici kayit (blacklist) ──
        try:
            async with async_session_factory() as session:
                # Eski kayitlari temizle
                await session.execute(text("DELETE FROM ip_blacklist_entries"))
                # Yeni kayitlari batch ekle (1000'er)
                batch = []
                for item in ip_list:
                    ip_addr = item.get("ipAddress", "")
                    if not ip_addr:
                        continue
                    batch.append({
                        "ip":       ip_addr,
                        "score":    item.get("abuseConfidenceScore", 0),
                        "country":  item.get("countryCode", ""),
                        "reported": item.get("lastReportedAt", ""),
                    })
                    if len(batch) >= 1000:
                        await session.execute(
                            text(
                                "INSERT INTO ip_blacklist_entries "
                                "(ip_address, abuse_score, country, last_reported_at, fetched_at) "
                                "VALUES (:ip, :score, :country, :reported, NOW())"
                            ),
                            batch,
                        )
                        batch = []
                if batch:
                    await session.execute(
                        text(
                            "INSERT INTO ip_blacklist_entries "
                            "(ip_address, abuse_score, country, last_reported_at, fetched_at) "
                            "VALUES (:ip, :score, :country, :reported, NOW())"
                        ),
                        batch,
                    )
                await session.commit()
                logger.info(f"Blacklist SQL: {len(ip_list)} IP yazildi")
        except Exception as sql_exc:
            logger.warning(f"Blacklist SQL yazma hatasi: {sql_exc}")

        # Auto-block (toplu — Telegram/AiInsight gondermeden, sonra tek ozet)
        if auto_block and ip_list:
            block_dur_raw = await redis.get("block_duration_sec")
            block_dur = int(block_dur_raw) if block_dur_raw else 3600
            now_iso = datetime.utcnow().isoformat()
            pipe_block = redis.pipeline()
            for item in ip_list[:500]:
                ip_addr = item.get("ipAddress", "")
                score = item.get("abuseConfidenceScore", 0)
                if ip_addr and score >= min_score:
                    pipe_block.sadd("dns:threat:blocked", ip_addr)
                    pipe_block.set(f"dns:threat:block_expire:{ip_addr}",
                                   f"AbuseIPDB blacklist (skor: {score})", ex=block_dur)
                    pipe_block.set(f"dns:threat:block_time:{ip_addr}", now_iso, ex=block_dur)
                    blocked_count += 1
            if blocked_count > 0:
                await pipe_block.execute()
                await redis.hincrby("dns:threat:stats", "total_auto_blocks", blocked_count)
                # Tek ozet bildirim
                summary_msg = (
                    f"AbuseIPDB Kara Liste: {blocked_count} IP otomatik engellendi "
                    f"(toplam {count} IP indirildi, min skor: {min_score})"
                )
                await _write_ai_insight(Severity.WARNING, summary_msg,
                                        "Kara liste otomatik engelleme tamamlandi.")
                logger.info(summary_msg)

        # Meta veri guncelle (UTC ISO format — timezone kaymasini onlemek icin)
        await redis.set(REDIS_KEY_BLACKLIST_LAST_FETCH, datetime.utcnow().isoformat() + "Z")
        await redis.set(REDIS_KEY_BLACKLIST_COUNT, str(count))
        await redis.expire(REDIS_KEY_BLACKLIST_IPS, BLACKLIST_FETCH_INTERVAL * 2)

        # Gunluk sayaci artir
        fetch_count = await redis.incr(REDIS_KEY_BLACKLIST_DAILY)
        if fetch_count == 1:
            await redis.expire(REDIS_KEY_BLACKLIST_DAILY, CACHE_TTL)
        ttl = await redis.ttl(REDIS_KEY_BLACKLIST_DAILY)
        if ttl == -1:
            await redis.expire(REDIS_KEY_BLACKLIST_DAILY, CACHE_TTL)

        logger.info(f"AbuseIPDB blacklist: {count} IP indirildi, {blocked_count} otomatik engellendi")
        return {"status": "ok", "count": count, "blocked": blocked_count, "message": f"{count} IP indirildi, {blocked_count} engellendi"}

    except httpx.TimeoutException:
        return {"status": "error", "count": 0, "blocked": 0, "message": "AbuseIPDB baglantisi zaman asimina ugradi"}
    except Exception as exc:
        logger.error(f"Blacklist fetch hatasi: {exc}")
        return {"status": "error", "count": 0, "blocked": 0, "message": f"Hata: {exc}"}


async def check_abuseipdb_block(subnet: str, api_key: str | None = None,
                                auto_block: bool = True) -> dict:
    """
    AbuseIPDB check-block endpoint ile bir subnet'i (CIDR) analiz et.
    Subnet icindeki raporlanmis IP'leri dondurur ve esik asilirsa otomatik subnet engeller.

    Returns: {"status": "ok"/"error", "network": str, "reported_ips": list,
              "total_reported": int, "malicious_count": int, "subnet_blocked": bool, "message": str}
    """
    redis = await get_redis()

    # API key — parametre veya Redis'ten
    if not api_key:
        api_key = await redis.get(REDIS_KEY_API_KEY)
        if api_key:
            api_key = api_key.strip()
    if not api_key:
        return {"status": "error", "network": subnet, "reported_ips": [],
                "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                "message": "API anahtari ayarlanmamis"}

    # CIDR dogrulama
    try:
        net = ipaddress.ip_network(subnet, strict=False)
        subnet = str(net)  # normalize (192.168.1.5/24 → 192.168.1.0/24)
    except ValueError:
        return {"status": "error", "network": subnet, "reported_ips": [],
                "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                "message": f"Gecersiz CIDR formati: {subnet}"}

    # Prefix sinirlama (ucretsiz plan: max /20)
    if net.prefixlen < 20:
        return {"status": "error", "network": subnet, "reported_ips": [],
                "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                "message": f"Subnet cok genis (/{net.prefixlen}). Ucretsiz plan icin min /20 gerekli."}

    # Cache kontrolu (24 saat)
    cache_key = f"{REDIS_KEY_CHECK_BLOCK_PREFIX}{subnet}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"check-block cache hit: {subnet}")
            return json.loads(cached)
    except Exception:
        pass

    # AbuseIPDB check-block API cagrisi
    try:
        from app.services.http_pool import get_client
        client = await get_client("abuseipdb", timeout=30)
        response = await client.get(
            ABUSEIPDB_CHECK_BLOCK_URL,
            headers={"Key": api_key, "Accept": "application/json"},
            params={"network": subnet, "maxAgeInDays": 30},
        )

        # Rate limit header kaydet — check-block AYRI havuz (check endpoint'ten farkli!)
        try:
            remaining = response.headers.get("X-RateLimit-Remaining")
            limit_h = response.headers.get("X-RateLimit-Limit")
            if remaining is not None:
                await redis.set("reputation:check_block_api_remaining", str(remaining), ex=CACHE_TTL)
            if limit_h is not None:
                await redis.set("reputation:check_block_api_limit", str(limit_h), ex=CACHE_TTL)
        except Exception:
            pass

        if response.status_code == 402:
            return {"status": "error", "network": subnet, "reported_ips": [],
                    "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                    "message": "Subnet boyutu plan limitini asiyor (402 Payment Required)"}
        if response.status_code == 429:
            return {"status": "error", "network": subnet, "reported_ips": [],
                    "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                    "message": "AbuseIPDB gunluk kota dolmus (429)"}
        if response.status_code != 200:
            return {"status": "error", "network": subnet, "reported_ips": [],
                    "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                    "message": f"AbuseIPDB check-block hatasi: HTTP {response.status_code}"}

        body = response.json()
        data = body.get("data", {})
        reported_addresses = data.get("reportedAddress", [])

        # Sonuclari isle
        reported_ips = []
        malicious_count = 0
        for addr in reported_addresses:
            ip_addr = addr.get("ipAddress", "")
            score = addr.get("abuseConfidenceScore", 0)
            num_reports = addr.get("numReports", 0)
            most_recent = addr.get("mostRecentReport", "")
            country = addr.get("countryCode", "")

            reported_ips.append({
                "ip": ip_addr,
                "abuse_score": score,
                "num_reports": num_reports,
                "most_recent_report": most_recent,
                "country": country,
            })
            if score >= CHECK_BLOCK_MIN_SCORE:
                malicious_count += 1

        total_reported = len(reported_ips)
        subnet_blocked = False

        # Otomatik subnet engelleme: esik asilirsa nftables'a kural ekle
        if auto_block and malicious_count >= CHECK_BLOCK_AUTO_THRESHOLD:
            try:
                from app.hal.linux_nftables import add_blocked_subnet
                await add_blocked_subnet(subnet, timeout_seconds=86400)  # 24 saat
                subnet_blocked = True
                logger.warning(
                    f"[SUBNET ENGEL] {subnet} otomatik engellendi: "
                    f"{malicious_count} kotu IP (esik: {CHECK_BLOCK_AUTO_THRESHOLD})"
                )
                # AiInsight + Telegram
                await _write_ai_insight(
                    Severity.CRITICAL,
                    f"Tehlikeli subnet tespit ve engellendi: {subnet} — "
                    f"{malicious_count}/{total_reported} IP skoru >={CHECK_BLOCK_MIN_SCORE} "
                    f"(toplam {data.get('numPossibleHosts', '?')} host)",
                    f"'{subnet}' subnet'i 24 saat sure ile otomatik engellendi. "
                    f"Engel surecini IP Yonetimi sayfasindan yonetebilirsiniz.",
                )
            except Exception as block_exc:
                logger.error(f"Subnet engelleme hatasi {subnet}: {block_exc}")

        result = {
            "status": "ok",
            "network": subnet,
            "network_address": data.get("networkAddress", ""),
            "netmask": data.get("netmask", ""),
            "min_address": data.get("minAddress", ""),
            "max_address": data.get("maxAddress", ""),
            "num_possible_hosts": data.get("numPossibleHosts", 0),
            "address_space_desc": data.get("addressSpaceDesc", ""),
            "reported_ips": reported_ips,
            "total_reported": total_reported,
            "malicious_count": malicious_count,
            "subnet_blocked": subnet_blocked,
            "message": (
                f"{subnet}: {total_reported} raporlanmis IP, {malicious_count} tehlikeli"
                + (f" — SUBNET ENGELLENDİ" if subnet_blocked else "")
            ),
        }

        # Cache'e yaz (24 saat)
        try:
            await redis.set(cache_key, json.dumps(result), ex=CHECK_BLOCK_CACHE_TTL)
            # Sonuc listesine ekle
            await redis.zadd(REDIS_KEY_CHECK_BLOCK_RESULTS, {subnet: malicious_count})
            await redis.expire(REDIS_KEY_CHECK_BLOCK_RESULTS, CHECK_BLOCK_CACHE_TTL)
        except Exception:
            pass

        logger.info(
            f"check-block {subnet}: {total_reported} reported, {malicious_count} malicious"
            + (", BLOCKED" if subnet_blocked else "")
        )
        return result

    except httpx.TimeoutException:
        return {"status": "error", "network": subnet, "reported_ips": [],
                "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                "message": "AbuseIPDB baglantisi zaman asimina ugradi"}
    except Exception as exc:
        logger.error(f"check-block hatasi {subnet}: {exc}")
        return {"status": "error", "network": subnet, "reported_ips": [],
                "total_reported": 0, "malicious_count": 0, "subnet_blocked": False,
                "message": f"Hata: {exc}"}


async def _check_block_for_critical_ip(ip: str, api_key: str) -> None:
    """
    Kritik skor (>=80) olan bir IP'nin /24 subnet'ini otomatik kontrol et.
    _process_ip icinden tetiklenir.
    """
    try:
        net = ipaddress.ip_network(f"{ip}/24", strict=False)
        subnet = str(net)
        redis = await get_redis()
        # Ayni subnet zaten kontrol edildiyse atla
        cached = await redis.get(f"{REDIS_KEY_CHECK_BLOCK_PREFIX}{subnet}")
        if cached:
            return
        logger.info(f"Kritik IP {ip} nedeniyle subnet kontrol baslatiliyor: {subnet}")
        await check_abuseipdb_block(subnet, api_key, auto_block=True)
    except Exception as exc:
        logger.debug(f"Otomatik subnet kontrolu basarisiz {ip}: {exc}")


async def _get_blocked_countries(redis) -> list[str]:
    """Redis'ten engellenen ulke kodlari listesini oku (JSON parse)."""
    try:
        raw = await redis.get(REDIS_KEY_COUNTRIES)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"blocked_countries okunamadi: {exc}")
    return []


async def _check_country_block(ip: str, country_code: str, blocked_countries: list[str]) -> None:
    """
    IP'nin ulkesi engellenen ulkeler listesindeyse critical AiInsight yaz.
    Bu kontrol AbuseIPDB skorundan bagimsiz calisir.
    """
    if not blocked_countries or not country_code:
        return
    if country_code.upper() not in [c.upper() for c in blocked_countries]:
        return

    message = (
        f"Engellenen ulkeden baglanti tespit edildi: {ip} "
        f"(Ulke: {country_code}) — Ulke engelleme listesinde mevcut."
    )
    action = (
        f"'{ip}' adresini guvenlik duvarinda engelleyin. "
        f"Bu IP engellenen ulke listesindeki '{country_code}' ulkesine ait."
    )
    logger.warning(f"[ULKE ENGEL] {message}")
    await _write_ai_insight(Severity.CRITICAL, message, action, category="country_block")
    # OTOMATIK ENGELLEME
    await auto_block_ip(ip, f"Engellenen ulke: {country_code}")


async def _run_reputation_cycle() -> None:
    """Tek bir itibar kontrol dongusunu calistir."""
    redis = await get_redis()

    # ── Enabled bayragi kontrolu ──
    try:
        enabled_raw = await redis.get(REDIS_KEY_ENABLED)
        # Key yoksa varsayilan olarak etkin; "0" ise devre disi
        if enabled_raw == "0":
            logger.debug("IP reputation worker devre disi (reputation:enabled=0). Dongu atlaniyor.")
            return
    except Exception as exc:
        logger.warning(f"reputation:enabled okunamadi: {exc}")

    # ── Blacklist otomatik fetch (24 saatte 1) ──
    try:
        last_fetch_raw = await redis.get(REDIS_KEY_BLACKLIST_LAST_FETCH)
        should_fetch = True
        if last_fetch_raw:
            # Son fetch'ten bu yana 24 saat gecti mi?
            try:
                # UTC ISO formatini parse et ("Z" ve "+00:00" suffix'lerini kaldir → naive UTC datetime)
                clean = last_fetch_raw.replace("Z", "").replace("+00:00", "")
                # Eski format uyumlulugu: "HH:MM:SS DD/MM/YYYY" gibi local format → parse hatasi
                # verilebilir; except blogu should_fetch=True birakmak icin kullanilir (guvenli)
                last_dt = datetime.fromisoformat(clean)
                if (datetime.utcnow() - last_dt).total_seconds() < BLACKLIST_FETCH_INTERVAL:
                    should_fetch = False
            except Exception:
                # Parse hatasi → eski format veya bozuk veri → yeniden fetch tetikle (guvenli)
                pass
        if should_fetch:
            logger.info("Blacklist otomatik fetch baslatiliyor...")
            await fetch_abuseipdb_blacklist()
    except Exception as exc:
        logger.warning(f"Blacklist auto-fetch hatasi: {exc}")

    # ── Engellenen ulkeler listesini al ──
    blocked_countries = await _get_blocked_countries(redis)
    if blocked_countries:
        logger.debug(f"Engellenen ulkeler: {blocked_countries}")

    # AbuseIPDB API anahtarini Redis'ten al
    api_key: str | None = None
    try:
        api_key = await redis.get(REDIS_KEY_API_KEY)
        if api_key:
            api_key = api_key.strip()
    except Exception as exc:
        logger.warning(f"AbuseIPDB API anahtari okunamadi: {exc}")

    if not api_key:
        logger.debug("AbuseIPDB API anahtari yapilandirilmamis — sadece GeoIP kontrolu yapilacak.")

    # Aktif dis IP'leri topla
    all_external_ips = await _get_active_external_ips()
    if not all_external_ips:
        logger.debug("Aktif dis baglanti bulunamadi.")
        return

    # Zaten cache'li olanlari filtrele
    unchecked_ips: list[str] = []
    for ip in all_external_ips:
        try:
            exists = await redis.exists(f"{REDIS_KEY_IP_PREFIX}{ip}")
            if not exists:
                unchecked_ips.append(ip)
        except Exception:
            unchecked_ips.append(ip)

    if not unchecked_ips:
        logger.debug(f"Tum {len(all_external_ips)} IP zaten cache'li.")
        return

    # Bu dongude max 10 IP kontrol et
    to_check = unchecked_ips[:MAX_CHECKS_PER_CYCLE]
    logger.info(
        f"IP itibar kontrolu: {len(all_external_ips)} aktif IP, "
        f"{len(unchecked_ips)} yeni, bu dongude {len(to_check)} kontrol edilecek."
    )

    # Batch GeoIP: tum IP'ler icin tek sorgu (10 IP -> 1 istek)
    geo_batch = await check_geoip_batch(to_check)

    checked_count = 0
    flagged_count = 0

    for ip in to_check:
        try:
            geo_data = geo_batch.get(ip)
            await _process_ip(ip, api_key, redis, geo_data=geo_data)
            checked_count += 1

            # Cache'den abuse_score ve country_code oku (flagged sayisi + ulke kontrolu icin)
            cached_score = await redis.hget(f"{REDIS_KEY_IP_PREFIX}{ip}", "abuse_score")
            cached_country = await redis.hget(f"{REDIS_KEY_IP_PREFIX}{ip}", "country_code")

            if cached_score and int(cached_score) >= 50:
                flagged_count += 1

            # Ulke engelleme kontrolu (AbuseIPDB skorundan bagimsiz)
            if blocked_countries and cached_country:
                await _check_country_block(ip, cached_country, blocked_countries)

        except Exception as exc:
            logger.error(f"IP isleme hatasi {ip}: {exc}", exc_info=True)

    logger.info(
        f"IP itibar: {checked_count} kontrol edildi, {flagged_count} isaretlendi "
        f"(toplam dis IP: {len(all_external_ips)})"
    )


# ─── Ana worker girisi ───────────────────────────────────────────────────────

async def start_ip_reputation() -> None:
    """
    IP itibar worker'ini baslat.
    main.py'deki lifespan fonksiyonunda asyncio.create_task() ile cagrilir.
    """
    logger.info(f"IP reputation worker basliyor — {STARTUP_DELAY}s bekleniyor...")
    await asyncio.sleep(STARTUP_DELAY)
    logger.info("IP reputation worker aktif.")

    while True:
        try:
            await _run_reputation_cycle()
        except asyncio.CancelledError:
            logger.info("IP reputation worker durduruldu.")
            break
        except Exception as exc:
            logger.error(f"IP reputation dongu hatasi: {exc}", exc_info=True)

        try:
            await asyncio.sleep(CHECK_INTERVAL)
        except asyncio.CancelledError:
            logger.info("IP reputation worker durduruldu.")
            break

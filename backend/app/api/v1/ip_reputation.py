# --- Ajan: DEDEKTIF (THE DETECTIVE) ---
# IP Reputation ayarları API: AbuseIPDB entegrasyon konfigürasyonu,
# kontrol edilmiş IP istatistikleri, cache yönetimi ve API test endpoint'leri.
#
# Redis key'leri:
#   reputation:enabled           → "1" / "0"
#   reputation:abuseipdb_key     → API key string
#   reputation:blocked_countries → JSON array ["CN", "RU", ...]
#   reputation:daily_checks      → integer sayaç
#   reputation:ip:{ip}           → HASH (abuse_score, country, city, ...)

import json
import logging

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app.api.deps import get_current_user
from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.models.user import User

logger = logging.getLogger("tonbilai.api.ip_reputation")
router = APIRouter()

# ─── Sabitler ────────────────────────────────────────────────────────────────

REDIS_KEY_API_KEY       = "reputation:abuseipdb_key"
REDIS_KEY_DAILY_CHECKS  = "reputation:daily_checks"
REDIS_KEY_IP_PREFIX     = "reputation:ip:"
REDIS_KEY_ENABLED       = "reputation:enabled"
REDIS_KEY_COUNTRIES     = "reputation:blocked_countries"

# Worker sabit değerleriyle senkronize (bilgi amaçlı, UI'a gönderilir)
CHECK_INTERVAL       = 300
MAX_CHECKS_PER_CYCLE = 10
DAILY_LIMIT          = 1000

ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
HTTP_TIMEOUT  = 10  # saniye


# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _mask_api_key(key: str) -> str:
    """API anahtarının ortasını gizle: ilk 4 + son 4 karakter görünür."""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


async def _get_blocked_countries(redis) -> list[str]:
    """Redis'ten blocked_countries listesini oku (JSON parse)."""
    try:
        raw = await redis.get(REDIS_KEY_COUNTRIES)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"blocked_countries okunamadi: {exc}")
    return []


# ─── Endpoint'ler ─────────────────────────────────────────────────────────────


@router.get("/config")
async def get_ip_reputation_config(
    current_user: User = Depends(get_current_user),
):
    """
    Mevcut IP reputation yapılandırmasını döndür.

    abuseipdb_key alanı maskelidir (ilk 4 + son 4 karakter görünür).
    Anahtarın set edilip edilmediğini abuseipdb_key_set ile kontrol edin.
    """
    redis = await get_redis()

    enabled_raw = await redis.get(REDIS_KEY_ENABLED)
    # Varsayılan: etkin (key yoksa açık sayılır)
    enabled = (enabled_raw != "0") if enabled_raw is not None else True

    api_key_raw: str | None = await redis.get(REDIS_KEY_API_KEY)
    api_key_set = bool(api_key_raw and api_key_raw.strip())
    masked_key = _mask_api_key(api_key_raw.strip()) if api_key_set else ""

    blocked_countries = await _get_blocked_countries(redis)

    return {
        "enabled":              enabled,
        "abuseipdb_key":        masked_key,
        "abuseipdb_key_set":    api_key_set,
        "blocked_countries":    blocked_countries,
        "check_interval":       CHECK_INTERVAL,
        "max_checks_per_cycle": MAX_CHECKS_PER_CYCLE,
        "daily_limit":          DAILY_LIMIT,
    }


@router.put("/config")
async def update_ip_reputation_config(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """
    IP reputation yapılandırmasını güncelle.

    - enabled: true/false → reputation:enabled Redis key'i
    - abuseipdb_key: string → dolu ise kaydet, boş string ise sil
    - blocked_countries: ["CN", "RU", ...] → JSON olarak kaydet
    """
    redis = await get_redis()
    updated_fields: list[str] = []

    # enabled bayrağı
    if "enabled" in data:
        enabled_val = "1" if data["enabled"] else "0"
        await redis.set(REDIS_KEY_ENABLED, enabled_val)
        updated_fields.append(f"enabled={data['enabled']}")

    # API anahtarı
    if "abuseipdb_key" in data:
        key_val = str(data["abuseipdb_key"]).strip()
        if key_val:
            await redis.set(REDIS_KEY_API_KEY, key_val)
            updated_fields.append("abuseipdb_key=<set>")
            logger.info("AbuseIPDB API anahtarı güncellendi.")
        else:
            # Boş string → anahtarı sil
            await redis.delete(REDIS_KEY_API_KEY)
            updated_fields.append("abuseipdb_key=<deleted>")
            logger.info("AbuseIPDB API anahtarı silindi.")

    # Engellenen ülkeler
    if "blocked_countries" in data:
        countries = data["blocked_countries"]
        if not isinstance(countries, list):
            countries = []
        # Temizle: sadece 2 haneli büyük harf country code'ları kabul et
        clean = [str(c).upper().strip() for c in countries if str(c).strip()]
        await redis.set(REDIS_KEY_COUNTRIES, json.dumps(clean))
        updated_fields.append(f"blocked_countries={clean}")

    logger.info(f"IP reputation config güncellendi: {', '.join(updated_fields) or 'değişiklik yok'}")

    return {
        "status":  "ok",
        "message": "IP reputation ayarları güncellendi.",
        "updated": updated_fields,
    }


@router.get("/summary")
async def get_ip_reputation_summary(
    current_user: User = Depends(get_current_user),
):
    """
    Reputation kontrollerinin özet istatistiklerini döndür.

    Redis'teki tüm reputation:ip:* key'lerini tarar ve
    abuse skorlarına göre flagged_critical / flagged_warning sayar.
    """
    redis = await get_redis()

    total_checked   = 0
    flagged_critical = 0
    flagged_warning  = 0

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) as total, "
                    "SUM(CASE WHEN abuse_score >= 80 THEN 1 ELSE 0 END) as critical, "
                    "SUM(CASE WHEN abuse_score >= 50 AND abuse_score < 80 THEN 1 ELSE 0 END) as warning "
                    "FROM ip_reputation_checks"
                )
            )
            row = result.mappings().first()
            if row:
                total_checked    = int(row["total"]    or 0)
                flagged_critical = int(row["critical"] or 0)
                flagged_warning  = int(row["warning"]  or 0)
    except Exception as exc:
        logger.error(f"IP reputation summary SQL hatasi: {exc}")
        # SQL basarisizsa Redis SCAN fallback
        try:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor, match=f"{REDIS_KEY_IP_PREFIX}*", count=200
                )
                for key in keys:
                    score_raw = await redis.hget(key, "abuse_score")
                    if score_raw is not None:
                        total_checked += 1
                        score = int(score_raw)
                        if score >= 80:
                            flagged_critical += 1
                        elif score >= 50:
                            flagged_warning += 1
                if cursor == 0:
                    break
        except Exception as fallback_exc:
            logger.error(f"IP reputation summary Redis fallback hatasi: {fallback_exc}")

    daily_raw = await redis.get(REDIS_KEY_DAILY_CHECKS)
    daily_checks_used = int(daily_raw) if daily_raw else 0

    # AbuseIPDB gercek rate limit degerleri (worker tarafindan kaydedilir)
    abuseipdb_remaining: int | None = None
    abuseipdb_limit: int | None = None
    try:
        remaining_raw = await redis.get("reputation:abuseipdb_remaining")
        limit_raw     = await redis.get("reputation:abuseipdb_limit")
        if remaining_raw is not None:
            abuseipdb_remaining = int(remaining_raw)
        if limit_raw is not None:
            abuseipdb_limit = int(limit_raw)
    except Exception as exc:
        logger.debug(f"AbuseIPDB rate limit okunamadi: {exc}")

    # Redis'te rate limit bilgisi yoksa (TTL dolmus veya hic yazilmamis),
    # API anahtari varsa canli sorgu yaparak header'lardan limit bilgisini guncelle.
    # Not: Bu sorgu 1 AbuseIPDB check hakkini harcar (nadir durum: sadece TTL sonrasi tetiklenir).
    if abuseipdb_remaining is None or abuseipdb_limit is None:
        try:
            api_key_raw = await redis.get(REDIS_KEY_API_KEY)
            if api_key_raw and api_key_raw.strip():
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                    resp = await client.get(
                        ABUSEIPDB_URL,
                        headers={"Key": api_key_raw.strip(), "Accept": "application/json"},
                        params={"ipAddress": "8.8.8.8", "maxAgeInDays": 1},
                    )
                    if resp.status_code == 200:
                        h_remaining = resp.headers.get("X-RateLimit-Remaining")
                        h_limit     = resp.headers.get("X-RateLimit-Limit")
                        if h_remaining is not None:
                            abuseipdb_remaining = int(h_remaining)
                            await redis.set("reputation:abuseipdb_remaining", str(abuseipdb_remaining), ex=86400)
                        if h_limit is not None:
                            abuseipdb_limit = int(h_limit)
                            await redis.set("reputation:abuseipdb_limit", str(abuseipdb_limit), ex=86400)
                        logger.info(f"AbuseIPDB limit canli guncellendi: {abuseipdb_remaining}/{abuseipdb_limit}")
        except Exception as exc:
            logger.debug(f"AbuseIPDB canli limit sorgusu basarisiz: {exc}")

    # Gercek API verisi varsa, yerel sayac yerine API verisini kullan (daha dogru)
    effective_limit = DAILY_LIMIT
    if abuseipdb_remaining is not None and abuseipdb_limit is not None:
        daily_checks_used = abuseipdb_limit - abuseipdb_remaining
        effective_limit = abuseipdb_limit

    return {
        "total_checked":       total_checked,
        "flagged_critical":    flagged_critical,
        "flagged_warning":     flagged_warning,
        "daily_checks_used":   daily_checks_used,
        "daily_limit":         effective_limit,
        "abuseipdb_remaining": abuseipdb_remaining,
        "abuseipdb_limit":     abuseipdb_limit,
    }


@router.get("/ips")
async def get_checked_ips(
    min_score: int = Query(default=0, ge=0, le=100, description="Minimum abuse skoru filtresi"),
    current_user: User = Depends(get_current_user),
):
    """
    Kontrol edilmiş IP'lerin listesini döndür (abuse_score DESC sıralı).

    min_score parametresiyle belirli bir eşiğin üstündeki IP'ler filtrelenebilir.
    SQL master veri deposundan okur; hata durumunda Redis fallback kullanır.
    """
    ips: list[dict] = []

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT ip_address, abuse_score, total_reports, country, country_code, "
                    "city, isp, org, checked_at FROM ip_reputation_checks "
                    "WHERE abuse_score >= :min_score ORDER BY abuse_score DESC"
                ),
                {"min_score": min_score},
            )
            for row in result.mappings():
                checked_str = ""
                if row["checked_at"]:
                    checked_str = row["checked_at"].strftime("%Y-%m-%d %H:%M:%S")
                ips.append({
                    "ip":            row["ip_address"],
                    "abuse_score":   row["abuse_score"]   or 0,
                    "total_reports": row["total_reports"] or 0,
                    "country":       row["country"]       or "",
                    "city":          row["city"]           or "",
                    "isp":           row["isp"]            or "",
                    "org":           row["org"]            or "",
                    "checked_at":    checked_str,
                })
    except Exception as exc:
        logger.error(f"IP listesi SQL hatasi: {exc}")
        # SQL basarisizsa Redis fallback
        try:
            redis = await get_redis()
            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor, match=f"{REDIS_KEY_IP_PREFIX}*", count=200
                )
                for key in keys:
                    data = await redis.hgetall(key)
                    if not data:
                        continue
                    score = int(data.get("abuse_score", 0))
                    if score < min_score:
                        continue
                    ip_addr = key
                    if isinstance(key, str):
                        ip_addr = key.removeprefix(REDIS_KEY_IP_PREFIX)
                    ips.append({
                        "ip":            ip_addr,
                        "abuse_score":   score,
                        "total_reports": int(data.get("total_reports", 0)),
                        "country":       data.get("country", ""),
                        "city":          data.get("city", ""),
                        "isp":           data.get("isp", ""),
                        "org":           data.get("org", ""),
                        "checked_at":    data.get("checked_at", ""),
                    })
                if cursor == 0:
                    break
            ips.sort(key=lambda x: x["abuse_score"], reverse=True)
        except Exception as fallback_exc:
            logger.error(f"IP listesi Redis fallback hatasi: {fallback_exc}")

    return {
        "ips":   ips,
        "total": len(ips),
    }


@router.delete("/cache")
async def clear_reputation_cache(
    current_user: User = Depends(get_current_user),
):
    """
    Tüm reputation:ip:* cache key'lerini temizle.

    Silinen key sayısını döndürür.
    """
    redis = await get_redis()
    deleted_count = 0

    try:
        cursor = 0
        keys_to_delete: list[str] = []
        while True:
            cursor, keys = await redis.scan(
                cursor, match=f"{REDIS_KEY_IP_PREFIX}*", count=200
            )
            keys_to_delete.extend(keys)
            if cursor == 0:
                break

        if keys_to_delete:
            deleted_count = await redis.delete(*keys_to_delete)
        logger.info(f"IP reputation cache temizlendi: {deleted_count} key silindi.")
    except Exception as exc:
        logger.error(f"Cache temizleme hatası: {exc}")

    # SQL temizleme
    sql_deleted = 0
    try:
        async with async_session_factory() as session:
            r1 = await session.execute(text("DELETE FROM ip_reputation_checks"))
            r2 = await session.execute(text("DELETE FROM ip_blacklist_entries"))
            await session.commit()
            sql_deleted = (r1.rowcount or 0) + (r2.rowcount or 0)
            logger.info(f"SQL reputation verileri temizlendi: {sql_deleted} kayit")
    except Exception as sql_exc:
        logger.warning(f"SQL temizleme hatasi: {sql_exc}")

    return {
        "status":      "ok",
        "deleted":     deleted_count,
        "sql_deleted": sql_deleted,
        "message":     f"{deleted_count} Redis + {sql_deleted} SQL IP reputation kaydı silindi.",
    }


@router.post("/test")
async def test_abuseipdb_key(
    current_user: User = Depends(get_current_user),
):
    """
    Mevcut AbuseIPDB API anahtarını test et.

    Bilinen bir IP (8.8.8.8 — Google DNS) ile API'ye sorgu gönderir.
    Anahtar ayarlanmamışsa hata döndürür.
    """
    redis = await get_redis()

    api_key_raw: str | None = await redis.get(REDIS_KEY_API_KEY)
    if not api_key_raw or not api_key_raw.strip():
        return {
            "status":  "error",
            "message": "AbuseIPDB API anahtarı ayarlanmamış. Lütfen önce anahtarı kaydedin.",
            "data":    None,
        }

    api_key = api_key_raw.strip()
    test_ip = "8.8.8.8"  # Google Public DNS — güvenli test hedefi

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                ABUSEIPDB_URL,
                headers={"Key": api_key, "Accept": "application/json"},
                params={"ipAddress": test_ip, "maxAgeInDays": 90},
            )

        if response.status_code == 200:
            body = response.json()
            rep_data = body.get("data", {})
            return {
                "status":  "ok",
                "message": "AbuseIPDB API anahtarı geçerli ve çalışıyor.",
                "data": {
                    "tested_ip":      test_ip,
                    "abuse_score":    rep_data.get("abuseConfidenceScore", 0),
                    "total_reports":  rep_data.get("totalReports", 0),
                    "country":        rep_data.get("countryCode", ""),
                    "usage_type":     rep_data.get("usageType", ""),
                    "isp":            rep_data.get("isp", ""),
                },
            }
        elif response.status_code == 401:
            return {
                "status":  "error",
                "message": "API anahtarı geçersiz veya yetkisiz (HTTP 401).",
                "data":    None,
            }
        elif response.status_code == 429:
            return {
                "status":  "error",
                "message": "AbuseIPDB günlük kotası dolmuş (HTTP 429).",
                "data":    None,
            }
        else:
            return {
                "status":  "error",
                "message": f"AbuseIPDB beklenmedik yanıt: HTTP {response.status_code}",
                "data":    None,
            }
    except httpx.TimeoutException:
        return {
            "status":  "error",
            "message": f"AbuseIPDB bağlantısı zaman aşımına uğradı ({HTTP_TIMEOUT}s).",
            "data":    None,
        }
    except Exception as exc:
        logger.error(f"AbuseIPDB test hatası: {exc}")
        return {
            "status":  "error",
            "message": f"Test sırasında hata oluştu: {exc}",
            "data":    None,
        }


@router.get("/api-usage")
async def check_api_usage(
    current_user: User = Depends(get_current_user),
):
    """
    AbuseIPDB API kullanım bilgisini canlı olarak kontrol et.

    Her zaman AbuseIPDB API'ye fresh sorgu yaparak X-RateLimit-Remaining
    ve X-RateLimit-Limit header'larını döndürür.
    Bu çağrı 1 check hakkı harcar.
    """
    redis = await get_redis()

    api_key_raw: str | None = await redis.get(REDIS_KEY_API_KEY)
    if not api_key_raw or not api_key_raw.strip():
        return {
            "status": "error",
            "message": "AbuseIPDB API anahtarı ayarlanmamış.",
            "data": None,
        }

    api_key = api_key_raw.strip()

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                ABUSEIPDB_URL,
                headers={"Key": api_key, "Accept": "application/json"},
                params={"ipAddress": "8.8.8.8", "maxAgeInDays": 1},
            )

        if response.status_code == 200:
            h_remaining = response.headers.get("X-RateLimit-Remaining")
            h_limit = response.headers.get("X-RateLimit-Limit")
            h_retry = response.headers.get("Retry-After")

            remaining = int(h_remaining) if h_remaining is not None else None
            limit = int(h_limit) if h_limit is not None else None
            used = (limit - remaining) if limit is not None and remaining is not None else None

            # Redis cache güncelle
            if remaining is not None:
                await redis.set("reputation:abuseipdb_remaining", str(remaining), ex=86400)
            if limit is not None:
                await redis.set("reputation:abuseipdb_limit", str(limit), ex=86400)

            # Yerel günlük sayacı senkronize et
            if used is not None:
                await redis.set(REDIS_KEY_DAILY_CHECKS, str(used))
                ttl = await redis.ttl(REDIS_KEY_DAILY_CHECKS)
                if ttl == -1:
                    await redis.expire(REDIS_KEY_DAILY_CHECKS, 86400)

            pct = round((used / limit) * 100, 1) if used is not None and limit and limit > 0 else 0

            return {
                "status": "ok",
                "message": "API kullanım bilgisi başarıyla alındı.",
                "data": {
                    "limit": limit,
                    "used": used,
                    "remaining": remaining,
                    "usage_percent": pct,
                    "retry_after": h_retry,
                },
            }
        elif response.status_code == 429:
            h_limit = response.headers.get("X-RateLimit-Limit")
            h_remaining = response.headers.get("X-RateLimit-Remaining")
            limit_val = int(h_limit) if h_limit else DAILY_LIMIT
            remaining_val = int(h_remaining) if h_remaining else 0
            used_val = limit_val - remaining_val
            if h_limit:
                await redis.set("reputation:abuseipdb_limit", str(limit_val), ex=86400)
            if h_remaining is not None:
                await redis.set("reputation:abuseipdb_remaining", str(remaining_val), ex=86400)
            return {
                "status": "ok",
                "message": "AbuseIPDB günlük kotası dolmuş.",
                "data": {"limit": limit_val, "used": used_val, "remaining": remaining_val, "usage_percent": 100},
            }
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "API anahtarı geçersiz veya yetkisiz (HTTP 401).",
                "data": None,
            }
        else:
            return {
                "status": "error",
                "message": f"AbuseIPDB beklenmedik yanıt: HTTP {response.status_code}",
                "data": None,
            }
    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": f"AbuseIPDB bağlantısı zaman aşımına uğradı ({HTTP_TIMEOUT}s).",
            "data": None,
        }
    except Exception as exc:
        logger.error(f"API usage check hatası: {exc}")
        return {
            "status": "error",
            "message": f"Kontrol sırasında hata oluştu: {exc}",
            "data": None,
        }


ABUSEIPDB_BLACKLIST_URL = "https://api.abuseipdb.com/api/v2/blacklist"


# ─── Check-Block (Subnet Analizi) Endpoint'leri ────────────────────────────────


@router.post("/check-block")
async def trigger_check_block(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """
    AbuseIPDB check-block ile bir subnet'i (CIDR) analiz et.

    Body: {"network": "1.2.3.0/24", "auto_block": true}
    Subnet icindeki raporlanmis tum IP'leri dondurur.
    auto_block=true ve tehlikeli IP sayisi esigi asarsa subnet otomatik engellenir.
    """
    network = data.get("network", "").strip()
    if not network:
        return {"status": "error", "message": "network alani zorunludur (CIDR formati, orn: 1.2.3.0/24)"}

    auto_block = data.get("auto_block", True)

    from app.workers.ip_reputation import check_abuseipdb_block
    result = await check_abuseipdb_block(network, auto_block=auto_block)
    return result


@router.get("/check-block/results")
async def get_check_block_results(
    current_user: User = Depends(get_current_user),
):
    """
    Daha once analiz edilmis subnet sonuclarini listele (cache'den).

    Her subnet icin: network, toplam raporlanmis IP, tehlikeli IP sayisi.
    """
    redis = await get_redis()
    results = []

    try:
        # ZSET'ten tum subnet'leri al (skor = malicious_count)
        members = await redis.zrevrangebyscore(
            "reputation:check_block_results", "+inf", "-inf", withscores=True
        )
        for subnet_bytes, score in members:
            subnet = subnet_bytes if isinstance(subnet_bytes, str) else subnet_bytes.decode()
            # Detayli sonucu cache'den oku
            cached = await redis.get(f"reputation:check_block:{subnet}")
            if cached:
                detail = json.loads(cached)
                results.append({
                    "network": subnet,
                    "total_reported": detail.get("total_reported", 0),
                    "malicious_count": detail.get("malicious_count", 0),
                    "subnet_blocked": detail.get("subnet_blocked", False),
                    "num_possible_hosts": detail.get("num_possible_hosts", 0),
                    "message": detail.get("message", ""),
                })
            else:
                results.append({
                    "network": subnet,
                    "total_reported": 0,
                    "malicious_count": int(score),
                    "subnet_blocked": False,
                    "num_possible_hosts": 0,
                    "message": "Cache suresi dolmus",
                })
    except Exception as exc:
        logger.error(f"check-block results hatasi: {exc}")

    return {"results": results, "total": len(results)}


@router.get("/check-block/api-usage")
async def check_block_api_usage(
    current_user: User = Depends(get_current_user),
):
    """Check-block API kullanım bilgisini dondur (ayri havuz, check endpoint'ten farkli)."""
    redis = await get_redis()

    api_remaining_raw = await redis.get("reputation:check_block_api_remaining")
    api_limit_raw = await redis.get("reputation:check_block_api_limit")

    api_remaining = int(api_remaining_raw) if api_remaining_raw is not None else None
    api_limit = int(api_limit_raw) if api_limit_raw is not None else None

    # Cache yoksa canli minimal sorgu (1 hak harcar)
    if api_remaining is None or api_limit is None:
        try:
            api_key_raw = await redis.get(REDIS_KEY_API_KEY)
            if api_key_raw and api_key_raw.strip():
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                    resp = await client.get(
                        "https://api.abuseipdb.com/api/v2/check-block",
                        headers={"Key": api_key_raw.strip(), "Accept": "application/json"},
                        params={"network": "8.8.8.0/24", "maxAgeInDays": 1},
                    )
                    h_remaining = resp.headers.get("X-RateLimit-Remaining")
                    h_limit = resp.headers.get("X-RateLimit-Limit")
                    if h_remaining is not None:
                        api_remaining = int(h_remaining)
                        await redis.set("reputation:check_block_api_remaining", str(api_remaining), ex=86400)
                    if h_limit is not None:
                        api_limit = int(h_limit)
                        await redis.set("reputation:check_block_api_limit", str(api_limit), ex=86400)
        except Exception as exc:
            logger.debug(f"Check-block API canli limit sorgusu basarisiz: {exc}")

    if api_remaining is not None and api_limit is not None:
        used = api_limit - api_remaining
        pct = round((used / api_limit) * 100, 1) if api_limit > 0 else 0
    else:
        used = 0
        api_limit = api_limit or 0
        api_remaining = api_remaining or 0
        pct = 0

    return {
        "status": "ok",
        "data": {
            "limit": api_limit,
            "used": used,
            "remaining": api_remaining,
            "usage_percent": pct,
        },
    }


@router.delete("/check-block/cache")
async def clear_check_block_cache(
    current_user: User = Depends(get_current_user),
):
    """Check-block cache'ini temizle."""
    redis = await get_redis()
    deleted = 0
    try:
        # Tum check_block: prefix'li key'leri sil
        cursor = 0
        keys_to_delete = []
        while True:
            cursor, keys = await redis.scan(cursor, match="reputation:check_block:*", count=200)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break
        # Results ZSET'i de sil
        keys_to_delete.append("reputation:check_block_results")
        if keys_to_delete:
            deleted = await redis.delete(*keys_to_delete)
    except Exception as exc:
        logger.error(f"check-block cache temizleme hatasi: {exc}")

    return {"status": "ok", "deleted": deleted, "message": f"{deleted} subnet cache kaydi silindi."}


@router.get("/blacklist/api-usage")
async def check_blacklist_api_usage(
    current_user: User = Depends(get_current_user),
):
    """
    AbuseIPDB Blacklist API kullanım bilgisini canlı kontrol et.

    Önce Redis cache'e bakar. Cache yoksa veya force ise, AbuseIPDB blacklist
    endpoint'ine limit=1 ile minimal sorgu yaparak X-RateLimit header'larını okur.
    Bu çağrı 1 blacklist fetch hakkı harcar (sadece cache boşsa).
    """
    redis = await get_redis()

    daily_raw = await redis.get("reputation:blacklist_daily_fetches")
    daily_fetches = int(daily_raw) if daily_raw else 0

    # Worker tarafından kaydedilen API rate limit header verileri
    api_remaining_raw = await redis.get("reputation:blacklist_api_remaining")
    api_limit_raw = await redis.get("reputation:blacklist_api_limit")

    api_remaining = int(api_remaining_raw) if api_remaining_raw is not None else None
    api_limit = int(api_limit_raw) if api_limit_raw is not None else None

    # Cache'de yoksa canlı sorgu yap (limit=1 ile minimal — 1 fetch hakkı harcar)
    if api_remaining is None or api_limit is None:
        try:
            api_key_raw = await redis.get(REDIS_KEY_API_KEY)
            if api_key_raw and api_key_raw.strip():
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                    resp = await client.get(
                        ABUSEIPDB_BLACKLIST_URL,
                        headers={"Key": api_key_raw.strip(), "Accept": "application/json"},
                        params={"confidenceMinimum": 100, "limit": 1},
                    )
                    if resp.status_code == 200:
                        h_remaining = resp.headers.get("X-RateLimit-Remaining")
                        h_limit = resp.headers.get("X-RateLimit-Limit")
                        if h_remaining is not None:
                            api_remaining = int(h_remaining)
                            await redis.set("reputation:blacklist_api_remaining", str(api_remaining), ex=86400)
                        if h_limit is not None:
                            api_limit = int(h_limit)
                            await redis.set("reputation:blacklist_api_limit", str(api_limit), ex=86400)
                        # Yerel sayacı da senkronize et
                        if api_remaining is not None and api_limit is not None:
                            real_used = api_limit - api_remaining
                            await redis.set("reputation:blacklist_daily_fetches", str(real_used))
                            daily_fetches = real_used
                        logger.info(f"Blacklist API limit canli: {api_remaining}/{api_limit}")
                    elif resp.status_code == 429:
                        logger.warning("Blacklist API limit dolmus (429)")
                    else:
                        logger.warning(f"Blacklist API limit sorgusu: HTTP {resp.status_code}")
        except Exception as exc:
            logger.debug(f"Blacklist API canli limit sorgusu basarisiz: {exc}")

    # Eğer API header verisi varsa, onu kullan (daha doğru)
    if api_remaining is not None and api_limit is not None:
        effective_used = api_limit - api_remaining
        effective_limit = api_limit
    else:
        effective_used = daily_fetches
        effective_limit = 5

    pct = round((effective_used / effective_limit) * 100, 1) if effective_limit > 0 else 0

    last_fetch = await redis.get("reputation:blacklist_last_fetch") or ""
    total_count = await redis.get("reputation:blacklist_count") or "0"

    return {
        "status": "ok",
        "data": {
            "limit": effective_limit,
            "used": effective_used,
            "remaining": effective_limit - effective_used,
            "usage_percent": pct,
            "local_fetches": daily_fetches,
            "api_remaining": api_remaining,
            "api_limit": api_limit,
            "last_fetch": last_fetch,
            "total_ips": int(total_count),
        },
    }


@router.get("/blacklist")
async def get_blacklist_ips(
    current_user: User = Depends(get_current_user),
):
    """AbuseIPDB blacklist IP'lerini listele.

    SQL master veri deposundan okur; hata durumunda Redis fallback kullanır.
    """
    redis = await get_redis()
    ips = []
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT ip_address, abuse_score, country, last_reported_at, fetched_at "
                    "FROM ip_blacklist_entries ORDER BY abuse_score DESC"
                )
            )
            for row in result.mappings():
                ips.append({
                    "ip":              row["ip_address"],
                    "abuse_score":     row["abuse_score"]      or 0,
                    "country":         row["country"]           or "",
                    "last_reported_at": row["last_reported_at"] or "",
                })
    except Exception as exc:
        logger.error(f"Blacklist SQL hatasi: {exc}")
        # SQL basarisizsa Redis fallback
        try:
            ip_set = await redis.smembers("reputation:blacklist_ips")
            for ip in ip_set:
                data = await redis.hgetall(f"reputation:blacklist_data:{ip}")
                if data:
                    ips.append({
                        "ip":              ip,
                        "abuse_score":     int(data.get("abuse_score", 0)),
                        "country":         data.get("country", ""),
                        "last_reported_at": data.get("last_reported_at", ""),
                    })
            ips.sort(key=lambda x: x["abuse_score"], reverse=True)
        except Exception as fallback_exc:
            logger.error(f"Blacklist Redis fallback hatasi: {fallback_exc}")

    last_fetch = await redis.get("reputation:blacklist_last_fetch") or ""
    total_count = await redis.get("reputation:blacklist_count") or "0"

    return {
        "ips":         ips,
        "total":       len(ips),
        "last_fetch":  last_fetch,
        "total_count": int(total_count),
    }


@router.post("/blacklist/fetch")
async def trigger_blacklist_fetch(
    current_user: User = Depends(get_current_user),
):
    """Manuel olarak AbuseIPDB blacklist fetch tetikle."""
    from app.workers.ip_reputation import fetch_abuseipdb_blacklist
    result = await fetch_abuseipdb_blacklist(force=False)
    return result


@router.get("/blacklist/config")
async def get_blacklist_config(
    current_user: User = Depends(get_current_user),
):
    """Blacklist ayarlarini dondur."""
    redis = await get_redis()

    auto_block_raw = await redis.get("reputation:blacklist_auto_block")
    min_score_raw = await redis.get("reputation:blacklist_min_score")
    limit_raw = await redis.get("reputation:blacklist_limit")
    daily_raw = await redis.get("reputation:blacklist_daily_fetches")
    last_fetch = await redis.get("reputation:blacklist_last_fetch") or ""
    count = await redis.get("reputation:blacklist_count") or "0"

    return {
        "auto_block": (auto_block_raw != "0") if auto_block_raw is not None else True,
        "min_score": int(min_score_raw) if min_score_raw else 100,
        "limit": int(limit_raw) if limit_raw else 10000,
        "daily_fetches": int(daily_raw) if daily_raw else 0,
        "daily_limit": 5,
        "last_fetch": last_fetch,
        "total_count": int(count),
    }


@router.put("/blacklist/config")
async def update_blacklist_config(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Blacklist ayarlarini guncelle."""
    redis = await get_redis()
    updated = []

    if "auto_block" in data:
        await redis.set("reputation:blacklist_auto_block", "1" if data["auto_block"] else "0")
        updated.append(f"auto_block={data['auto_block']}")
    if "min_score" in data:
        val = max(25, min(100, int(data["min_score"])))
        await redis.set("reputation:blacklist_min_score", str(val))
        updated.append(f"min_score={val}")
    if "limit" in data:
        val = max(100, min(10000, int(data["limit"])))
        await redis.set("reputation:blacklist_limit", str(val))
        updated.append(f"limit={val}")

    return {"status": "ok", "updated": updated}


# ─── Catch-all: {network:path} EN SONA — static path'lerden sonra gelmeli ────

@router.get("/check-block/{network:path}")
async def get_check_block_detail(
    network: str,
    current_user: User = Depends(get_current_user),
):
    """Belirli bir subnet'in check-block sonuc detayini dondur (cache'den)."""
    redis = await get_redis()
    import ipaddress as _ipa
    try:
        net = _ipa.ip_network(network, strict=False)
        normalized = str(net)
    except ValueError:
        return {"status": "error", "message": f"Gecersiz CIDR: {network}"}

    cached = await redis.get(f"reputation:check_block:{normalized}")
    if cached:
        return json.loads(cached)

    return {"status": "error", "message": f"{normalized} icin cache'de sonuc bulunamadi. Analiz baslatmak icin POST /check-block kullanin."}

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

from app.api.deps import get_current_user
from app.db.redis_client import get_redis
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
DAILY_LIMIT          = 900

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
    except Exception as exc:
        logger.error(f"IP reputation summary tarama hatası: {exc}")

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
    """
    redis = await get_redis()
    ips: list[dict] = []

    try:
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
                # Redis key'inden prefix'i çıkar
                if isinstance(key, str):
                    ip_addr = key.removeprefix(REDIS_KEY_IP_PREFIX)
                ips.append({
                    "ip":           ip_addr,
                    "abuse_score":  score,
                    "total_reports": int(data.get("total_reports", 0)),
                    "country":      data.get("country", ""),
                    "city":         data.get("city", ""),
                    "isp":          data.get("isp", ""),
                    "org":          data.get("org", ""),
                    "checked_at":   data.get("checked_at", ""),
                })
            if cursor == 0:
                break
    except Exception as exc:
        logger.error(f"IP listesi tarama hatası: {exc}")

    # Abuse skoruna göre azalan sıralama
    ips.sort(key=lambda x: x["abuse_score"], reverse=True)

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

    return {
        "status":  "ok",
        "deleted": deleted_count,
        "message": f"{deleted_count} IP reputation cache kaydı silindi.",
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


@router.get("/blacklist")
async def get_blacklist_ips(
    current_user: User = Depends(get_current_user),
):
    """AbuseIPDB blacklist IP'lerini listele."""
    redis = await get_redis()
    ips = []
    try:
        ip_set = await redis.smembers("reputation:blacklist_ips")
        for ip in ip_set:
            data = await redis.hgetall(f"reputation:blacklist_data:{ip}")
            if data:
                ips.append({
                    "ip": ip,
                    "abuse_score": int(data.get("abuse_score", 0)),
                    "country": data.get("country", ""),
                    "last_reported_at": data.get("last_reported_at", ""),
                })
        ips.sort(key=lambda x: x["abuse_score"], reverse=True)
    except Exception as exc:
        logger.error(f"Blacklist listeleme hatasi: {exc}")

    last_fetch = await redis.get("reputation:blacklist_last_fetch") or ""
    total_count = await redis.get("reputation:blacklist_count") or "0"

    return {
        "ips": ips,
        "total": len(ips),
        "last_fetch": last_fetch,
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

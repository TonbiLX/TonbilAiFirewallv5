# --- Ajan: ANALIST (THE ANALYST) ---
# Domain Reputation Skoru Servisi: Sorgulanan domainlerin risk puanini hesaplar.
# Shannon entropi, TLD riski, uzunluk, rakam oranı, bilinen CDN/güvenli listeler.
# Redis cache ile performansli, dns_proxy ve threat_analyzer tarafindan kullanilir.

import logging
import math
from collections import Counter

from app.db.redis_client import get_redis

logger = logging.getLogger("tonbilai.domain_reputation")

# --- Bilinen Guvenli Domainler (Beyaz Liste) ---
SAFE_DOMAINS = {
    # Buyuk teknoloji
    "google.com", "googleapis.com", "gstatic.com", "googlevideo.com",
    "youtube.com", "ytimg.com", "ggpht.com",
    "apple.com", "icloud.com", "mzstatic.com",
    "microsoft.com", "msftconnecttest.com", "windowsupdate.com",
    "live.com", "outlook.com", "office.com",
    "amazon.com", "amazonaws.com", "cloudfront.net",
    "facebook.com", "fbcdn.net", "meta.com",
    "instagram.com", "whatsapp.net", "whatsapp.com",
    "twitter.com", "x.com", "twimg.com",
    # CDN / Altyapi
    "cloudflare.com", "cloudflare-dns.com",
    "akamai.com", "akamaized.net", "akamaihd.net",
    "fastly.net", "fastlylb.net",
    "edgecastcdn.net", "azureedge.net",
    # DNS
    "dns.google", "one.one.one.one",
    # Diger güvenli
    "github.com", "githubusercontent.com",
    "stackoverflow.com", "wikipedia.org",
    "netflix.com", "nflxvideo.net",
    "spotify.com", "scdn.co",
    "steam.com", "steamcommunity.com", "steampowered.com",
    "reddit.com", "redd.it", "redditstatic.com",
    "linkedin.com",
    "samsung.com", "samsungcloud.com",
    "playstation.com", "playstation.net",
    "xbox.com", "xboxlive.com",
    "nintendo.com", "nintendo.net",
    # Turkiye
    "trendyol.com", "hepsiburada.com", "sahibinden.com",
    "turktelekom.com.tr", "turkcell.com.tr", "vodafone.com.tr",
    # NTP / Altyapi
    "pool.ntp.org", "ntp.org",
}

# --- Bilinen Guvenli CDN Alt Domainleri ---
SAFE_SUFFIXES = [
    ".googleapis.com", ".gstatic.com", ".googlevideo.com",
    ".google.com", ".google.com.tr",
    ".apple.com", ".icloud.com",
    ".microsoft.com", ".windows.com", ".azure.com",
    ".amazonaws.com", ".cloudfront.net",
    ".akamaized.net", ".akamaihd.net",
    ".cloudflare.com", ".cloudflare-dns.com",
    ".fbcdn.net", ".facebook.com",
    ".samsungcloudsolution.net", ".samsungcloud.com",
]

# --- Yuksek Riskli TLD'ler ---
HIGH_RISK_TLDS = {
    "xyz", "top", "buzz", "click", "loan", "work", "gq", "ml",
    "cf", "ga", "tk", "icu", "cam", "rest", "surf", "monster",
    "quest", "win", "bid", "trade", "review", "party", "date",
    "racing", "cricket", "science", "download", "accountant",
    "faith", "stream",
}

# Redis cache TTL
REPUTATION_CACHE_TTL = 3600  # 1 saat


def _calculate_entropy(name: str) -> float:
    """Shannon entropi hesapla."""
    if not name or len(name) < 4:
        return 0.0
    freq = Counter(name.lower())
    length = len(name)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )


def _get_base_domain(domain: str) -> str:
    """Ana domain'i cikar (subdomain'leri at).
    Ornek: 'ads.tracking.example.com' -> 'example.com'
    """
    parts = domain.rstrip(".").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def _get_tld(domain: str) -> str:
    """TLD'yi cikar."""
    parts = domain.rstrip(".").split(".")
    return parts[-1] if parts else ""


def calculate_reputation_sync(domain: str) -> dict:
    """Domain reputation skorunu hesapla (senkron, Redis gerektirmez).
    Returns: {"score": 0-100, "risk_level": str, "factors": list[str]}
    """
    normalized = domain.rstrip(".").lower()
    base_domain = _get_base_domain(normalized)
    tld = _get_tld(normalized)
    parts = normalized.split(".")
    name = parts[0] if parts else normalized  # En soldaki label

    score = 0
    factors = []

    # --- Beyaz liste kontrolleri (negatif puan = güvenli) ---

    # Tam esleme
    if base_domain in SAFE_DOMAINS or normalized in SAFE_DOMAINS:
        return {"score": 0, "risk_level": "safe", "factors": ["Bilinen güvenli domain"]}

    # Suffix esleme (CDN alt domainleri)
    for suffix in SAFE_SUFFIXES:
        if normalized.endswith(suffix):
            return {"score": 5, "risk_level": "safe", "factors": ["Guvenli CDN alt domain'i"]}

    # --- Risk faktorleri (pozitif puan = riskli) ---

    # 1. Shannon entropi
    entropy = _calculate_entropy(name)
    if entropy >= 4.0:
        score += 30
        factors.append(f"Cok yuksek entropi: {entropy:.2f} (DGA suphesi)")
    elif entropy >= 3.5:
        score += 15
        factors.append(f"Yuksek entropi: {entropy:.2f}")

    # 2. Domain uzunlugu
    if len(name) >= 30:
        score += 10
        factors.append(f"Anormal uzunluk: {len(name)} karakter")

    # 3. Rakam oranı
    if len(name) > 0:
        digit_ratio = sum(1 for c in name if c.isdigit()) / len(name)
        if digit_ratio > 0.4:
            score += 15
            factors.append(f"Yuksek rakam oranı: %{digit_ratio*100:.0f}")

    # 4. Sesli harf oranı
    if len(name) >= 8:
        vowels = set("aeiouy")
        vowel_ratio = sum(1 for c in name.lower() if c in vowels) / len(name)
        if vowel_ratio < 0.10:
            score += 10
            factors.append(f"Cok dusuk sesli harf oranı: %{vowel_ratio*100:.0f}")

    # 5. TLD riski
    if tld in HIGH_RISK_TLDS:
        score += 20
        factors.append(f"Yuksek riskli TLD: .{tld}")

    # 6. Subdomain derinligi
    if len(parts) >= 5:
        score += 10
        factors.append(f"Derin subdomain: {len(parts)} seviye")

    # 7. Tire ve özel karakter oranı
    if len(name) > 0:
        special_ratio = sum(1 for c in name if c in "-_") / len(name)
        if special_ratio > 0.2:
            score += 5
            factors.append(f"Yuksek özel karakter oranı: %{special_ratio*100:.0f}")

    # Skoru 0-100 aralığına sinirla
    score = max(0, min(100, score))

    # Risk seviyesini belirle
    if score <= 20:
        risk_level = "safe"
    elif score <= 40:
        risk_level = "low"
    elif score <= 60:
        risk_level = "medium"
    elif score <= 80:
        risk_level = "high"
    else:
        risk_level = "critical"

    return {
        "score": score,
        "risk_level": risk_level,
        "factors": factors if factors else ["Normal domain"],
    }


async def calculate_reputation(domain: str) -> dict:
    """Domain reputation skorunu hesapla (async, Redis cache ile).
    Öncelikle cache'e bakar, yoksa hesaplar ve cache'e yazar.
    """
    try:
        redis = await get_redis()
        cache_key = f"dns:reputation:{domain.rstrip('.').lower()}"

        # Cache kontrolü
        cached = await redis.hgetall(cache_key)
        if cached:
            return {
                "score": int(cached.get("score", 0)),
                "risk_level": cached.get("risk_level", "safe"),
                "factors": (cached.get("factors", "")).split("|") if cached.get("factors") else [],
            }

        # Hesapla
        result = calculate_reputation_sync(domain)

        # Cache'e yaz
        await redis.hset(cache_key, mapping={
            "score": str(result["score"]),
            "risk_level": result["risk_level"],
            "factors": "|".join(result["factors"]),
        })
        await redis.expire(cache_key, REPUTATION_CACHE_TTL)

        return result

    except Exception as e:
        logger.debug(f"Reputation hesaplama hatasi: {e}")
        return calculate_reputation_sync(domain)


async def get_cached_reputation(redis_client, domain: str) -> dict | None:
    """Redis'ten cache'lenmis reputation skorunu dondur (dns_proxy için hizli erişim).
    Cache yoksa None dondurur (hesaplama yapmaz - performans için).
    """
    try:
        cache_key = f"dns:reputation:{domain.rstrip('.').lower()}"
        cached = await redis_client.hgetall(cache_key)
        if cached:
            return {
                "score": int(cached.get("score", 0)),
                "risk_level": cached.get("risk_level", "safe"),
            }
        return None
    except Exception:
        return None

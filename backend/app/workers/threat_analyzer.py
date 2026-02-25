# --- Ajan: ANALIST (THE ANALYST) ---
# AI DNS Tehdit Analiz Sistemi: Dış IP flood tespiti, DGA algilama,
# şüpheli sorgu tipi kontrolü, otomatik IP engelleme.
# Sonuçlar AiInsight tablosuna yazilir (InsightsPage'de görünür).
#
# v2 Eklemeler (2026-02-15):
# - Subnet bazli flood tespiti (/24 alt agi izleme)
# - Koordineli tarama pattern tespiti (ayni qtype+domain, farkli IP'ler)
# - Tehdit skor sistemi (birikimli puan, esik asilinca otomatik engel)
# - Insight spam azaltma (30 dk cooldown, toplu uyari)

import asyncio
import ipaddress
import logging
import math
import time
from collections import Counter
from datetime import datetime

from app.db.session import async_session_factory
from app.db.redis_client import get_redis
from app.models.ai_insight import AiInsight, Severity
from app.services.telegram_service import notify_ip_blocked, notify_device_isolation_suggestion, notify_ai_insight

logger = logging.getLogger("tonbilai.threat_analyzer")

# --- Sabitler ---
EXTERNAL_RATE_THRESHOLD = 20       # dis IP: 20 sorgu/dk -> engelle
LOCAL_RATE_THRESHOLD = 300         # yerel: 300 sorgu/dk -> uyari
BLOCK_DURATION_SEC = 3600          # otomatik engel süresi: 1 saat
DGA_ENTROPY_THRESHOLD = 3.5        # Shannon entropi esigi
SUSPICIOUS_QTYPES = {"TXT", "ANY", "NULL", "AXFR", "HINFO", "WKS"}
CLEANUP_INTERVAL = 300             # 5 dk'da bir temizlik

# v2 Sabitler
SUBNET_FLOOD_THRESHOLD = 5         # /24 subnet: 5+ benzersiz IP -> engelle
SUBNET_WINDOW_SEC = 300            # subnet izleme penceresi: 5 dk
SCAN_PATTERN_THRESHOLD = 3         # 3+ farkli IP ayni qtype+domain -> koordineli tarama
SCAN_PATTERN_WINDOW_SEC = 300      # pattern izleme penceresi: 5 dk
THREAT_SCORE_AUTO_BLOCK = 15       # tehdit skoru 15+ -> otomatik engel
THREAT_SCORE_TTL = 3600            # skor TTL: 1 saat
SUBNET_BLOCK_DURATION_SEC = 3600   # subnet engel süresi: 1 saat
AGGREGATED_COOLDOWN_SEC = 1800     # toplu uyari cooldown: 30 dk

# Güvenilir IP'ler - otomatik engellemeye tabi TUTULMAYACAK IP'ler
# Pi'nin kendi public IP'si, gateway, yerel DNS sunuculari vb.
TRUSTED_IPS: set[str] = set()

def _load_trusted_ips():
    """Güvenilir IP listesini yeniden yukle.
    /opt/tonbilaios/backend/data/trusted_ips.txt varsa oku, yoksa varsayilan degerleri kullan.
    ONEMLI: Set objesini yeniden oluşturma (rebind), mevcut seti güncelle.
    Aksi halde import eden moduller eski referansi kullanmaya devam eder.
    """
    defaults = {
        "176.88.250.236",  # Pi public IP (DoT istemcileri bu IP ile gorunebilir)
        "192.168.1.1",     # Modem/Gateway
        "192.168.1.9",     # Pi kendisi
    }
    try:
        import pathlib
        trust_file = pathlib.Path("/opt/tonbilaios/backend/data/trusted_ips.txt")
        if trust_file.exists():
            for line in trust_file.read_text().strip().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    defaults.add(line)
    except Exception:
        pass
    # Mevcut set objesini yerinde güncelle (rebind etme!)
    TRUSTED_IPS.clear()
    TRUSTED_IPS.update(defaults)
    logger.info(f"Güvenilir IP listesi yuklendi: {len(TRUSTED_IPS)} IP")

_load_trusted_ips()


def is_trusted_ip(ip: str) -> bool:
    """IP guvenilir listesinde mi? DNS proxy ve diger moduller için."""
    return ip in TRUSTED_IPS


# Bellek ici duplike onleme - ayni IP/olay için tekrar tekrar insight yazmamak
_recent_insights: dict[str, float] = {}
_INSIGHT_COOLDOWN = 1800  # ayni olay için 30 dk bekleme (v2: 5 dk -> 30 dk)


# --- Shannon Entropi (DGA Algilama) ---

def calculate_entropy(domain: str) -> float:
    """Domain adinin Shannon entropisini hesapla.
    Yuksek entropi = rastgele uretilmis domain (DGA suphesi).
    Normal domainler genelde 2.5-3.2 arasinda,
    DGA domainleri 3.5+ olur.
    """
    # Sadece ana domain kismini al (TLD haric)
    parts = domain.rstrip(".").split(".")
    if len(parts) >= 2:
        name = parts[0]  # En soldaki label (örnek: "xk3j8f9a2m")
    else:
        name = domain

    if not name or len(name) < 4:
        return 0.0

    freq = Counter(name.lower())
    length = len(name)
    entropy = -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )
    return entropy


def _is_dga_suspicious(domain: str) -> bool:
    """Domain DGA suphesi tasiyor mu?"""
    parts = domain.rstrip(".").split(".")
    if len(parts) < 2:
        return False

    name = parts[0]
    # Cok kısa isimler (google, fb vb.) DGA degil
    if len(name) < 8:
        return False

    # Entropi kontrolü
    entropy = calculate_entropy(domain)
    if entropy < DGA_ENTROPY_THRESHOLD:
        return False

    # Ek kontrol: rakam oranı yuksek mi?
    digit_ratio = sum(1 for c in name if c.isdigit()) / len(name)
    if digit_ratio > 0.4:
        return True

    # Ek kontrol: sesli harf oranı cok dusuk mu?
    vowels = set("aeiouy")
    vowel_ratio = sum(1 for c in name.lower() if c in vowels) / len(name)
    if vowel_ratio < 0.15 and entropy >= DGA_ENTROPY_THRESHOLD:
        return True

    return entropy >= 4.0  # Cok yuksek entropi -> kesin şüpheli


# --- Yardimci Fonksiyonlar (v2) ---

def _extract_subnet(ip: str) -> str:
    """IP adresinden /24 subnet cikar.
    Ornek: '45.232.214.55' -> '45.232.214.0/24'
    """
    try:
        addr = ipaddress.IPv4Address(ip)
        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        return str(network)
    except (ipaddress.AddressValueError, ValueError):
        # IPv6 veya geçersiz adres için IP'yi oldugu gibi dondur
        return ip


# --- AiInsight Kaydi Yazma ---

async def _write_insight(
    severity: Severity,
    message: str,
    suggested_action: str | None = None,
    category: str = "security",
    cooldown_key: str | None = None,
):
    """AiInsight tablosuna tehdit kaydi yaz.
    cooldown_key verilirse, ayni key için _INSIGHT_COOLDOWN süresi içinde
    tekrar yazilmaz (spam onleme).
    """
    if cooldown_key:
        now = time.monotonic()
        last = _recent_insights.get(cooldown_key, 0)
        if now - last < _INSIGHT_COOLDOWN:
            return
        _recent_insights[cooldown_key] = now

    try:
        async with async_session_factory() as session:
            insight = AiInsight(
                severity=severity,
                message=message,
                suggested_action=suggested_action,
                category=category,
                timestamp=datetime.utcnow(),
            )
            session.add(insight)
            await session.commit()
            logger.info(f"AiInsight yazildi [{severity.value}]: {message[:80]}")
    except Exception as e:
        logger.error(f"AiInsight yazma hatasi: {e}")

    # Telegram bildirimi (DB işleminden bagimsiz, hata yutulur)
    try:
        await notify_ai_insight(severity.value, message, category)
    except Exception as e:
        logger.debug(f"AI Insight Telegram bildirim hatasi: {e}")


# --- Redis İşlemleri ---

async def _get_redis():
    """Redis istemcisini al."""
    return await get_redis()


async def is_ip_blocked(ip: str) -> bool:
    """IP tehdit listesinde mi? (O(1) Redis SISMEMBER)
    v2: Subnet bazli engel kontrolü de yapar.
    v3: Güvenilir IP'ler ASLA engellenmez (bypass + uyari).
    """
    # Güvenilir IP korumasi - TRUSTED_IPS'teki IP'ler asla engellenmez
    if ip in TRUSTED_IPS:
        return False
    try:
        redis = await _get_redis()
        # Mevcut: bireysel IP kontrolü
        if await redis.sismember("dns:threat:blocked", ip):
            return True
        # v2: subnet bazli engel kontrolü
        return await is_subnet_blocked(ip)
    except Exception:
        return False


async def is_subnet_blocked(ip: str) -> bool:
    """IP'nin /24 subnet'i engelli mi? (v2)"""
    try:
        redis = await _get_redis()
        subnet = _extract_subnet(ip)
        return await redis.exists(f"dns:threat:subnet_blocked:{subnet}") > 0
    except Exception:
        return False


async def auto_block_ip(ip: str, reason: str):
    """IP'yi otomatik engelle ve AiInsight yaz."""
    # Güvenilir IP korumasi - Pi'nin kendisi ve gateway asla engellenmemeli
    # Ama uyari oluştur ve Telegram bildirim at
    if ip in TRUSTED_IPS:
        logger.warning(f"Güvenilir IP tehdit tespiti (engellenmedi): {ip} (sebep: {reason})")
        await _write_insight(
            severity=Severity.WARNING,
            message=(
                f"Güvenilir IP'den tehdit tespiti: {ip} - {reason}. "
                f"IP guvenilir listesinde oldugu için engellenmedi."
            ),
            suggested_action=(
                f"Bu IP'yi ({ip}) kontrol edin. Cihaz ele gecirilmis olabilir. "
                f"Gerekliyse guvenilir listesinden cikarin."
            ),
            category="trusted_ip_threat",
            cooldown_key=f"trusted_threat:{ip}",
        )
        from app.services.telegram_service import notify_trusted_ip_threat
        await notify_trusted_ip_threat(ip, reason)
        return
    try:
        redis = await _get_redis()
        added = await redis.sadd("dns:threat:blocked", ip)
        if not added:
            return  # Zaten engelli

        # Engel süresi için ayri key (TTL ile otomatik kalkar)
        await redis.set(f"dns:threat:block_expire:{ip}", reason, ex=BLOCK_DURATION_SEC)

        # İstatistikleri güncelle
        await redis.hincrby("dns:threat:stats", "total_auto_blocks", 1)
        await redis.hset("dns:threat:stats", "last_threat_time",
                         datetime.utcnow().isoformat())

        logger.warning(f"IP OTOMATIK ENGELLENDI: {ip} - Sebep: {reason}")

        # nftables blocked_ips setine de ekle (ag seviyesi engelleme)
        try:
            from app.hal import linux_nftables as nft
            await nft.add_blocked_ip(ip, BLOCK_DURATION_SEC)
        except Exception as nft_err:
            logger.warning(f"nftables IP engelleme hatasi: {nft_err}")

        await _write_insight(
            severity=Severity.CRITICAL,
            message=f"Dış IP otomatik engellendi: {ip} - {reason}",
            suggested_action=f"IP {ip} 1 saat boyunca engelli. "
                            "Kalici engellemek için: AI Chat'ten 'IP engelle {ip}' yazin.",
            category="security",
            cooldown_key=f"block:{ip}",
        )

        # Telegram bildirim (fire-and-forget)
        try:
            await notify_ip_blocked(ip, reason)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"IP engelleme hatasi ({ip}): {e}")


async def auto_block_subnet(subnet: str, reason: str, triggering_ips: set[str] | None = None):
    """Tum /24 subnet'i engelle (v2).
    Triggering_ips: Bu subnet'ten gelen bilinen IP'ler (bunlari bireysel olarak da engelle).
    """
    # Güvenilir IP subnet korumasi
    if triggering_ips:
        trusted_in_set = triggering_ips & TRUSTED_IPS
        if trusted_in_set:
            logger.warning(f"Subnet engelleme onlendi: {subnet} içinde guvenilir IP var ({trusted_in_set})")
            return
    try:
        redis = await _get_redis()

        # Subnet engel key'ini ayarla (TTL ile otomatik kalkar)
        already_blocked = await redis.exists(f"dns:threat:subnet_blocked:{subnet}")
        if already_blocked:
            return  # Zaten engelli

        await redis.set(
            f"dns:threat:subnet_blocked:{subnet}",
            reason,
            ex=SUBNET_BLOCK_DURATION_SEC,
        )

        # Bilinen IP'leri bireysel olarak da engelle
        if triggering_ips:
            for ip in triggering_ips:
                await redis.sadd("dns:threat:blocked", ip)
                await redis.set(
                    f"dns:threat:block_expire:{ip}",
                    f"Subnet engeli: {reason}",
                    ex=SUBNET_BLOCK_DURATION_SEC,
                )

        # İstatistikleri güncelle
        blocked_count = len(triggering_ips) if triggering_ips else 0
        await redis.hincrby("dns:threat:stats", "total_auto_blocks", max(blocked_count, 1))
        await redis.hset("dns:threat:stats", "last_threat_time",
                         datetime.utcnow().isoformat())

        logger.warning(
            f"SUBNET OTOMATIK ENGELLENDI: {subnet} - "
            f"{blocked_count} bilinen IP - Sebep: {reason}"
        )

        # nftables subnet kurallarini da ekle
        try:
            from app.hal import linux_nftables as nft
            await nft.add_blocked_subnet(subnet, SUBNET_BLOCK_DURATION_SEC)
            if triggering_ips:
                for tip in triggering_ips:
                    await nft.add_blocked_ip(tip, SUBNET_BLOCK_DURATION_SEC)
        except Exception as nft_err:
            logger.warning(f"nftables subnet engelleme hatasi: {nft_err}")

        await _write_insight(
            severity=Severity.CRITICAL,
            message=(
                f"Alt ag otomatik engellendi: {subnet} - "
                f"{blocked_count} benzersiz IP tespit edildi. {reason}"
            ),
            suggested_action=(
                f"Subnet {subnet} {SUBNET_BLOCK_DURATION_SEC // 60} dakika boyunca engelli. "
                "Tum alt ag trafiği reddedilecek."
            ),
            category="security",
            cooldown_key=f"subnet_block:{subnet}",
        )

        # Telegram bildirim (fire-and-forget)
        try:
            await notify_ip_blocked(
                subnet,
                f"Subnet engeli: {blocked_count} benzersiz IP. {reason}"
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Subnet engelleme hatasi ({subnet}): {e}")


async def manual_block_ip(ip: str, reason: str = "Manuel engelleme", ttl_seconds: int | None = None):
    """IP'yi manuel engelle (Chat/API üzerinden).
    ttl_seconds: None veya 0 = kalici (Redis'te süresi olmayan), pozitif = o kadar saniye TTL.
    """
    try:
        redis = await _get_redis()
        await redis.sadd("dns:threat:blocked", ip)

        if ttl_seconds is not None and ttl_seconds > 0:
            await redis.set(f"dns:threat:block_expire:{ip}", reason, ex=ttl_seconds)
        else:
            # Kalici engel — TTL yok
            await redis.set(f"dns:threat:block_expire:{ip}", reason)

        await redis.hincrby("dns:threat:stats", "total_auto_blocks", 1)

        sure_str = f"{ttl_seconds // 60} dk" if ttl_seconds else "kalici"
        logger.info(f"IP MANUEL ENGELLENDI: {ip} - {reason} (sure: {sure_str})")

        # nftables blocked_ips setine de ekle
        try:
            from app.hal import linux_nftables as nft
            nft_ttl = ttl_seconds if (ttl_seconds and ttl_seconds > 0) else 31536000
            await nft.add_blocked_ip(ip, nft_ttl)
        except Exception as nft_err:
            logger.warning(f"nftables manuel IP engelleme hatasi: {nft_err}")

        await _write_insight(
            severity=Severity.WARNING,
            message=f"IP manuel olarak engellendi: {ip} - {reason} (sure: {sure_str})",
            suggested_action="Engeli kaldirmak için: AI Chat'ten "
                            f"'{ip} engelini kaldir' yazin.",
            category="security",
        )
        return True
    except Exception as e:
        logger.error(f"Manuel IP engelleme hatasi ({ip}): {e}")
        return False


async def update_block_ttl(ip: str, ttl_seconds: int | None = None):
    """Mevcut bir IP engelinin Redis TTL'ini güncelle."""
    try:
        redis = await _get_redis()
        key = f"dns:threat:block_expire:{ip}"
        exists = await redis.exists(key)
        if not exists:
            return False
        if ttl_seconds is not None and ttl_seconds > 0:
            await redis.expire(key, ttl_seconds)
        else:
            await redis.persist(key)
        logger.info(f"IP engel TTL güncellendi: {ip} -> {ttl_seconds or 'kalici'}s")
        return True
    except Exception as e:
        logger.error(f"IP engel TTL güncelleme hatasi ({ip}): {e}")
        return False


async def manual_unblock_ip(ip: str):
    """IP engelini kaldir."""
    try:
        redis = await _get_redis()
        removed = await redis.srem("dns:threat:blocked", ip)
        await redis.delete(f"dns:threat:block_expire:{ip}")

        if removed:
            logger.info(f"IP ENGELI KALDIRILDI: {ip}")

            # nftables setinden de kaldir
            try:
                from app.hal import linux_nftables as nft
                await nft.remove_blocked_ip(ip)
            except Exception as nft_err:
                logger.warning(f"nftables IP engel kaldirma hatasi: {nft_err}")

            await _write_insight(
                severity=Severity.INFO,
                message=f"IP engeli kaldırıldı: {ip}",
                category="security",
            )
            return True
        return False
    except Exception as e:
        logger.error(f"IP engel kaldirma hatasi ({ip}): {e}")
        return False


async def get_blocked_ips() -> list[dict]:
    """Engellenen IP listesini dondur."""
    try:
        redis = await _get_redis()
        ips = await redis.smembers("dns:threat:blocked")
        result = []
        for ip in ips:
            reason = await redis.get(f"dns:threat:block_expire:{ip}") or "Bilinmiyor"
            ttl = await redis.ttl(f"dns:threat:block_expire:{ip}")
            result.append({
                "ip": ip,
                "reason": reason,
                "remaining_seconds": max(ttl, 0),
            })
        return result
    except Exception as e:
        logger.error(f"Engellenen IP listesi hatasi: {e}")
        return []


async def get_threat_stats() -> dict:
    """Tehdit istatistiklerini dondur."""
    try:
        redis = await _get_redis()
        stats = await redis.hgetall("dns:threat:stats") or {}
        blocked_count = await redis.scard("dns:threat:blocked")
        return {
            "blocked_ip_count": blocked_count,
            "total_external_blocked": int(stats.get("total_external_blocked", 0)),
            "total_auto_blocks": int(stats.get("total_auto_blocks", 0)),
            "total_suspicious": int(stats.get("total_suspicious", 0)),
            "last_threat_time": stats.get("last_threat_time"),
        }
    except Exception as e:
        logger.error(f"Tehdit istatistik hatasi: {e}")
        return {
            "blocked_ip_count": 0,
            "total_external_blocked": 0,
            "total_auto_blocks": 0,
            "total_suspicious": 0,
            "last_threat_time": None,
        }


# --- v2: Subnet Flood Tespiti ---

async def _check_subnet_flood(client_ip: str, domain: str, qtype_name: str) -> bool:
    """Ayni /24 subnet'ten gelen koordineli sorgulari tespit et.
    5+ benzersiz IP ayni subnet'ten şüpheli sorgu yaparsa -> tum subnet engellenir.
    Dondurur: True = subnet engellendi, False = henüz esik asilmadi.
    """
    # Sadece şüpheli sorgu tipleri için subnet izleme yap
    if qtype_name not in SUSPICIOUS_QTYPES:
        return False

    try:
        redis = await _get_redis()
        subnet = _extract_subnet(client_ip)

        # Subnet zaten engelli mi?
        if await redis.exists(f"dns:threat:subnet_blocked:{subnet}"):
            return True  # Zaten engelli, tekrar engellemeye gerek yok

        # Bu IP'yi subnet SET'ine ekle (benzersiz IP takibi)
        subnet_key = f"dns:threat:subnet:{subnet}"
        await redis.sadd(subnet_key, client_ip)

        # Ilk ekleme ise TTL ayarla
        ttl = await redis.ttl(subnet_key)
        if ttl == -1:  # TTL yok -> yeni key
            await redis.expire(subnet_key, SUBNET_WINDOW_SEC)

        # Subnet sorgu sayacıni artir
        count_key = f"dns:threat:subnet_count:{subnet}"
        count = await redis.incr(count_key)
        if count == 1:
            await redis.expire(count_key, SUBNET_WINDOW_SEC)

        # Benzersiz IP sayısıni kontrol et
        unique_ips = await redis.scard(subnet_key)

        if unique_ips >= SUBNET_FLOOD_THRESHOLD:
            # Subnet'ten gelen tum bilinen IP'leri al
            triggering_ips = await redis.smembers(subnet_key)
            # str'ye cevir (Redis bytes donebilir)
            ip_set = {
                ip.decode() if isinstance(ip, bytes) else ip
                for ip in triggering_ips
            }

            reason = (
                f"Koordineli tarama: {unique_ips} benzersiz IP, "
                f"{count} toplam sorgu, hedef: {domain} ({qtype_name})"
            )
            await auto_block_subnet(subnet, reason, triggering_ips=ip_set)

            # Toplu uyari insight'i
            await _write_insight(
                severity=Severity.CRITICAL,
                message=(
                    f"Koordineli tarama tespiti: {unique_ips} benzersiz IP, "
                    f"{subnet} alt agi, hedef: {domain} ({qtype_name})"
                ),
                suggested_action=(
                    f"Subnet {subnet} otomatik engellendi. "
                    f"Tespit edilen IP'ler: {', '.join(list(ip_set)[:10])}"
                    f"{'...' if len(ip_set) > 10 else ''}"
                ),
                category="security",
                cooldown_key=f"subnet_flood:{subnet}",
            )
            return True

        return False
    except Exception as e:
        logger.debug(f"Subnet flood kontrol hatasi: {e}")
        return False


# --- v2: Koordineli Tarama Pattern Tespiti ---

async def _check_scan_pattern(client_ip: str, domain: str, qtype_name: str) -> bool:
    """Ayni qtype + ayni domain için farkli IP'lerden gelen sorgulari tespit et.
    3+ farkli IP -> koordineli tarama uyarısı.
    Dondurur: True = pattern tespit edildi (aggregated uyari yazildi).
    """
    if qtype_name not in SUSPICIOUS_QTYPES:
        return False

    try:
        redis = await _get_redis()

        # Domain'i normalize et (kucuk harf, sondaki nokta kaldir)
        normalized_domain = domain.rstrip(".").lower()
        pattern_key = f"dns:threat:pattern:{qtype_name}:{normalized_domain}"

        # Bu IP'yi pattern SET'ine ekle
        await redis.sadd(pattern_key, client_ip)

        # Ilk ekleme ise TTL ayarla
        ttl = await redis.ttl(pattern_key)
        if ttl == -1:
            await redis.expire(pattern_key, SCAN_PATTERN_WINDOW_SEC)

        # Benzersiz IP sayısıni kontrol et
        unique_ips = await redis.scard(pattern_key)

        if unique_ips >= SCAN_PATTERN_THRESHOLD:
            # Aggregated uyari yaz (cooldown ile spam onleme)
            cooldown_key = f"scan_pattern:{qtype_name}:{normalized_domain}"
            await _write_insight(
                severity=Severity.WARNING,
                message=(
                    f"Koordineli tarama tespiti: {unique_ips} benzersiz IP, "
                    f"hedef: {normalized_domain} ({qtype_name})"
                ),
                suggested_action=(
                    f"{unique_ips} farkli IP adresinden ayni hedefe ({normalized_domain}) "
                    f"{qtype_name} sorgusu gönderildi. "
                    "Subnet bazli engelleme otomatik degerlendiriliyor."
                ),
                category="security",
                cooldown_key=cooldown_key,
            )
            return True

        return False
    except Exception as e:
        logger.debug(f"Scan pattern kontrol hatasi: {e}")
        return False


# --- v2: Tehdit Skor Sistemi ---

async def _update_threat_score(client_ip: str, domain: str, qtype_name: str) -> int:
    """IP için tehdit skorunu güncelle ve kontrol et.
    Skor 15+ -> otomatik engel.
    Dondurur: guncel skor degeri.
    """
    try:
        redis = await _get_redis()
        score_key = f"dns:threat:score:{client_ip}"

        points = 0

        # Şüpheli sorgu tipi: +2 puan
        if qtype_name in SUSPICIOUS_QTYPES:
            points += 2

        # Bilinen tarama pattern'i eslesmesi: +5 puan
        # (Ayni qtype+domain için 3+ IP zaten gorulduyse)
        normalized_domain = domain.rstrip(".").lower()
        pattern_key = f"dns:threat:pattern:{qtype_name}:{normalized_domain}"
        pattern_count = await redis.scard(pattern_key)
        if pattern_count >= SCAN_PATTERN_THRESHOLD:
            points += 5

        # Subnet zaten flaglenmis mi: +3 puan
        subnet = _extract_subnet(client_ip)
        subnet_key = f"dns:threat:subnet:{subnet}"
        subnet_unique = await redis.scard(subnet_key)
        if subnet_unique >= 3:  # Subnet'te 3+ IP gorulduyse flag
            points += 3

        # DGA domain sorgusu: +10 puan
        if _is_dga_suspicious(domain):
            points += 10

        if points == 0:
            return 0

        # Skoru artir
        new_score = await redis.hincrby(score_key, "total", points)

        # TTL ayarla (her güncellemeye yenilenir)
        await redis.expire(score_key, THREAT_SCORE_TTL)

        # Detay bilgisi kaydet
        await redis.hset(score_key, "last_domain", domain)
        await redis.hset(score_key, "last_qtype", qtype_name)
        await redis.hset(score_key, "last_update", datetime.utcnow().isoformat())

        # Esik kontrolü: 15+ -> otomatik engel
        if new_score >= THREAT_SCORE_AUTO_BLOCK:
            # Zaten engelli mi kontrol et
            already_blocked = await redis.sismember("dns:threat:blocked", client_ip)
            if not already_blocked:
                reason = (
                    f"Tehdit skoru esigi asildi: {new_score} puan "
                    f"(esik: {THREAT_SCORE_AUTO_BLOCK}). "
                    f"Son sorgu: {domain} ({qtype_name})"
                )
                await auto_block_ip(client_ip, reason)
                logger.warning(
                    f"Tehdit skoru engeli: {client_ip} -> "
                    f"{new_score} puan, son: {domain} ({qtype_name})"
                )

        return new_score
    except Exception as e:
        logger.debug(f"Tehdit skor güncelleme hatasi: {e}")
        return 0


# --- Sorgu Analiz Fonksiyonlari ---

async def report_external_query(client_ip: str, domain: str, qtype_name: str):
    """Dış IP'den gelen DNS sorgusunu analiz et.
    Esik asilirsa otomatik engelle.

    v2 akışı:
    1. Mevcut rate limiting (sorgu/dk esigi)
    2. Subnet flood kontrolü (koordineli tarama)
    3. Tehdit skor güncelleme (birikimli puan)
    4. Tarama pattern kontrolü (ayni hedef, farkli IP'ler)
    5. Şüpheli sorgu tipi uyarısı (aggregation ile)
    """
    # Güvenilir IP korumasi - analiz yap ama engelleme yerine uyari oluştur
    is_trusted = client_ip in TRUSTED_IPS
    if is_trusted:
        try:
            redis = await _get_redis()
            # Güvenilir IP için rate tracking (engelleme yok, sadece izleme)
            key = f"dns:threat:ext:{client_ip}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
            # Esik asilirsa uyari oluştur (engelleme yok)
            if count == EXTERNAL_RATE_THRESHOLD:
                reason = (
                    f"Güvenilir IP'den asiri dis sorgu: {count} sorgu/dk "
                    f"(esik: {EXTERNAL_RATE_THRESHOLD}). "
                    f"Son sorgu: {domain} ({qtype_name})"
                )
                logger.warning(f"Güvenilir IP tehdit tespiti (engellenmedi): {client_ip} - {reason}")
                await _write_insight(
                    severity=Severity.WARNING,
                    message=(
                        f"Güvenilir IP'den tehdit tespiti: {client_ip} - {reason}. "
                        f"IP guvenilir listesinde oldugu için engellenmedi."
                    ),
                    suggested_action=(
                        f"Bu IP'yi ({client_ip}) kontrol edin. Cihaz ele gecirilmis olabilir."
                    ),
                    category="trusted_ip_threat",
                    cooldown_key=f"trusted_ext_flood:{client_ip}",
                )
                from app.services.telegram_service import notify_trusted_ip_threat
                await notify_trusted_ip_threat(client_ip, reason)
        except Exception as e:
            logger.debug(f"Güvenilir IP analiz hatasi: {e}")
        return
    try:
        redis = await _get_redis()

        # --- 1. Mevcut: Sorgu sayacıni artir (60 saniyelik pencere) ---
        key = f"dns:threat:ext:{client_ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)

        # Toplam dis sorgu sayacıni artir
        await redis.hincrby("dns:threat:stats", "total_external_blocked", 1)

        # Esik kontrolü
        if count >= EXTERNAL_RATE_THRESHOLD:
            reason = (
                f"Dış IP flood: {count} sorgu/dk "
                f"(esik: {EXTERNAL_RATE_THRESHOLD}). "
                f"Son sorgu: {domain} ({qtype_name})"
            )
            await auto_block_ip(client_ip, reason)
            return

        # --- 2. v2: Subnet flood kontrolü ---
        subnet_blocked = await _check_subnet_flood(client_ip, domain, qtype_name)
        if subnet_blocked:
            return  # Subnet engellendi, baska işlem gerekmiyor

        # --- 3. v2: Tehdit skor güncelleme ---
        score = await _update_threat_score(client_ip, domain, qtype_name)
        if score >= THREAT_SCORE_AUTO_BLOCK:
            return  # Skor esigi asildi, IP zaten engellendi

        # --- 4. v2: Tarama pattern kontrolü ---
        pattern_detected = await _check_scan_pattern(client_ip, domain, qtype_name)

        # --- 5. Şüpheli sorgu tipi (aggregation ile, v2: 30 dk cooldown) ---
        if qtype_name in SUSPICIOUS_QTYPES:
            await redis.hincrby("dns:threat:stats", "total_suspicious", 1)

            # v2: Eger koordineli tarama pattern'i tespit edildiyse,
            # bireysel uyari yazma (aggregated uyari zaten yazildi)
            if not pattern_detected:
                await _write_insight(
                    severity=Severity.WARNING,
                    message=(
                        f"Dış IP'den şüpheli DNS sorgusu: {client_ip} -> "
                        f"{domain} ({qtype_name})"
                    ),
                    suggested_action=(
                        f"Bu IP'yi engellemek için: AI Chat'ten "
                        f"'{client_ip} IP engelle' yazin."
                    ),
                    category="security",
                    cooldown_key=f"ext_suspicious:{client_ip}",
                )
    except Exception as e:
        logger.debug(f"Dış sorgu analiz hatasi: {e}")


async def report_local_query(
    client_ip: str, domain: str, qtype_name: str
):
    """Yerel IP'den gelen DNS sorgusunu analiz et.
    Şüpheli durumlar için uyari oluştur.
    """
    try:
        redis = await _get_redis()

        # Sorgu sayacıni artir (60 saniyelik pencere)
        key = f"dns:threat:local:{client_ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)

        # Yerel flood tespiti
        if count == LOCAL_RATE_THRESHOLD:
            await redis.hincrby("dns:threat:stats", "total_suspicious", 1)
            await _write_insight(
                severity=Severity.WARNING,
                message=(
                    f"Yerel cihaz asiri DNS sorgusu: {client_ip} -> "
                    f"{count} sorgu/dk (esik: {LOCAL_RATE_THRESHOLD}). "
                    f"Cihaz ele gecirilmis veya malware bulasmis olabilir."
                ),
                suggested_action=(
                    f"Cihazi (IP: {client_ip}) kontrol edin. "
                    "Malware taramas yapin veya cihazi agdan cikarin."
                ),
                category="anomaly",
                cooldown_key=f"local_flood:{client_ip}",
            )

        # Şüpheli sorgu tipi kontrolü (sadece belirli aralıklarda uyar)
        if qtype_name in SUSPICIOUS_QTYPES and count <= 3:
            await redis.hincrby("dns:threat:stats", "total_suspicious", 1)
            await _write_insight(
                severity=Severity.INFO,
                message=(
                    f"Yerel cihazdan şüpheli DNS sorgusu: {client_ip} -> "
                    f"{domain} ({qtype_name})"
                ),
                category="anomaly",
                cooldown_key=f"local_suspicious:{client_ip}:{qtype_name}",
            )

        # DGA tespiti (her 50 sorguda bir kontrol - performans için)
        if count % 50 == 1 and _is_dga_suspicious(domain):
            await redis.hincrby("dns:threat:stats", "total_suspicious", 1)
            entropy = calculate_entropy(domain)
            await _write_insight(
                severity=Severity.WARNING,
                message=(
                    f"DGA şüpheli domain tespiti: {client_ip} -> {domain} "
                    f"(entropi: {entropy:.2f}, esik: {DGA_ENTROPY_THRESHOLD}). "
                    "Olasi botnet/malware C2 iletisimi."
                ),
                suggested_action=(
                    f"Cihazi (IP: {client_ip}) malware taramasindan gecirin. "
                    f"Domain '{domain}' engellemeyi dusunun."
                ),
                category="anomaly",
                cooldown_key=f"dga:{client_ip}",
            )

        # Domain reputation kontrolü (her 10 sorguda bir - performans için)
        if count % 10 == 1:
            try:
                from app.services.domain_reputation import calculate_reputation
                rep = await calculate_reputation(domain)
                if rep["risk_level"] in ("high", "critical"):
                    await _write_insight(
                        severity=Severity.WARNING,
                        message=(
                            f"Yuksek riskli domain tespiti: {client_ip} -> {domain} "
                            f"(skor: {rep['score']}/100) - {', '.join(rep['factors'])}"
                        ),
                        suggested_action=f"Bu domain'i engellemek için: '{domain} engelle'",
                        category="reputation",
                        cooldown_key=f"reputation:{domain}",
                    )
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Yerel sorgu analiz hatasi: {e}")


# --- Cihaz Risk Degerlendirme (Faz 4) ---

async def evaluate_device_risk(client_ip: str, device_id: int) -> dict:
    """Cihaz risk değerlendirmesini yap.
    Returns: {"risk_score": 0-100, "risk_level": str, "factors": list, "suggest_isolation": bool}
    """
    factors = []
    score = 0

    try:
        redis = await _get_redis()

        # 1. Şüpheli sorgu tipi sayısı (HINFO, WKS vb.)
        qt_key = f"dns:fp:{client_ip}:qtypes"
        qtypes = await redis.hgetall(qt_key)
        suspicious_count = sum(
            int(v) for k, v in qtypes.items()
            if (k.decode() if isinstance(k, bytes) else k) in SUSPICIOUS_QTYPES
        )
        if suspicious_count >= 10:
            score += 30
            factors.append(f"Şüpheli sorgu tipi: {suspicious_count} adet")
        elif suspicious_count >= 3:
            score += 15
            factors.append(f"Şüpheli sorgu tipi: {suspicious_count} adet")

        # 2. Tehdit skoru (birikimli)
        score_key = f"dns:threat:score:{client_ip}"
        threat_total = await redis.hget(score_key, "total")
        if threat_total:
            threat_val = int(threat_total)
            if threat_val >= 10:
                score += 20
                factors.append(f"Tehdit skoru: {threat_val}")

        # 3. Yerel flood sayacı
        local_key = f"dns:threat:local:{client_ip}"
        local_count = await redis.get(local_key)
        if local_count and int(local_count) >= 200:
            score += 15
            factors.append(f"Yuksek sorgu hacmi: {local_count}/dk")

        # 4. DGA domain sorgusu kontrolü (son 10 dk'daki domainler)
        fp_key = f"dns:fp:{client_ip}:domains"
        cached_domains = await redis.smembers(fp_key)
        dga_count = 0
        for d in cached_domains:
            d_str = d.decode() if isinstance(d, bytes) else d
            if _is_dga_suspicious(d_str):
                dga_count += 1
        if dga_count >= 3:
            score += 40
            factors.append(f"DGA şüpheli domain: {dga_count} adet")
        elif dga_count >= 1:
            score += 15
            factors.append(f"DGA şüpheli domain: {dga_count} adet")

        # 5. Domain reputation ortalamasi (cache'lenenleri kontrol et)
        high_rep_count = 0
        for d in list(cached_domains)[:20]:  # performans için max 20
            d_str = d.decode() if isinstance(d, bytes) else d
            rep_key = f"dns:reputation:{d_str}"
            rep_score = await redis.hget(rep_key, "score")
            if rep_score and int(rep_score) >= 60:
                high_rep_count += 1
        if high_rep_count >= 3:
            score += 30
            factors.append(f"Yuksek riskli domain erişimi: {high_rep_count} adet")

    except Exception as e:
        logger.debug(f"Cihaz risk değerlendirme hatasi ({client_ip}): {e}")

    # Skoru sinirla
    score = max(0, min(100, score))

    # Risk seviyesi
    if score >= 70:
        risk_level = "dangerous"
    elif score >= 40:
        risk_level = "suspicious"
    else:
        risk_level = "safe"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "factors": factors if factors else ["Normal davranis"],
        "suggest_isolation": score >= 70,
    }


async def evaluate_all_online_devices():
    """Tum online cihazlarin risk değerlendirmesini yap ve DB'ye yaz."""
    try:
        from sqlalchemy import select, update as sql_update
        from app.models.device import Device

        async with async_session_factory() as session:
            result = await session.execute(
                select(Device).where(Device.is_online == True)
            )
            devices = result.scalars().all()

            for device in devices:
                if not device.ip_address:
                    continue

                assessment = await evaluate_device_risk(device.ip_address, device.id)

                changed = False
                if device.risk_score != assessment["risk_score"]:
                    device.risk_score = assessment["risk_score"]
                    changed = True
                if device.risk_level != assessment["risk_level"]:
                    device.risk_level = assessment["risk_level"]
                    changed = True

                device.last_risk_assessment = datetime.utcnow()

                if changed and assessment["suggest_isolation"]:
                    logger.warning(
                        f"Izolasyon onerisi: {device.hostname or device.ip_address} "
                        f"(skor: {assessment['risk_score']})"
                    )
                    # Telegram bildirimi
                    try:
                        await notify_device_isolation_suggestion(
                            ip=device.ip_address,
                            hostname=device.hostname,
                            device_type=device.device_type,
                            risk_factors=assessment["factors"],
                            risk_score=assessment["risk_score"],
                        )
                    except Exception:
                        pass

                    await _write_insight(
                        severity=Severity.CRITICAL,
                        message=(
                            f"Cihaz izolasyon onerisi: "
                            f"{device.hostname or device.ip_address} "
                            f"(skor: {assessment['risk_score']}/100) - "
                            f"{', '.join(assessment['factors'])}"
                        ),
                        suggested_action=(
                            f"Cihazi engellemek için: "
                            f"'{device.hostname or device.ip_address} engelle'"
                        ),
                        category="isolation",
                        cooldown_key=f"isolation:{device.ip_address}",
                    )

            await session.commit()
            logger.info(f"Risk değerlendirmesi tamamlandi: {len(devices)} cihaz")

    except Exception as e:
        logger.error(f"Toplu risk değerlendirme hatasi: {e}")


# --- Saatlik Trend Analizi (Faz 5) ---

async def analyze_hourly_trends() -> dict | None:
    """Son 1 saatlik DNS trafiğini analiz et, trend raporu oluştur.
    Redis'ten sayaclari okur, onceki saat ile karsilastirir, anomali tespit eder.
    """
    try:
        redis = await _get_redis()
        from app.db.session import async_session_factory
        from app.models.dns_query_log import DnsQueryLog
        from app.models.device import Device
        from sqlalchemy import select, func
        from datetime import timedelta

        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)
        hour_key = now.strftime("%Y%m%d%H")
        prev_key = (now - timedelta(hours=1)).strftime("%Y%m%d%H")

        async with async_session_factory() as session:
            # Son 1 saatlik sorgu sayısı
            total_q = await session.scalar(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= one_hour_ago
                )
            ) or 0

            # Engellenen sorgu sayısı
            blocked_q = await session.scalar(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= one_hour_ago,
                    DnsQueryLog.blocked == True,
                )
            ) or 0

            # Onceki saat sayilari (karsilastirma için)
            prev_total = await session.scalar(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= two_hours_ago,
                    DnsQueryLog.timestamp < one_hour_ago,
                )
            ) or 0

            # Aktif cihaz sayısı
            active_devices = await session.scalar(
                select(func.count(Device.id)).where(Device.is_online == True)
            ) or 0

            # En cok sorgulayan cihazlar (top 5)
            top_clients_q = await session.execute(
                select(
                    DnsQueryLog.client_ip,
                    func.count(DnsQueryLog.id).label("cnt"),
                ).where(
                    DnsQueryLog.timestamp >= one_hour_ago
                ).group_by(DnsQueryLog.client_ip).order_by(
                    func.count(DnsQueryLog.id).desc()
                ).limit(5)
            )
            top_clients = [
                {"ip": row[0], "count": row[1]}
                for row in top_clients_q.all()
            ]

            # En cok engellenen domainler (top 5)
            top_blocked_q = await session.execute(
                select(
                    DnsQueryLog.domain,
                    func.count(DnsQueryLog.id).label("cnt"),
                ).where(
                    DnsQueryLog.timestamp >= one_hour_ago,
                    DnsQueryLog.blocked == True,
                ).group_by(DnsQueryLog.domain).order_by(
                    func.count(DnsQueryLog.id).desc()
                ).limit(5)
            )
            top_blocked = [
                {"domain": row[0], "count": row[1]}
                for row in top_blocked_q.all()
            ]

        # Engelleme oranı
        block_rate = (blocked_q / total_q * 100) if total_q > 0 else 0

        # Degisim oranı
        change_pct = 0
        if prev_total > 0:
            change_pct = ((total_q - prev_total) / prev_total) * 100

        stats = {
            "hour": hour_key,
            "total_queries": total_q,
            "blocked_queries": blocked_q,
            "block_rate": block_rate,
            "active_devices": active_devices,
            "change_from_previous": round(change_pct, 1),
            "top_clients": top_clients,
            "top_blocked": top_blocked,
        }

        # Redis'e kaydet (72 saat TTL)
        trend_key = f"dns:trends:hourly:{hour_key}"
        import json
        await redis.set(trend_key, json.dumps(stats), ex=259200)  # 72 saat

        # Anomali tespiti: %50+ sapma
        if prev_total > 0 and abs(change_pct) >= 50:
            direction = "artis" if change_pct > 0 else "azalis"
            await _write_insight(
                severity=Severity.WARNING,
                message=(
                    f"Saatlik DNS trafik anomalisi: %{abs(change_pct):.0f} {direction} "
                    f"({prev_total} -> {total_q} sorgu)"
                ),
                suggested_action="Ag trafiğini ve aktif cihazlari kontrol edin.",
                category="anomaly",
                cooldown_key=f"hourly_anomaly:{hour_key}",
            )

        # Telegram özet bildirimi
        top_devices_text = "\n".join(
            f"  {c['ip']}: {c['count']} sorgu"
            for c in top_clients[:3]
        ) or "  -"
        top_blocked_text = "\n".join(
            f"  {b['domain']}: {b['count']}"
            for b in top_blocked[:3]
        ) or "  -"

        from app.services.telegram_service import notify_hourly_summary
        await notify_hourly_summary({
            "total_queries": total_q,
            "blocked_queries": blocked_q,
            "block_rate": block_rate,
            "active_devices": active_devices,
            "top_devices_text": top_devices_text,
            "top_blocked_text": top_blocked_text,
        })

        logger.info(
            f"Saatlik trend: {total_q} sorgu, {blocked_q} engel "
            f"(%{block_rate:.1f}), {active_devices} cihaz"
        )
        return stats

    except Exception as e:
        logger.error(f"Saatlik trend analizi hatasi: {e}")
        return None


async def get_hourly_trends(hours: int = 24) -> list[dict]:
    """Son X saatlik trend verilerini Redis'ten oku."""
    try:
        redis = await _get_redis()
        import json
        from datetime import timedelta

        results = []
        now = datetime.utcnow()

        for i in range(hours):
            dt = now - timedelta(hours=i)
            hour_key = dt.strftime("%Y%m%d%H")
            trend_key = f"dns:trends:hourly:{hour_key}"
            data = await redis.get(trend_key)
            if data:
                results.append(json.loads(data))

        return list(reversed(results))  # Eski -> yeni sirasiyla
    except Exception as e:
        logger.error(f"Trend okuma hatasi: {e}")
        return []


# --- Worker Dongusu ---

async def _cleanup_expired_blocks():
    """Süresi dolan IP engellerini temizle."""
    try:
        redis = await _get_redis()
        blocked_ips = await redis.smembers("dns:threat:blocked")

        removed = 0
        for ip in blocked_ips:
            # Expire key'i yoksa engel süresi dolmus demektir
            exists = await redis.exists(f"dns:threat:block_expire:{ip}")
            if not exists:
                await redis.srem("dns:threat:blocked", ip)
                removed += 1
                logger.info(f"IP engeli süresi doldu, kaldırıldı: {ip}")

                # nftables setinden de kaldir
                try:
                    from app.hal import linux_nftables as nft
                    await nft.remove_blocked_ip(ip)
                except Exception:
                    pass

        if removed:
            await _write_insight(
                severity=Severity.INFO,
                message=f"{removed} IP'nin engel süresi doldu, otomatik kaldırıldı.",
                category="security",
            )
    except Exception as e:
        logger.error(f"Engel temizleme hatasi: {e}")


async def _cleanup_cooldowns():
    """Eski cooldown kayitlarini temizle (bellek tasmasini onle)."""
    now = time.monotonic()
    stale = [k for k, t in _recent_insights.items()
             if now - t > _INSIGHT_COOLDOWN * 2]
    for k in stale:
        _recent_insights.pop(k, None)


async def start_threat_analyzer_worker():
    """Tehdit analizci worker dongusu."""
    logger.info("Tehdit Analizci worker başlatildi (v2: subnet+pattern+score).")

    cycle = 0
    while True:
        await asyncio.sleep(60)  # Her dakika
        cycle += 1

        # Her 5 dakikada süresi dolan engelleri temizle
        if cycle % 5 == 0:
            await _cleanup_expired_blocks()
            await _cleanup_cooldowns()

        # Her 10 dakikada online cihazlarin risk değerlendirmesi
        if cycle % 10 == 0:
            await evaluate_all_online_devices()
            # Fingerprint cooldown temizligi
            try:
                from app.services.dns_fingerprint import cleanup_cooldowns
                cleanup_cooldowns()
            except Exception:
                pass

        # Her 60 dakikada saatlik trend analizi
        if cycle % 60 == 0:
            await analyze_hourly_trends()

        # Her 30 dakikada özet istatistik logla
        if cycle % 30 == 0:
            stats = await get_threat_stats()
            if stats["total_auto_blocks"] > 0 or stats["blocked_ip_count"] > 0:
                logger.info(
                    f"Tehdit Özeti: {stats['blocked_ip_count']} engelli IP, "
                    f"{stats['total_auto_blocks']} otomatik engel, "
                    f"{stats['total_suspicious']} şüpheli sorgu"
                )




async def sync_blocked_ips_to_nftables():
    """Başlangicta Redis'teki engelli IP'leri nftables'a senkronize et.
    main.py lifespan'dan cagirilir.
    """
    try:
        from app.hal import linux_nftables as nft
        redis = await _get_redis()

        # 1. Bireysel IP'leri senkronize et
        blocked_ips = await redis.smembers("dns:threat:blocked")
        ip_timeout_pairs = []

        for ip in blocked_ips:
            ip_str = ip if isinstance(ip, str) else ip.decode()
            if "/" in ip_str:
                continue
            ttl = await redis.ttl(f"dns:threat:block_expire:{ip_str}")
            if ttl > 0:
                ip_timeout_pairs.append((ip_str, ttl))
            elif ttl == -1:
                ip_timeout_pairs.append((ip_str, 31536000))

        if ip_timeout_pairs:
            await nft.sync_blocked_ips(ip_timeout_pairs)
            logger.info(f"Başlangic nftables sync: {len(ip_timeout_pairs)} IP")

        # 2. Subnet bloklarini senkronize et
        cursor = 0
        subnet_count = 0
        while True:
            cursor, keys = await redis.scan(
                cursor, match="dns:threat:subnet_blocked:*", count=100
            )
            for key in keys:
                key_str = key if isinstance(key, str) else key.decode()
                subnet = key_str.replace("dns:threat:subnet_blocked:", "")
                ttl = await redis.ttl(key_str)
                if ttl > 0:
                    await nft.add_blocked_subnet(subnet, ttl)
                    subnet_count += 1
            if cursor == 0:
                break

        if subnet_count:
            logger.info(f"Başlangic nftables sync: {subnet_count} subnet")

        total = len(ip_timeout_pairs) + subnet_count
        if total == 0:
            logger.info("Başlangic nftables sync: engelli IP/subnet yok")
        else:
            logger.info(f"Başlangic nftables sync tamamlandi: {total} toplam engel")

    except Exception as e:
        logger.error(f"Başlangic nftables sync hatasi: {e}")

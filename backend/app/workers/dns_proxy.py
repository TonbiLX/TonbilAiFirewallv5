# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Gercek DNS Proxy: Port 53'te dinler (UDP), Port 853'te DoT dinler (TCP+TLS),
# Redis'ten engelleme kontrolü yapar, engelsiz domainleri upstream DNS'e yonlendirir.
# AdGuard Home / Pi-hole benzeri DNS sinkhole islevi.
# Android Özel DNS (Private DNS) desteği için DNS-over-TLS (DoT).

import asyncio
import logging
import struct
import socket
import ssl
import os
import time
import urllib.request
from datetime import datetime
from collections import deque

import redis.asyncio as aioredis

from app.workers.device_discovery import discover_device
from app.workers.threat_analyzer import (
    is_ip_blocked, report_external_query, report_local_query,
    is_trusted_ip,
    SUSPICIOUS_QTYPES as THREAT_SUSPICIOUS_QTYPES,
)
from app.services.dns_fingerprint import analyze_fingerprint

logger = logging.getLogger("tonbilai.dns_proxy")

# Upstream DNS sunuculari
UPSTREAM_DNS = [
    ("1.1.1.1", 53),      # Cloudflare
    ("8.8.8.8", 53),      # Google
]

# 5651 Uyum: WAN IP cache (periyodik güncelleme)
_wan_ip_cache: str = ""
_wan_ip_last_check: float = 0.0
_WAN_IP_REFRESH_INTERVAL = 300  # 5 dakikada bir güncelle


def _detect_wan_ip() -> str:
    """Sistemin WAN (dis) IP adresini tespit et."""
    # 1. Ortam degiskeninden al (öncelikli)
    env_wan = os.environ.get("WAN_IP", "").strip()
    if env_wan:
        return env_wan
    # 2. HTTP API ile tespit
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TonbilAiOS/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                ip = resp.read().decode("utf-8").strip()
                if ip and len(ip) < 46:
                    return ip
        except Exception:
            continue
    return ""


def get_wan_ip() -> str:
    """Cachelenmis WAN IP dondur, gerekirse güncelle."""
    global _wan_ip_cache, _wan_ip_last_check
    now = time.monotonic()
    if not _wan_ip_cache or (now - _wan_ip_last_check) > _WAN_IP_REFRESH_INTERVAL:
        _wan_ip_last_check = now
        detected = _detect_wan_ip()
        if detected:
            _wan_ip_cache = detected
            logger.info(f"5651: WAN IP güncellendi: {detected}")
    return _wan_ip_cache


# Izin verilen yerel ag bloklari (RFC 1918 + Docker)
ALLOWED_NETWORKS = [
    ("192.168.", ),
    ("10.", ),
    ("172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
     "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
     "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31."),
    ("127.", ),
]

# Dış IP rate limiting: IP başına saniyede max sorgu
_rate_limit_buckets: dict[str, list] = {}
RATE_LIMIT_PER_SEC = 5
_RATE_LIMIT_CLEANUP_INTERVAL = 60
_last_rate_cleanup = 0.0


def _cleanup_rate_limit_buckets():
    """Stale rate limit bucket'larini temizle (bellek sizmasi onleme)."""
    global _last_rate_cleanup
    now = time.monotonic()
    if now - _last_rate_cleanup < _RATE_LIMIT_CLEANUP_INTERVAL:
        return
    _last_rate_cleanup = now
    stale_ips = [
        ip for ip, bucket in _rate_limit_buckets.items()
        if not bucket or (now - bucket[-1]) > 60
    ]
    for ip in stale_ips:
        del _rate_limit_buckets[ip]


def is_local_ip(ip: str) -> bool:
    """IP adresi yerel ag bloklarindan mi kontrol et."""
    for group in ALLOWED_NETWORKS:
        for prefix in group:
            if ip.startswith(prefix):
                return True
    return False


def check_rate_limit(ip: str) -> bool:
    """Dış IP'ler için rate limit kontrolü. True = izin ver, False = engelle."""
    _cleanup_rate_limit_buckets()
    now = time.monotonic()
    if ip not in _rate_limit_buckets:
        _rate_limit_buckets[ip] = [now]
        return True
    bucket = _rate_limit_buckets[ip]
    # Son 1 saniyedeki istekleri tut
    _rate_limit_buckets[ip] = [t for t in bucket if now - t < 1.0]
    if len(_rate_limit_buckets[ip]) >= _cached_rate_limit:
        return False
    _rate_limit_buckets[ip].append(now)
    return True

# DNS kayit tipleri
DNS_TYPES = {
    1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 10: "NULL", 11: "WKS",
    12: "PTR", 13: "HINFO", 15: "MX", 16: "TXT", 28: "AAAA",
    33: "SRV", 65: "HTTPS", 252: "AXFR", 255: "ANY",
}

# Yerel cihazlardan gelen bu sorgu tipleri otomatik engellenir (DNS tarama/kesif onleme)
# TXT (16) engellenMEZ: Let's Encrypt, SPF, DKIM vb. için gerekli
BLOCKED_QTYPES = {10, 252, 255}  # NULL, WKS, HINFO, AXFR, ANY

# Sinkhole IP (engellenen domainler için)
# Pi'nin IP'si: tarayici bu IP'ye baglaninca nginx block page gosterir
SINKHOLE_IPV4 = "192.168.1.2"
SINKHOLE_IPV6 = "::"

# --- Redis Hot-Reload Cache (30sn aralikla guncellenir) ---
_cached_rate_limit = RATE_LIMIT_PER_SEC
_cached_blocked_qtypes = BLOCKED_QTYPES.copy()
_cached_sinkhole_v4 = SINKHOLE_IPV4
_cached_sinkhole_v6 = SINKHOLE_IPV6
_cache_ts = 0.0

async def _refresh_dns_security_cache(redis_client):
    """30 saniyede bir Redis security:config HASH'ten DNS guvenlik ayarlarini oku."""
    global _cached_rate_limit, _cached_blocked_qtypes, _cached_sinkhole_v4, _cached_sinkhole_v6, _cache_ts
    import time as _time
    now = _time.monotonic()
    if now - _cache_ts < 30:
        return
    _cache_ts = now
    try:
        val = await redis_client.hget("security:config", "dns_rate_limit_per_sec")
        if val:
            _cached_rate_limit = int(val)
        val = await redis_client.hget("security:config", "dns_blocked_qtypes")
        if val:
            _cached_blocked_qtypes = {int(x.strip()) for x in val.split(",") if x.strip()}
        val = await redis_client.hget("security:config", "sinkhole_ipv4")
        if val:
            _cached_sinkhole_v4 = val
        val = await redis_client.hget("security:config", "sinkhole_ipv6")
        if val:
            _cached_sinkhole_v6 = val
    except Exception:
        pass

# Yerel ag DNS override: guard.tonbilx.com -> Pi yerel IP (DoT/Private DNS için)
LOCAL_DNS_OVERRIDES = {
    "wall.tonbilx.com": "192.168.1.4",
    "guard.tonbilx.com": "192.168.1.2",
}


def _is_local_client(client_ip: str) -> bool:
    """İstemcinin yerel agdan mi yoksa disindan mi geldigini kontrol et.
    Yerel agdan gelenler için LOCAL_DNS_OVERRIDES uygulanir,
    dis DoT kullanıcılarinda upstream DNS'e yonlendirilir."""
    try:
        import ipaddress as _ipa
        addr = _ipa.ip_address(client_ip)
        return addr.is_private or addr.is_loopback
    except (ValueError, TypeError):
        return True  # Guvenli taraf: bilinmeyen IP yerel kabul edilir


def parse_dns_query(data: bytes) -> dict:
    """DNS sorgusunu ayristir."""
    if len(data) < 12:
        return None
    # Maks payload kontrolü (UDP DNS max 512 byte, EDNS0 ile 4096)
    if len(data) > 4096:
        logger.warning(f"DNS paketi cok buyuk: {len(data)} bytes, dusuruldu")
        return None

    transaction_id = struct.unpack("!H", data[0:2])[0]
    flags = struct.unpack("!H", data[2:4])[0]
    qdcount = struct.unpack("!H", data[4:6])[0]

    # Domain adini ayristir
    offset = 12
    labels = []
    while offset < len(data):
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length >= 192:  # Pointer
            break
        offset += 1
        labels.append(data[offset:offset + length].decode("ascii", errors="ignore"))
        offset += length

    domain = ".".join(labels)

    # Domain uzunluk kontrolü (RFC 1035: max 253 karakter)
    if len(domain) > 253:
        logger.warning(f"DNS domain cok uzun: {len(domain)} karakter, dusuruldu")
        return None

    # Sorgu tipini oku
    qtype = struct.unpack("!H", data[offset:offset + 2])[0] if offset + 2 <= len(data) else 1

    return {
        "transaction_id": transaction_id,
        "flags": flags,
        "domain": domain.lower(),
        "qtype": qtype,
        "qtype_name": DNS_TYPES.get(qtype, f"TYPE{qtype}"),
        "raw": data,
    }


def build_blocked_response(query_data: bytes, qtype: int) -> bytes:
    """Engellenen domain için DNS yaniti oluştur (0.0.0.0 / :: dondu)."""
    transaction_id = query_data[0:2]
    flags = struct.pack("!H", 0x8580)
    counts = struct.pack("!HHHH", 1, 1, 0, 0)

    # Question section (orijinalden kopyala)
    offset = 12
    while offset < len(query_data):
        length = query_data[offset]
        if length == 0:
            offset += 1
            break
        if length >= 192:
            offset += 2
            break
        offset += 1 + length
    offset += 4  # QTYPE + QCLASS
    question = query_data[12:offset]

    # Answer section
    answer_name = struct.pack("!H", 0xC00C)
    # TTL=2 saniye: engel kaldirildiginda telefon cache'i hizla biter.
    # Pi-hole de ayni TTL kullanir. 300s cihaz unblock sonrasi soruna yol aciyor.
    blocked_ttl = 2

    if qtype == 28:  # AAAA
        answer_type = struct.pack("!H", 28)
        answer_class = struct.pack("!H", 1)
        answer_ttl = struct.pack("!I", blocked_ttl)
        rdata = socket.inet_pton(socket.AF_INET6, _cached_sinkhole_v6)
        answer_rdlength = struct.pack("!H", len(rdata))
    else:  # A
        answer_type = struct.pack("!H", 1)
        answer_class = struct.pack("!H", 1)
        answer_ttl = struct.pack("!I", blocked_ttl)
        rdata = socket.inet_aton(_cached_sinkhole_v4)
        answer_rdlength = struct.pack("!H", 4)

    answer = answer_name + answer_type + answer_class + answer_ttl + answer_rdlength + rdata
    return transaction_id + flags + counts + question + answer


def build_override_response(query_data: bytes, qtype: int, override_ip: str) -> bytes:
    """DNS sorgusuna özel IP ile yanit ver (LOCAL_DNS_OVERRIDES için)."""
    transaction_id = query_data[0:2]
    flags = struct.pack("!H", 0x8180)  # Standard response, no error
    counts = struct.pack("!HHHH", 1, 1, 0, 0)

    # Question section (orijinalden kopyala)
    offset = 12
    while offset < len(query_data):
        length = query_data[offset]
        if length == 0:
            offset += 1
            break
        if length >= 192:
            offset += 2
            break
        offset += 1 + length
    offset += 4  # QTYPE + QCLASS
    question = query_data[12:offset]

    # Answer section
    answer_name = struct.pack("!H", 0xC00C)

    if qtype == 28:  # AAAA - IPv6 yok, bos yanit dondur
        flags = struct.pack("!H", 0x8180)
        counts = struct.pack("!HHHH", 1, 0, 0, 0)
        return transaction_id + flags + counts + question
    else:  # A
        answer_type = struct.pack("!H", 1)
        answer_class = struct.pack("!H", 1)
        answer_ttl = struct.pack("!I", 60)  # Kısa TTL
        rdata = socket.inet_aton(override_ip)
        answer_rdlength = struct.pack("!H", 4)

    answer = answer_name + answer_type + answer_class + answer_ttl + answer_rdlength + rdata
    return transaction_id + flags + counts + question + answer


async def is_domain_blocked(redis_client: aioredis.Redis, domain: str) -> bool:
    """Domain engelli mi kontrol et. Ust domain yuruyusu yapar."""
    parts = domain.lower().split(".")
    for i in range(len(parts)):
        check_domain = ".".join(parts[i:])
        if len(check_domain) > 3:
            if await redis_client.sismember("dns:blocked_domains", check_domain):
                return True
    return False


async def is_service_domain(
    redis_client: aioredis.Redis, domain: str
) -> bool:
    """Domain herhangi bir tanimli servisin domain'i mi? (subdomain yuruyusu ile)"""
    parts = domain.lower().split(".")
    for i in range(len(parts)):
        check_domain = ".".join(parts[i:])
        if len(check_domain) > 3:
            if await redis_client.sismember("dns:all_service_domains", check_domain):
                return True
    return False


async def check_device_service_block(
    redis_client: aioredis.Redis, client_ip: str, domain: str
) -> str | None:
    """Cihaz bazinda servis engelleme kontrolü.
    Engellenmisse servis ID'sini dondurur, degilse None."""
    # 1. IP'den device_id bul
    device_id = await redis_client.get(f"dns:ip_to_device:{client_ip}")
    if not device_id:
        return None

    # 2. Cihazin engelli servis ID'lerini al
    service_ids = await redis_client.smembers(
        f"dns:device_blocked_services:{device_id}"
    )
    if not service_ids:
        return None

    # 3. Her servisin domain listesinde kontrol et (subdomain yuruyusu ile)
    parts = domain.lower().split(".")
    for service_id in service_ids:
        redis_key = f"dns:service_domains:{service_id}"
        for i in range(len(parts)):
            check_domain = ".".join(parts[i:])
            if len(check_domain) > 3:
                if await redis_client.sismember(redis_key, check_domain):
                    return service_id

    return None


async def check_device_custom_rule(
    redis_client: aioredis.Redis, client_ip: str, domain: str
) -> str | None:
    """Cihaz bazinda özel DNS kuralı kontrolü (subdomain yuruyusu ile).
    Returns: "allow" (override), "block" (engel), None (kural yok)."""
    device_id = await redis_client.get(f"dns:ip_to_device:{client_ip}")
    if not device_id:
        return None

    parts = domain.lower().split(".")

    # Öncelik 1: Allow kuralı (tum engelleri override eder)
    for i in range(len(parts)):
        check_domain = ".".join(parts[i:])
        if len(check_domain) > 3:
            if await redis_client.sismember(
                f"dns:device_custom_allowed:{device_id}", check_domain
            ):
                return "allow"

    # Öncelik 2: Block kuralı
    for i in range(len(parts)):
        check_domain = ".".join(parts[i:])
        if len(check_domain) > 3:
            if await redis_client.sismember(
                f"dns:device_custom_blocked:{device_id}", check_domain
            ):
                return "block"

    return None


async def is_profile_domain_blocked(
    redis_client: aioredis.Redis, profile_id: str, domain: str
) -> bool:
    """Profil bazinda domain engelleme kontrolu (subdomain yuruyusu ile)."""
    parts = domain.lower().split(".")
    for i in range(len(parts)):
        check_domain = ".".join(parts[i:])
        if len(check_domain) > 3:
            if await redis_client.sismember(
                f"dns:profile_domains:{profile_id}", check_domain
            ):
                return True
    return False


async def forward_to_upstream(data: bytes) -> bytes:
    """DNS sorgusunu upstream sunucuya yonlendir."""
    for upstream_ip, upstream_port in UPSTREAM_DNS:
        try:
            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            await loop.run_in_executor(None, sock.sendto, data, (upstream_ip, upstream_port))
            response, _ = await loop.run_in_executor(None, sock.recvfrom, 4096)
            sock.close()
            return response
        except Exception as e:
            logger.debug(f"Upstream {upstream_ip} hatasi: {e}")
            try:
                sock.close()
            except:
                pass
            continue
    logger.error("Tum upstream DNS sunuculari başarısız!")
    return None


def extract_answer_ip(response: bytes) -> str:
    """DNS yanitindan IP adresini cikar."""
    if not response or len(response) < 12:
        return ""
    try:
        ancount = struct.unpack("!H", response[6:8])[0]
        if ancount == 0:
            return ""
        # Question section'i atla
        offset = 12
        while offset < len(response) and response[offset] != 0:
            if response[offset] >= 192:
                offset += 2
                break
            offset += response[offset] + 1
        else:
            offset += 1
        offset += 4  # QTYPE + QCLASS

        # Ilk answer'i oku
        # Name (pointer veya label)
        if offset < len(response) and response[offset] >= 192:
            offset += 2
        else:
            while offset < len(response) and response[offset] != 0:
                offset += response[offset] + 1
            offset += 1

        if offset + 10 > len(response):
            return ""

        atype = struct.unpack("!H", response[offset:offset+2])[0]
        offset += 8  # type + class + ttl
        rdlen = struct.unpack("!H", response[offset:offset+2])[0]
        offset += 2

        if atype == 1 and rdlen == 4 and offset + 4 <= len(response):
            return ".".join(str(b) for b in response[offset:offset+4])
        elif atype == 28 and rdlen == 16 and offset + 16 <= len(response):
            return socket.inet_ntop(socket.AF_INET6, response[offset:offset+16])
    except:
        pass
    return ""




def extract_all_answer_ips(response: bytes) -> list[str]:
    """DNS yanitindan TUM A/AAAA IP adreslerini cikar (trafik izleme için)."""
    ips = []
    if not response or len(response) < 12:
        return ips
    try:
        ancount = struct.unpack("!H", response[6:8])[0]
        if ancount == 0:
            return ips
        # Question section'i atla
        offset = 12
        while offset < len(response) and response[offset] != 0:
            if response[offset] >= 192:
                offset += 2
                break
            offset += response[offset] + 1
        else:
            offset += 1
        offset += 4  # QTYPE + QCLASS

        # Tum answer kayitlarini oku
        for _ in range(ancount):
            if offset >= len(response):
                break
            # Name (pointer veya label)
            if response[offset] >= 192:
                offset += 2
            else:
                while offset < len(response) and response[offset] != 0:
                    offset += response[offset] + 1
                offset += 1

            if offset + 10 > len(response):
                break

            atype = struct.unpack("!H", response[offset:offset+2])[0]
            offset += 8  # type + class + ttl
            rdlen = struct.unpack("!H", response[offset:offset+2])[0]
            offset += 2

            if atype == 1 and rdlen == 4 and offset + 4 <= len(response):
                ip = ".".join(str(b) for b in response[offset:offset+4])
                ips.append(ip)
            elif atype == 28 and rdlen == 16 and offset + 16 <= len(response):
                ip = socket.inet_ntop(socket.AF_INET6, response[offset:offset+16])
                ips.append(ip)
            offset += rdlen
    except Exception:
        pass
    return ips


async def cache_dns_ip_mapping(redis_client, domain: str, response: bytes):
    """DNS yanit IP'lerini Redis'e kaydet (trafik izleme için IP->domain eslesmesi)."""
    if not domain or not response:
        return
    try:
        ips = extract_all_answer_ips(response)
        for ip in ips:
            # Sinkhole ve yerel IP'leri atlat
            if ip in ("0.0.0.0", "::", "127.0.0.1") or ip.startswith("192.168.") or ip.startswith("10."):
                continue
            await redis_client.setex(
                f"dns:ip_to_domain:{ip}",
                3600,  # 1 saat TTL
                domain,
            )
    except Exception:
        pass

class DnsProxyProtocol(asyncio.DatagramProtocol):
    """UDP DNS proxy protokolu."""

    def __init__(self, redis_client: aioredis.Redis, stats: dict, query_log: deque):
        self.redis = redis_client
        self.stats = stats
        self.query_log = query_log
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.ensure_future(self.handle_query(data, addr))

    async def handle_query(self, data: bytes, addr: tuple):
        """DNS sorgusunu isle."""
        query = parse_dns_query(data)
        if not query:
            return

        domain = query["domain"]
        qtype = query["qtype"]
        qtype_name = query["qtype_name"]
        client_ip = addr[0]
        start_time = time.monotonic()

        await _refresh_dns_security_cache(self.redis)

        # Tehdit listesindeki IP'leri hizlica at (hem dis hem yerel)
        if await is_ip_blocked(client_ip):
            self.stats.setdefault("threat_blocked", 0)
            self.stats["threat_blocked"] += 1
            return

        # Dış IP kontrolü - yerel ag disindaki sorgulari reddet
        # ama guvenilir IP'leri yerel gibi isle (sorguyu ilet)
        if not is_local_ip(client_ip):
            if not is_trusted_ip(client_ip):
                asyncio.ensure_future(
                    report_external_query(client_ip, domain, qtype_name)
                )
                return  # Dış IP, sorguyu yanitsiz birak
            # Guvenilir dis IP: yerel gibi isle, sorguyu upstream'e ilet
            logger.debug(f"Guvenilir dis IP sorgusu kabul edildi: {client_ip} -> {domain}")

        self.stats["total_queries"] += 1

        blocked = False
        block_reason = None

        # 0) Cihaz tamamen engelli mi? (is_blocked=True → MAC nftables DROP)
        # Engelli cihaz Pi'ye (input chain) ulasabilir, forward DROP.
        # Tüm DNS sorgularina sinkhole dondurerek block page gosteririz.
        try:
            _dev_id = await self.redis.get(f"dns:ip_to_device:{client_ip}")
            if _dev_id and await self.redis.sismember("dns:blocked_device_ids", _dev_id):
                blocked = True
                block_reason = "device_blocked"
        except Exception:
            pass

        if not blocked:
            try:
                # 1) Sorgu tipi bazli engelleme (HINFO, WKS, NULL, AXFR, ANY)
                if qtype in _cached_blocked_qtypes:
                    blocked = True
                    block_reason = "query_type_block"
                    qtype_label = DNS_TYPES.get(qtype, f"TYPE{qtype}")
                    logger.info(f"Sorgu tipi engellendi: {client_ip} -> {domain} ({qtype_label})")
                else:
                    # 2) Cihaz özel kural kontrolü (en yuksek öncelik)
                    custom_result = await check_device_custom_rule(self.redis, client_ip, domain)
                    if custom_result == "allow":
                        pass  # Açık izin — sonraki kontrolleri atla
                    elif custom_result == "block":
                        blocked = True
                        block_reason = "device_custom_rule"
                    else:
                        # 3) Servis engelleme (BAGIMSIZ, her zaman kontrol edilir)
                        if await is_service_domain(self.redis, domain):
                            service_id = await check_device_service_block(
                                self.redis, client_ip, domain
                            )
                            if service_id:
                                blocked = True
                                block_reason = f"service:{service_id}"

                        # 4) Profil bazli VEYA global blocklist kontrolü
                        if not blocked:
                            _dev_id_for_profile = await self.redis.get(
                                f"dns:ip_to_device:{client_ip}"
                            )
                            _profile_id = None
                            if _dev_id_for_profile:
                                _profile_id = await self.redis.get(
                                    f"dns:device_profile:{_dev_id_for_profile}"
                                )

                            if _profile_id:
                                # Profil varsa: sadece profil domain setini kontrol et
                                if await is_profile_domain_blocked(
                                    self.redis, _profile_id, domain
                                ):
                                    blocked = True
                                    block_reason = f"profile:{_profile_id}"
                            else:
                                # Profil yoksa: global blocklist (mevcut davranis)
                                blocked = await is_domain_blocked(self.redis, domain)
                                block_reason = "blocklist" if blocked else None

                        # 5) Domain reputation aktif engelleme (skor >= 80)
                        if not blocked:
                            try:
                                from app.services.domain_reputation import get_cached_reputation
                                rep = await get_cached_reputation(self.redis, domain)
                                if rep and rep.get("score", 0) >= 80:
                                    blocked = True
                                    block_reason = "reputation_block"
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"DNS engelleme kontrol hatasi: {e}")

        answer_ip = ""
        elapsed_ms = 0

        if blocked:
            response = build_blocked_response(data, qtype)
            self.stats["blocked_queries"] += 1
            elapsed_ms = (time.monotonic() - start_time) * 1000
            answer_ip = _cached_sinkhole_v4 if qtype != 28 else _cached_sinkhole_v6
            logger.info(f"BLOCKED {domain} ({qtype_name}) from {client_ip} [{elapsed_ms:.1f}ms] reason={block_reason}")
            # Block sebebini Redis'e kaydet (block page icin)
            try:
                await self.redis.setex(
                    f"dns:block_info:{domain}", 600,
                    block_reason or "blocklist",
                )
            except Exception:
                pass
        else:
            # Yerel DNS override kontrolü (DoT/Private DNS için)
            override_ip = LOCAL_DNS_OVERRIDES.get(domain) if _is_local_client(client_ip) else None
            if override_ip:
                response = build_override_response(data, qtype, override_ip)
                elapsed_ms = (time.monotonic() - start_time) * 1000
                answer_ip = override_ip
                logger.debug(f"DNS Override: {domain} -> {override_ip} (local client: {client_ip})")
            else:
                response = await forward_to_upstream(data)
                if response is None:
                    return
                elapsed_ms = (time.monotonic() - start_time) * 1000
                answer_ip = extract_answer_ip(response)
            # Trafik izleme: IP->domain eslesmesini Redis'e kaydet
            asyncio.ensure_future(cache_dns_ip_mapping(self.redis, domain, response))

        if self.transport and response:
            self.transport.sendto(response, addr)

        # Cihaz otomatik kesfi - DNS sorgusu yapan IP'yi kaydet
        asyncio.ensure_future(discover_device(client_ip))

        # DNS Fingerprinting - sorgu pattern'inden cihaz tipi tespit et
        asyncio.ensure_future(analyze_fingerprint(client_ip, domain, qtype_name))

        # Tehdit analizi - şüpheli qtype, DGA, yerel flood tespiti
        if qtype_name in THREAT_SUSPICIOUS_QTYPES or not blocked:
            asyncio.ensure_future(
                report_local_query(client_ip, domain, qtype_name)
            )

        # Sorguyu log kuyruğuna ekle (DB'ye toplu yazilacak)
        self.query_log.append({
            "client_ip": client_ip,
            "domain": domain,
            "query_type": qtype_name,
            "blocked": blocked,
            "block_reason": block_reason,
            "upstream_response_ms": int(elapsed_ms),
            "answer_ip": answer_ip,
            "timestamp": datetime.utcnow(),
            "destination_port": 53,       # 5651: UDP DNS port
            "wan_ip": get_wan_ip(),        # 5651: NAT dis IP
        })


async def flush_query_logs(query_log: deque, db_url: str):
    """Kuyruktaki DNS sorgularini DB'ye toplu yaz."""
    from app.db.session import async_session_factory
    from app.models.dns_query_log import DnsQueryLog

    # device_id lookup için Redis
    _flush_redis = None

    while True:
        await asyncio.sleep(5)  # 5 saniyede bir toplu yazim

        if not query_log:
            continue

        # Kuyruktaki tum sorguları al
        entries = []
        while query_log:
            try:
                entries.append(query_log.popleft())
            except IndexError:
                break

        if not entries:
            continue

        # Redis bağlantısi (lazy init)
        if _flush_redis is None:
            try:
                from app.db.redis_client import get_redis
                _flush_redis = await get_redis()
            except Exception:
                _flush_redis = None

        try:
            async with async_session_factory() as session:
                # 5651: MAC adresi toplu cozumleme (DB sorgusu azaltmak için)
                from app.models.device import Device

                for entry in entries:
                    # IP'den device_id bul (Redis cache)
                    device_id = None
                    mac_address = None
                    if _flush_redis and entry.get("client_ip"):
                        try:
                            did = await _flush_redis.get(
                                f"dns:ip_to_device:{entry['client_ip']}"
                            )
                            if did:
                                device_id = int(did)
                                # 5651: MAC adresini Redis cache'den al
                                cached_mac = await _flush_redis.get(
                                    f"dns:device_mac:{did}"
                                )
                                if cached_mac:
                                    mac_address = cached_mac
                                else:
                                    # DB'den MAC al ve Redis'e cache'le
                                    from sqlalchemy import select
                                    dev = await session.scalar(
                                        select(Device.mac_address).where(
                                            Device.id == device_id
                                        )
                                    )
                                    if dev:
                                        mac_address = dev
                                        await _flush_redis.setex(
                                            f"dns:device_mac:{did}",
                                            3600,  # 1 saat cache
                                            mac_address,
                                        )
                        except Exception:
                            pass

                    log = DnsQueryLog(
                        client_ip=entry["client_ip"],
                        domain=entry["domain"],
                        query_type=entry["query_type"],
                        blocked=entry["blocked"],
                        block_reason=entry["block_reason"],
                        upstream_response_ms=entry["upstream_response_ms"],
                        answer_ip=entry["answer_ip"],
                        device_id=device_id,
                        # 5651 Kanun Uyumu alanlari
                        mac_address=mac_address,
                        destination_port=entry.get("destination_port", 53),
                        wan_ip=entry.get("wan_ip", ""),
                    )
                    session.add(log)
                await session.commit()
        except Exception as e:
            logger.error(f"DNS log yazma hatasi: {e}")


CERT_DIR = "/opt/tonbilaios/backend/certs"

# DoT sunucusu yönetimi için global referanslar
_dot_server = None
_dot_server_task = None
_dot_redis_client = None
_dot_stats = None
_dot_query_log = None


async def reload_dot_server():
    """DoT sunucusunu yeni sertifikayla yeniden başlat."""
    global _dot_server, _dot_server_task
    cert_file = os.path.join(CERT_DIR, "fullchain.pem")
    key_file = os.path.join(CERT_DIR, "privkey.pem")

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        logger.warning("DoT reload: Sertifika dosyalari bulunamadı.")
        return False

    # Mevcut sunucuyu durdur
    if _dot_server is not None:
        try:
            _dot_server.close()
            await _dot_server.wait_closed()
            logger.info("DoT: Eski sunucu durduruldu.")
        except Exception as e:
            logger.debug(f"DoT sunucu durdurma hatasi: {e}")
        _dot_server = None

    if _dot_server_task and not _dot_server_task.done():
        _dot_server_task.cancel()
        try:
            await _dot_server_task
        except asyncio.CancelledError:
            pass

    # Yeni SSL context oluştur
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        ssl_ctx.load_cert_chain(cert_file, key_file)
    except Exception as e:
        logger.error(f"DoT reload: TLS sertifika yükleme hatasi: {e}")
        return False

    # Yeni sunucu başlat
    async def client_handler(reader, writer):
        await handle_dot_client(reader, writer, _dot_redis_client, _dot_stats, _dot_query_log)

    try:
        server = await asyncio.start_server(client_handler, "0.0.0.0", 853, ssl=ssl_ctx)
        _dot_server = server
        _dot_server_task = asyncio.create_task(_run_dot_server(server))
        logger.info("DoT: Yeni sertifikayla yeniden başlatildi (port 853).")
        return True
    except Exception as e:
        logger.error(f"DoT reload: Sunucu başlatma hatasi: {e}")
        return False


async def _run_dot_server(server):
    """DoT sunucusunu serve_forever ile calistir."""
    async with server:
        await server.serve_forever()


async def handle_dot_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    redis_client: aioredis.Redis,
    stats: dict,
    query_log: deque,
):
    """DoT (DNS over TLS) istemci bağlantısini isle. RFC 7858."""
    peer = writer.get_extra_info("peername")
    client_ip = peer[0] if peer else "unknown"

    try:
        while True:
            # DNS-over-TLS: 2 byte uzunluk + DNS mesaji
            length_data = await asyncio.wait_for(reader.readexactly(2), timeout=30)
            msg_length = struct.unpack("!H", length_data)[0]

            if msg_length < 12 or msg_length > 65535:
                break

            dns_data = await asyncio.wait_for(reader.readexactly(msg_length), timeout=10)

            query = parse_dns_query(dns_data)
            if not query:
                continue

            domain = query["domain"]
            qtype = query["qtype"]
            qtype_name = query["qtype_name"]
            start_time = time.monotonic()

            await _refresh_dns_security_cache(redis_client)

            # Tehdit listesindeki IP'leri at (DoT için de gecerli)
            if await is_ip_blocked(client_ip):
                continue

            stats["total_queries"] += 1

            blocked = False
            block_reason = None

            try:
                # Cihaz özel kural kontrolü (en yuksek öncelik)
                custom_result = await check_device_custom_rule(redis_client, client_ip, domain)
                if custom_result == "allow":
                    pass  # Açık izin
                elif custom_result == "block":
                    blocked = True
                    block_reason = "device_custom_rule"
                else:
                    # Servis engelleme (BAGIMSIZ, her zaman kontrol edilir)
                    if await is_service_domain(redis_client, domain):
                        service_id = await check_device_service_block(
                            redis_client, client_ip, domain
                        )
                        if service_id:
                            blocked = True
                            block_reason = f"service:{service_id}"

                    # Profil bazli VEYA global blocklist kontrolü
                    if not blocked:
                        _dev_id_dot = await redis_client.get(
                            f"dns:ip_to_device:{client_ip}"
                        )
                        _profile_id_dot = None
                        if _dev_id_dot:
                            _profile_id_dot = await redis_client.get(
                                f"dns:device_profile:{_dev_id_dot}"
                            )

                        if _profile_id_dot:
                            if await is_profile_domain_blocked(
                                redis_client, _profile_id_dot, domain
                            ):
                                blocked = True
                                block_reason = f"profile:{_profile_id_dot}"
                        else:
                            blocked = await is_domain_blocked(redis_client, domain)
                            block_reason = "blocklist" if blocked else None
            except Exception:
                pass

            answer_ip = ""

            if blocked:
                response = build_blocked_response(dns_data, qtype)
                stats["blocked_queries"] += 1
                elapsed_ms = (time.monotonic() - start_time) * 1000
                answer_ip = _cached_sinkhole_v4 if qtype != 28 else _cached_sinkhole_v6
                logger.info(
                    f"DoT BLOCKED {domain} ({qtype_name}) from {client_ip} [{elapsed_ms:.1f}ms] reason={block_reason}"
                )
            else:
                # Yerel DNS override kontrolü (DoT/Private DNS için)
                override_ip = LOCAL_DNS_OVERRIDES.get(domain) if _is_local_client(client_ip) else None
                if override_ip:
                    response = build_override_response(dns_data, qtype, override_ip)
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    answer_ip = override_ip
                    logger.debug(f"DoT Override: {domain} -> {override_ip} (local client: {client_ip})")
                else:
                    response = await forward_to_upstream(dns_data)
                    if response is None:
                        continue
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    answer_ip = extract_answer_ip(response)
                # Trafik izleme: IP->domain eslesmesini Redis'e kaydet
                asyncio.ensure_future(cache_dns_ip_mapping(redis_client, domain, response))

            # DoT yaniti: 2 byte uzunluk + DNS yaniti
            writer.write(struct.pack("!H", len(response)) + response)
            await writer.drain()

            # Cihaz kesfi - DoT istemcisi (public IP'ler de kabul edilir)
            asyncio.ensure_future(discover_device(client_ip, is_dot=True))

            # Tehdit analizi - DoT sorgulari için de
            if qtype_name in THREAT_SUSPICIOUS_QTYPES or not blocked:
                asyncio.ensure_future(
                    report_local_query(client_ip, domain, qtype_name)
                )

            # Log kuyruguna ekle
            query_log.append({
                "client_ip": client_ip,
                "domain": domain,
                "query_type": qtype_name,
                "blocked": blocked,
                "block_reason": block_reason,
                "upstream_response_ms": int(elapsed_ms),
                "answer_ip": answer_ip,
                "timestamp": datetime.utcnow(),
                "destination_port": 853,      # 5651: DoT port
                "wan_ip": get_wan_ip(),        # 5651: NAT dis IP
            })

    except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionResetError):
        pass
    except Exception as e:
        logger.debug(f"DoT istemci hatasi ({client_ip}): {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start_dot_server(
    redis_client: aioredis.Redis,
    stats: dict,
    query_log: deque,
    port: int = 853,
):
    """DoT (DNS over TLS) sunucusunu başlat (TCP port 853)."""
    global _dot_server, _dot_server_task, _dot_redis_client, _dot_stats, _dot_query_log

    # Global referanslari kaydet (reload için)
    _dot_redis_client = redis_client
    _dot_stats = stats
    _dot_query_log = query_log

    cert_file = os.path.join(CERT_DIR, "fullchain.pem")
    key_file = os.path.join(CERT_DIR, "privkey.pem")

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        logger.warning(
            f"DoT: Sertifika dosyalari bulunamadı ({cert_file}). "
            "DoT sunucusu başlatilmiyor. TLS ayarlarından sertifika yükleyin."
        )
        # Periyodik kontrol - sertifika yuklendikten sonra başlat
        while True:
            await asyncio.sleep(10)
            if os.path.exists(cert_file) and os.path.exists(key_file):
                logger.info("DoT: Sertifika dosyalari bulundu, sunucu başlatiliyor...")
                break

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        ssl_ctx.load_cert_chain(cert_file, key_file)
    except Exception as e:
        logger.error(f"DoT: TLS sertifika yükleme hatasi: {e}")
        return

    async def client_handler(reader, writer):
        await handle_dot_client(reader, writer, redis_client, stats, query_log)

    server = await asyncio.start_server(
        client_handler,
        "0.0.0.0",
        port,
        ssl=ssl_ctx,
    )

    _dot_server = server
    logger.info(f"DoT (DNS-over-TLS) AKTIF - 0.0.0.0:{port} (TCP+TLS)")
    async with server:
        await server.serve_forever()


async def start_dns_proxy(redis_url: str = "redis://redis:6379/0"):
    """DNS proxy sunucusunu başlat (UDP port 53 + DoT port 853)."""
    logger.info("DNS Proxy başlatiliyor (port 53 + DoT 853)...")

    redis_client = aioredis.from_url(redis_url, decode_responses=True)

    stats = {
        "total_queries": 0,
        "blocked_queries": 0,
        "start_time": datetime.utcnow().isoformat(),
    }

    # DNS sorgu log kuyrugu (DB'ye toplu yazilir)
    query_log = deque(maxlen=10000)

    try:
        await redis_client.ping()
        logger.info("DNS Proxy: Redis bağlantısi başarılı.")
    except Exception as e:
        logger.error(f"DNS Proxy: Redis bağlantısi başarısız: {e}")
        for attempt in range(10):
            await asyncio.sleep(3)
            try:
                await redis_client.ping()
                logger.info(f"DNS Proxy: Redis bağlantısi başarılı (deneme {attempt + 2}).")
                break
            except:
                continue
        else:
            logger.error("DNS Proxy: Redis'e baglanamadi, proxy başlatilmiyor.")
            return

    loop = asyncio.get_event_loop()

    # UDP DNS sunucusu (port 53)
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DnsProxyProtocol(redis_client, stats, query_log),
        local_addr=("0.0.0.0", 53),
    )

    logger.info("DNS Proxy AKTIF - 0.0.0.0:53 (UDP)")
    logger.info(f"Upstream DNS: {', '.join(f'{ip}:{port}' for ip, port in UPSTREAM_DNS)}")

    # DB log yazici task
    log_task = asyncio.create_task(flush_query_logs(query_log, redis_url))

    # DoT sunucusu (port 853) - arka planda başlat
    dot_task = asyncio.create_task(start_dot_server(redis_client, stats, query_log))

    # İstatistik loglama dongusu
    while True:
        await asyncio.sleep(60)
        total = stats["total_queries"]
        blocked = stats["blocked_queries"]
        ratio = (blocked / total * 100) if total > 0 else 0
        logger.info(f"DNS Stats: {total} sorgu, {blocked} engellendi ({ratio:.1f}%)")

        try:
            await redis_client.hset("dns:proxy_stats", mapping={
                "total_queries": total,
                "blocked_queries": blocked,
                "block_ratio": f"{ratio:.1f}",
                "uptime_since": stats["start_time"],
            })
        except:
            pass

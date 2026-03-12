# --- Lokal IP Blocklist Sync Worker ---
# Ucretsiz IP blocklist kaynaklarini periyodik olarak indirir ve Redis SET'e yazar.
# IP reputation worker, AbuseIPDB sorgusu oncesinde lokal blocklist kontrolu yapar.
#
# Kaynaklar:
#   - Firehol Level 1: ~50K kotu IP (saatlik)
#   - Spamhaus DROP/EDROP: ISP seviyesi kotu aglar (gunluk)
#   - DShield Top 20: En aktif saldirganlarin /24 bloklari (gunluk)
#   - Emerging Threats: Compromised IP listesi (gunluk)
#
# Redis yapisi:
#   blocklist:{name}_ips   → SET (tum IP'ler)
#   blocklist:{name}_nets  → SET (tum CIDR'lar)
#   blocklist:{name}_meta  → HASH (last_fetch, count, url)
#   blocklist:combined     → SET (tum kaynaklarin IP'leri birlesik)
#   blocklist:combined_nets → SET (tum CIDR'lar birlesik)

import asyncio
import ipaddress
import logging
import time

from app.db.redis_client import get_redis

logger = logging.getLogger("tonbilai.ip_blocklist_sync")

# ─── Kaynak tanimlari ───────────────────────────────────────────────────────

BLOCKLIST_SOURCES = [
    {
        "name": "firehol_level1",
        "url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
        "interval": 3600,
        "type": "netset",       # Yorum satirlari # ile baslar, IP ve CIDR karisik
    },
    {
        "name": "spamhaus_drop",
        "url": "https://www.spamhaus.org/drop/drop.txt",
        "interval": 86400,
        "type": "cidr",         # Her satir: CIDR ; yorum
    },
    {
        "name": "spamhaus_edrop",
        "url": "https://www.spamhaus.org/drop/edrop.txt",
        "interval": 86400,
        "type": "cidr",
    },
    {
        "name": "dshield_top20",
        "url": "https://feeds.dshield.org/block.txt",
        "interval": 86400,
        "type": "dshield",      # Tab-separated: start_ip\tend_ip\t...
    },
    {
        "name": "emerging_threats",
        "url": "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt",
        "interval": 86400,
        "type": "iplist",       # Her satir: IP adresi veya yorum #
    },
]

SYNC_INTERVAL = 3600         # Ana dongu: her 1 saatte kontrol
STARTUP_DELAY = 60           # Baslangic gecikmesi (diger worker'lar hazir olsun)


# ─── Parser fonksiyonlari ──────────────────────────────────────────────────

def _parse_netset(text: str) -> tuple[set[str], set[str]]:
    """Firehol netset formatini parse et: IP ve CIDR karisik."""
    ips = set()
    nets = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "/" in line:
            try:
                net = ipaddress.ip_network(line, strict=False)
                nets.add(str(net))
            except ValueError:
                continue
        else:
            try:
                ipaddress.ip_address(line)
                ips.add(line)
            except ValueError:
                continue
    return ips, nets


def _parse_cidr(text: str) -> tuple[set[str], set[str]]:
    """Spamhaus DROP/EDROP formatini parse et: CIDR ; yorum."""
    ips = set()
    nets = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        # "10.0.0.0/8 ; SBL123456" formatinda
        parts = line.split(";")[0].strip()
        if not parts:
            continue
        if "/" in parts:
            try:
                net = ipaddress.ip_network(parts, strict=False)
                nets.add(str(net))
            except ValueError:
                continue
        else:
            try:
                ipaddress.ip_address(parts)
                ips.add(parts)
            except ValueError:
                continue
    return ips, nets


def _parse_dshield(text: str) -> tuple[set[str], set[str]]:
    """DShield block.txt formatini parse et: tab-separated, start_ip /24 CIDR olustur."""
    ips = set()
    nets = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 1:
            start_ip = parts[0].strip()
            try:
                ipaddress.ip_address(start_ip)
                # /24 CIDR olustur
                net = ipaddress.ip_network(f"{start_ip}/24", strict=False)
                nets.add(str(net))
            except ValueError:
                continue
    return ips, nets


def _parse_iplist(text: str) -> tuple[set[str], set[str]]:
    """Basit IP listesi: her satirda 1 IP, # ile yorum."""
    ips = set()
    nets = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "/" in line:
            try:
                net = ipaddress.ip_network(line, strict=False)
                nets.add(str(net))
            except ValueError:
                continue
        else:
            try:
                ipaddress.ip_address(line)
                ips.add(line)
            except ValueError:
                continue
    return ips, nets


_PARSERS = {
    "netset": _parse_netset,
    "cidr": _parse_cidr,
    "dshield": _parse_dshield,
    "iplist": _parse_iplist,
}


# ─── Sync fonksiyonlari ──────────────────────────────────────────────────

async def sync_single_blocklist(source: dict) -> tuple[int, int]:
    """
    Tek bir blocklist kaynagini indir ve Redis'e yaz.
    Returns: (ip_count, net_count)
    """
    name = source["name"]
    url = source["url"]
    src_type = source["type"]
    redis = await get_redis()

    try:
        from app.services.http_pool import get_client
        client = await get_client("blocklist", timeout=30)
        response = await client.get(url)
        if response.status_code != 200:
            logger.warning(f"Blocklist {name} indirilemedi: HTTP {response.status_code}")
            return 0, 0

        text = response.text
        parser = _PARSERS.get(src_type, _parse_iplist)
        ips, nets = parser(text)

        total = len(ips) + len(nets)
        if total == 0:
            logger.warning(f"Blocklist {name}: bos liste (0 IP/CIDR)")
            return 0, 0

        # Redis pipeline ile yaz
        ip_key = f"blocklist:{name}_ips"
        net_key = f"blocklist:{name}_nets"
        meta_key = f"blocklist:{name}_meta"

        pipe = redis.pipeline()
        # Eski verileri temizle
        pipe.delete(ip_key, net_key)
        # IP'leri yaz
        if ips:
            pipe.sadd(ip_key, *ips)
            pipe.expire(ip_key, source["interval"] * 3)  # 3x interval TTL
        # CIDR'lari yaz
        if nets:
            pipe.sadd(net_key, *nets)
            pipe.expire(net_key, source["interval"] * 3)
        # Meta bilgisi
        pipe.hset(meta_key, mapping={
            "last_fetch": str(int(time.time())),
            "ip_count": str(len(ips)),
            "net_count": str(len(nets)),
            "total": str(total),
            "url": url,
        })
        pipe.expire(meta_key, source["interval"] * 3)
        await pipe.execute()

        logger.info(f"Blocklist {name}: {len(ips)} IP + {len(nets)} CIDR = {total} kayit")
        return len(ips), len(nets)

    except Exception as exc:
        logger.warning(f"Blocklist {name} sync hatasi: {exc}")
        return 0, 0


async def sync_all_blocklists() -> dict:
    """
    Tum kaynaklari donguyle senkronize et.
    Interval gecmediyse atla.
    Returns: {"total_ips": N, "total_nets": N, "sources_synced": N}
    """
    redis = await get_redis()
    total_ips = 0
    total_nets = 0
    sources_synced = 0

    for source in BLOCKLIST_SOURCES:
        name = source["name"]
        interval = source["interval"]

        # Interval kontrolu
        try:
            meta_key = f"blocklist:{name}_meta"
            last_fetch_raw = await redis.hget(meta_key, "last_fetch")
            if last_fetch_raw:
                elapsed = time.time() - int(last_fetch_raw)
                if elapsed < interval:
                    logger.debug(f"Blocklist {name}: atlanacak ({int(elapsed)}s < {interval}s)")
                    continue
        except Exception:
            pass  # Meta okunamazsa yeniden fetch et

        ip_count, net_count = await sync_single_blocklist(source)
        total_ips += ip_count
        total_nets += net_count
        if ip_count > 0 or net_count > 0:
            sources_synced += 1

        # Kaynaklar arasi kisa bekleme (rate limit korunma)
        await asyncio.sleep(2)

    # Combined SET olustur: tum kaynaklarin IP'lerini birlestir
    await _rebuild_combined_sets(redis)

    logger.info(
        f"Blocklist sync tamamlandi: {sources_synced} kaynak, "
        f"{total_ips} IP + {total_nets} CIDR"
    )
    return {"total_ips": total_ips, "total_nets": total_nets, "sources_synced": sources_synced}


async def _rebuild_combined_sets(redis) -> None:
    """Tum kaynaklarin IP ve CIDR SET'lerini birlesik SET'e yaz."""
    ip_keys = []
    net_keys = []
    for source in BLOCKLIST_SOURCES:
        name = source["name"]
        ip_key = f"blocklist:{name}_ips"
        net_key = f"blocklist:{name}_nets"
        # Key varsa listeye ekle
        if await redis.exists(ip_key):
            ip_keys.append(ip_key)
        if await redis.exists(net_key):
            net_keys.append(net_key)

    # SUNIONSTORE: tum IP'leri birlesik SET'e yaz
    if ip_keys:
        await redis.sunionstore("blocklist:combined", *ip_keys)
        await redis.expire("blocklist:combined", 86400 * 2)
    else:
        await redis.delete("blocklist:combined")

    if net_keys:
        await redis.sunionstore("blocklist:combined_nets", *net_keys)
        await redis.expire("blocklist:combined_nets", 86400 * 2)
    else:
        await redis.delete("blocklist:combined_nets")

    # Istatistik logla
    combined_count = await redis.scard("blocklist:combined")
    combined_nets = await redis.scard("blocklist:combined_nets")
    logger.info(f"Blocklist combined: {combined_count} IP + {combined_nets} CIDR")


# ─── Lookup fonksiyonlari ──────────────────────────────────────────────────

async def is_ip_in_local_blocklist(ip: str) -> tuple[bool, str]:
    """
    IP'nin lokal blocklist'te olup olmadigini kontrol et.
    Returns: (is_blocked, source_name)
    O(1) SET lookup + O(3) subnet kontrolu
    """
    redis = await get_redis()

    # 1. Tam IP eslesmesi (O(1))
    try:
        if await redis.sismember("blocklist:combined", ip):
            return True, "local_blocklist"
    except Exception:
        pass

    # 2. CIDR subnet eslesmesi: IP'nin /24, /16, /8 network adreslerini kontrol et
    try:
        addr = ipaddress.ip_address(ip)
        for prefix_len in [24, 16, 8]:
            network = ipaddress.ip_network(f"{ip}/{prefix_len}", strict=False)
            if await redis.sismember("blocklist:combined_nets", str(network)):
                return True, "local_subnet_blocklist"
    except Exception:
        pass

    return False, ""


# ─── Worker ana girisi ──────────────────────────────────────────────────

async def start_blocklist_sync() -> None:
    """
    Lokal IP blocklist sync worker'ini baslat.
    main.py lifespan'da asyncio.create_task() ile cagrilir.
    """
    logger.info(f"IP blocklist sync worker basliyor — {STARTUP_DELAY}s bekleniyor...")
    await asyncio.sleep(STARTUP_DELAY)
    logger.info("IP blocklist sync worker aktif.")

    # Ilk calistirma: tum listeleri indir
    try:
        result = await sync_all_blocklists()
        logger.info(f"IP blocklist ilk sync: {result}")
    except Exception as exc:
        logger.error(f"IP blocklist ilk sync hatasi: {exc}")

    # Periyodik dongu
    while True:
        try:
            await asyncio.sleep(SYNC_INTERVAL)
            await sync_all_blocklists()
        except asyncio.CancelledError:
            logger.info("IP blocklist sync worker durduruldu.")
            break
        except Exception as exc:
            logger.error(f"IP blocklist sync dongu hatasi: {exc}")

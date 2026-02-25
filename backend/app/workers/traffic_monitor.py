# --- Ajan: ANALIST (THE ANALYST) ---
# Gercek trafik izleme iscisi: conntrack üzerinden bağlantı takibi,
# DNS IP->domain eslesmesi ile trafik loglarını veritabanina yazar.
# Bridge (br0 = eth0 + eth1) üzerinden gecen tum internet trafiğini izler.
# br_netfilter modulu ile conntrack kopru trafiğini görebilir.

import asyncio
import logging
import re
import time
from collections import defaultdict

from app.db.session import async_session_factory
from app.db.redis_client import get_redis
from app.models.traffic_log import TrafficLog
from app.services.timezone_service import now_local

logger = logging.getLogger("tonbilai.traffic_monitor")

# Conntrack ciktisi ayristirma deseni
# Ornek satirlar:
# ipv4  2 tcp  6 431998 ESTABLISHED src=192.168.1.40 dst=142.251.36.110 sport=34036 dport=443
#   src=142.251.36.110 dst=192.168.1.40 sport=443 dport=34036 [ASSURED] mark=0 use=1
# Byte sayacli:
# ipv4  2 tcp  6 50 SYN_RECV src=192.168.1.40 dst=1.2.3.4 sport=12345 dport=443
#   packets=10 bytes=1500 src=1.2.3.4 dst=192.168.1.40 sport=443 dport=12345
#   packets=8 bytes=12000 [ASSURED] mark=0 use=1
_CONNTRACK_FIELD_RE = re.compile(
    r'(src|dst|sport|dport|packets|bytes)=([^\s]+)'
)
_PROTO_RE = re.compile(r'^ipv[46]\s+\d+\s+(\w+)\s+')

# LAN IP on eki
LAN_PREFIX = '192.168.1.'

# Router'in kendi IP'si (kopru arayuzu)
ROUTER_IP = '192.168.1.2'

# Izleme dongusu aralığı (saniye)
MONITOR_INTERVAL = 60

# Onceki okumadaki bağlantı byte degerlerini saklar (delta hesaplama)
# Anahtar: (proto, src_ip, src_port, dst_ip, dst_port)
# Deger: (bytes_original_dir, bytes_reply_dir)
_previous_bytes: dict[tuple, tuple[int, int]] = {}

# Bağlantı son görülme zamani (eski kayitlari temizlemek için)
_last_seen: dict[tuple, float] = {}

# Temizleme esigi (saniye) - bu suredir görülmeyen bağlantılari sil
_STALE_TIMEOUT = 300


def _parse_conntrack_line(line: str) -> dict | None:
    """Tek bir conntrack satirini ayristir.

    Conntrack satiri iki yon icerir:
    - Original yonu (1. src/dst/sport/dport + packets/bytes)
    - Reply yonu (2. src/dst/sport/dport + packets/bytes)

    Returns:
        dict with keys: proto, src, dst, sport, dport,
                        bytes_orig, bytes_reply
        or None if line cannot be parsed.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    # Protokol cikart
    proto_match = _PROTO_RE.match(line)
    if not proto_match:
        return None
    proto = proto_match.group(1).upper()  # tcp, udp, icmp -> TCP, UDP, ICMP

    # ICMP'de sport/dport yok, atla
    if proto == 'ICMP':
        return None

    # Tum field=value ciftlerini bul
    matches = _CONNTRACK_FIELD_RE.findall(line)
    if len(matches) < 4:
        return None

    # Conntrack satirinda iki set src/dst/sport/dport var:
    # 1. orijinal yon (istemci -> sunucu)
    # 2. yanit yonu (sunucu -> istemci)
    # Byte/packet sayaclari da her yon için ayri olabilir.

    fields_by_occurrence: list[dict] = []
    current = {}
    seen_keys_in_current = set()

    for key, val in matches:
        if key in seen_keys_in_current:
            # Ayni key tekrar goruldu = yeni yon basladi
            fields_by_occurrence.append(current)
            current = {}
            seen_keys_in_current = set()
        current[key] = val
        seen_keys_in_current.add(key)

    if current:
        fields_by_occurrence.append(current)

    if len(fields_by_occurrence) < 2:
        return None

    orig = fields_by_occurrence[0]
    reply = fields_by_occurrence[1]

    try:
        result = {
            'proto': proto,
            'src': orig.get('src', ''),
            'dst': orig.get('dst', ''),
            'sport': int(orig.get('sport', 0)),
            'dport': int(orig.get('dport', 0)),
            'bytes_orig': int(orig.get('bytes', 0)),
            'bytes_reply': int(reply.get('bytes', 0)),
        }
    except (ValueError, TypeError):
        return None

    return result


def _is_lan_ip(ip: str) -> bool:
    """IP adresi yerel ag içinde mi?"""
    return ip.startswith(LAN_PREFIX)


def _is_router_ip(ip: str) -> bool:
    """IP adresi router'in kendi IP'si mi?"""
    return ip == ROUTER_IP


def _cleanup_stale_entries(now: float):
    """Uzun suredir görülmeyen bağlantılari bellekten temizle."""
    stale_keys = [
        k for k, t in _last_seen.items()
        if (now - t) > _STALE_TIMEOUT
    ]
    for k in stale_keys:
        _previous_bytes.pop(k, None)
        _last_seen.pop(k, None)
    if stale_keys:
        logger.debug(f"Temizlendi: {len(stale_keys)} eski bağlantı kaydi silindi.")


async def _run_conntrack() -> str:
    """conntrack komutunu calistir ve ciktisini dondur."""
    try:
        proc = await asyncio.create_subprocess_exec(
            'sudo', '/usr/sbin/conntrack', '-L', '-o', 'extended',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode('utf-8', errors='replace')
    except asyncio.TimeoutError:
        logger.error("conntrack komutu zaman asimina ugradi.")
        return ''
    except Exception as e:
        logger.error(f"conntrack calistirma hatasi: {e}")
        return ''


async def _process_conntrack_output(output: str, redis_client) -> list[dict]:
    """conntrack ciktisini isle, delta hesapla, trafik kayitlarini dondur.

    Returns:
        List of dicts: {device_id, destination_domain, protocol,
                        bytes_sent, bytes_received}
    """
    now = time.monotonic()

    # Aggregated traffic: (device_id, domain, proto) -> {sent, received}
    aggregated: dict[tuple, dict] = defaultdict(
        lambda: {'bytes_sent': 0, 'bytes_received': 0}
    )

    lines = output.strip().split('\n')

    # Tum bağlantılari parse et
    parsed_entries = []
    for line in lines:
        entry = _parse_conntrack_line(line)
        if not entry:
            continue

        src_ip = entry['src']
        dst_ip = entry['dst']

        # Sadece LAN cihazlarindan disa giden trafik
        # (src LAN IP, dst dis IP)
        if _is_lan_ip(src_ip) and not _is_lan_ip(dst_ip):
            if _is_router_ip(src_ip):
                continue  # Router'in kendi trafiğini atla
            parsed_entries.append(entry)

    # Tekrarlanan bağlantılari onle
    seen_connections: set[tuple] = set()
    unique_entries = []
    for entry in parsed_entries:
        conn_key = (entry['proto'], entry['src'], entry['sport'],
                    entry['dst'], entry['dport'])
        if conn_key not in seen_connections:
            seen_connections.add(conn_key)
            unique_entries.append(entry)

    if not unique_entries:
        _cleanup_stale_entries(now)
        return []

    # Toplu Redis sorgulari: device_id ve domain arama
    dst_ips = list({e['dst'] for e in unique_entries})
    src_ips = list({e['src'] for e in unique_entries})

    # Redis pipeline ile toplu sorgula
    pipe = redis_client.pipeline(transaction=False)
    for ip in src_ips:
        pipe.get(f'dns:ip_to_device:{ip}')
    for ip in dst_ips:
        pipe.get(f'dns:ip_to_domain:{ip}')

    try:
        results = await pipe.execute()
    except Exception as e:
        logger.error(f"Redis pipeline hatasi: {e}")
        return []

    # Sonuçlari haritalara ayir
    device_id_map: dict[str, int | None] = {}
    for i, ip in enumerate(src_ips):
        val = results[i]
        device_id_map[ip] = int(val) if val else None

    domain_map: dict[str, str] = {}
    offset = len(src_ips)
    for i, ip in enumerate(dst_ips):
        val = results[offset + i]
        domain_map[ip] = val if val else ip  # Domain bulunamazsa ham IP kullan

    # Her bağlantıyi isle - delta hesapla
    for entry in unique_entries:
        src_ip = entry['src']
        dst_ip = entry['dst']
        proto = entry['proto']
        bytes_orig = entry['bytes_orig']
        bytes_reply = entry['bytes_reply']

        # Byte sayacı yoksa (eski bağlantı, accounting oncesi) atla
        if bytes_orig == 0 and bytes_reply == 0:
            continue

        device_id = device_id_map.get(src_ip)
        if device_id is None:
            continue  # Tanimsiz cihaz - atla

        conn_key = (proto, src_ip, entry['sport'], dst_ip, entry['dport'])
        _last_seen[conn_key] = now

        # Delta hesapla
        prev = _previous_bytes.get(conn_key, (0, 0))
        delta_sent = max(0, bytes_orig - prev[0])
        delta_received = max(0, bytes_reply - prev[1])

        # Onceki degerleri güncelle
        _previous_bytes[conn_key] = (bytes_orig, bytes_reply)

        # Delta 0 ise atla (değişiklik yok)
        if delta_sent == 0 and delta_received == 0:
            continue

        domain = domain_map.get(dst_ip, dst_ip)

        # Aggregate: (device_id, domain, proto) bazinda topla
        agg_key = (device_id, domain, proto)
        aggregated[agg_key]['bytes_sent'] += delta_sent
        aggregated[agg_key]['bytes_received'] += delta_received

    # Eski kayitlari temizle
    _cleanup_stale_entries(now)

    # Sonuçlari listeye cevir
    records = []
    for (device_id, domain, proto), traffic in aggregated.items():
        if traffic['bytes_sent'] > 0 or traffic['bytes_received'] > 0:
            records.append({
                'device_id': device_id,
                'destination_domain': domain[:255],  # VARCHAR(255) siniri
                'protocol': proto,
                'bytes_sent': traffic['bytes_sent'],
                'bytes_received': traffic['bytes_received'],
            })

    return records


async def _write_traffic_logs(records: list[dict]):
    """Trafik kayitlarini veritabanina toplu yaz."""
    if not records:
        return

    try:
        async with async_session_factory() as session:
            now = now_local()
            for record in records:
                log = TrafficLog(
                    timestamp=now,
                    device_id=record['device_id'],
                    destination_domain=record['destination_domain'],
                    category=record.get('category'),
                    bytes_sent=record['bytes_sent'],
                    bytes_received=record['bytes_received'],
                    protocol=record['protocol'],
                )
                session.add(log)
            await session.commit()
            logger.debug(f"Veritabanina {len(records)} trafik kaydi yazildi.")
    except Exception as e:
        logger.error(f"Trafik log yazma hatasi: {e}")


# Bilinen domain -> kategori eslesmesi
_KNOWN_CATEGORIES = {
    'youtube.com': 'streaming', 'netflix.com': 'streaming',
    'twitch.tv': 'streaming', 'disneyplus.com': 'streaming',
    'spotify.com': 'streaming', 'primevideo.com': 'streaming',
    'hulu.com': 'streaming', 'crunchyroll.com': 'streaming',
    'instagram.com': 'social', 'tiktok.com': 'social',
    'twitter.com': 'social', 'x.com': 'social',
    'facebook.com': 'social', 'whatsapp.com': 'social',
    'whatsapp.net': 'social', 'snapchat.com': 'social',
    'reddit.com': 'social', 'linkedin.com': 'social',
    'pinterest.com': 'social', 'tumblr.com': 'social',
    'google.com': 'search', 'bing.com': 'search',
    'duckduckgo.com': 'search', 'yandex.com': 'search',
    'github.com': 'development', 'stackoverflow.com': 'development',
    'gitlab.com': 'development', 'npmjs.com': 'development',
    'pypi.org': 'development',
    'zoom.us': 'communication', 'teams.microsoft.com': 'communication',
    'discord.com': 'communication', 'discord.gg': 'communication',
    'slack.com': 'communication', 'telegram.org': 'communication',
    'web.telegram.org': 'communication',
    'amazon.com': 'shopping', 'ebay.com': 'shopping',
    'aliexpress.com': 'shopping', 'trendyol.com': 'shopping',
    'hepsiburada.com': 'shopping',
    'wikipedia.org': 'education', 'khanacademy.org': 'education',
    'udemy.com': 'education', 'coursera.org': 'education',
    'apple.com': 'technology', 'microsoft.com': 'technology',
    'icloud.com': 'technology', 'googleapis.com': 'technology',
    'gstatic.com': 'technology', 'cloudflare.com': 'technology',
    'akamai.net': 'technology', 'fbcdn.net': 'social',
    'googlevideo.com': 'streaming', 'ytimg.com': 'streaming',
    'sndcdn.com': 'streaming',
}


def _categorize_domain(domain: str) -> str | None:
    """Domain'in kategorisini belirle (varsa)."""
    domain_lower = domain.lower().rstrip('.')
    # Tam eslesme
    if domain_lower in _KNOWN_CATEGORIES:
        return _KNOWN_CATEGORIES[domain_lower]
    # Alt domain eslesmesi
    for known, cat in _KNOWN_CATEGORIES.items():
        if domain_lower.endswith('.' + known):
            return cat
    return None


async def start_traffic_monitor():
    """Ana trafik izleme dongusu - conntrack tabanli gercek trafik olcumu."""
    logger.info("Trafik izleme iscisi başlatiliyor (conntrack tabanli)...")

    # Başlangicta biraz bekle - diger servislerin hazir olmasini sagla
    await asyncio.sleep(10)

    redis_client = None
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        logger.info("Trafik izleme: Redis bağlantısi başarılı.")
    except Exception as e:
        logger.error(f"Trafik izleme: Redis bağlantısi başarısız: {e}")
        # Yeniden dene
        for attempt in range(5):
            await asyncio.sleep(5)
            try:
                redis_client = await get_redis()
                await redis_client.ping()
                logger.info(
                    f"Trafik izleme: Redis bağlantısi başarılı "
                    f"(deneme {attempt + 2})."
                )
                break
            except Exception:
                continue
        else:
            logger.error(
                "Trafik izleme: Redis'e baglanamadi, isci durduruluyor."
            )
            return

    # conntrack erişim testi
    test_output = await _run_conntrack()
    if not test_output:
        logger.error(
            "Trafik izleme: conntrack komutuna erisilemedi. "
            "sudoers yapılandirmasini kontrol edin."
        )
        return

    conn_count = len(test_output.strip().splitlines())
    logger.info(
        f"Trafik izleme iscisi AKTIF - {MONITOR_INTERVAL}s aralıkla "
        f"conntrack okuma. Ilk okumada {conn_count} bağlantı bulundu."
    )

    # Ilk okumada sadece baseline al (delta = 0 olacak)
    await _process_conntrack_output(test_output, redis_client)
    logger.info("Trafik izleme: Baseline byte degerleri alindi.")

    while True:
        try:
            # conntrack ciktisini oku
            output = await _run_conntrack()
            if not output:
                await asyncio.sleep(MONITOR_INTERVAL)
                continue

            # Bağlantılar isle ve delta hesapla
            records = await _process_conntrack_output(output, redis_client)

            if records:
                # Kategorileri belirle
                for record in records:
                    cat = _categorize_domain(record['destination_domain'])
                    if cat:
                        record['category'] = cat

                # Veritabanina yaz
                await _write_traffic_logs(records)

                total_sent = sum(r['bytes_sent'] for r in records)
                total_recv = sum(r['bytes_received'] for r in records)
                logger.info(
                    f"Trafik: {len(records)} kayit yazildi, "
                    f"gönderilen: {total_sent:,} B, "
                    f"alinan: {total_recv:,} B"
                )

        except asyncio.CancelledError:
            logger.info("Trafik izleme iscisi durduruluyor.")
            raise
        except Exception as e:
            logger.error(
                f"Trafik izleme dongusu hatasi: {e}", exc_info=True
            )

        await asyncio.sleep(MONITOR_INTERVAL)

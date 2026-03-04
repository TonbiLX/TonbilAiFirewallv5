# --- Ajan: ANALIST (THE ANALYST) ---
# Per-flow baglanti takip iscisi: conntrack uzerinden her bir TCP/UDP akisini izler,
# Redis'e canli veri yazar, MariaDB'ye periyodik olarak kaydeder.
#
# Mevcut traffic_monitor.py domain bazli agregle ederken, bu worker
# her bir flow'u ayri ayri takip eder (src:port -> dst:port).

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta

from app.db.session import async_session_factory
from app.db.redis_client import get_redis
from app.models.connection_flow import ConnectionFlow
from app.services.timezone_service import now_local

from sqlalchemy import select, and_, update, text

logger = logging.getLogger("tonbilai.flow_tracker")

# ─── Yapilandirma ───────────────────────────────────────────────
FLOW_TRACK_INTERVAL = 20       # saniye - conntrack okuma araligi
FLOW_DB_SYNC_INTERVAL = 60     # saniye - DB'ye yazma araligi
FLOW_RETENTION_DAYS = 7        # gun - eski flow temizleme
LARGE_TRANSFER_THRESHOLD = 1_000_000  # 1 MB

# ─── Sabitler ────────────────────────────────────────────────────
LAN_PREFIX = "192.168.1."
ROUTER_IP = "192.168.1.2"

# Conntrack parse
_CONNTRACK_FIELD_RE = re.compile(r"(src|dst|sport|dport|packets|bytes)=([^\s]+)")
_PROTO_RE = re.compile(r"^ipv[46]\s+\d+\s+(\w+)\s+")
_STATE_RE = re.compile(r"\b(ESTABLISHED|TIME_WAIT|CLOSE_WAIT|SYN_SENT|SYN_RECV|FIN_WAIT|CLOSE|LAST_ACK|LISTEN)\b")

# ─── Bellek state ────────────────────────────────────────────────
# flow_id -> {bytes_sent, bytes_received, packets_sent, packets_received, ts}
_prev_counters: dict[str, dict] = {}
# flow_id -> son gorulen zaman (monotonic)
_last_seen: dict[str, float] = {}
# Stale flow esigi
_STALE_TIMEOUT = 120  # 2 dakika gorunmezse bitmis say

# Bilinen domain -> kategori (traffic_monitor.py ile ayni)
_KNOWN_CATEGORIES = {
    "youtube.com": "streaming", "netflix.com": "streaming",
    "twitch.tv": "streaming", "disneyplus.com": "streaming",
    "spotify.com": "streaming", "primevideo.com": "streaming",
    "googlevideo.com": "streaming", "ytimg.com": "streaming",
    "instagram.com": "social", "tiktok.com": "social",
    "twitter.com": "social", "x.com": "social",
    "facebook.com": "social", "whatsapp.com": "social",
    "whatsapp.net": "social", "reddit.com": "social",
    "fbcdn.net": "social",
    "google.com": "search", "bing.com": "search",
    "github.com": "development", "stackoverflow.com": "development",
    "zoom.us": "communication", "discord.com": "communication",
    "telegram.org": "communication", "slack.com": "communication",
    "amazon.com": "shopping", "trendyol.com": "shopping",
    "hepsiburada.com": "shopping",
    "wikipedia.org": "education",
    "apple.com": "technology", "microsoft.com": "technology",
    "icloud.com": "technology", "googleapis.com": "technology",
    "cloudflare.com": "technology", "akamai.net": "technology",
}

# ─── Port → Servis/Uygulama Tespiti ──────────────────────────

# (service_name, app_name) — service_name: protokol seviyesi, app_name: uygulama seviyesi
_PORT_SERVICE_MAP: dict[int, tuple[str, str | None]] = {
    # Web
    80: ("HTTP", None), 443: ("HTTPS", None),
    8080: ("HTTP-Proxy", None), 8443: ("HTTPS-Alt", None),
    # E-posta
    25: ("SMTP", None), 465: ("SMTPS", None), 587: ("SMTP-Submit", None),
    110: ("POP3", None), 995: ("POP3S", None),
    143: ("IMAP", None), 993: ("IMAPS", None),
    # Dosya transferi / uzak erisim
    21: ("FTP", None), 22: ("SSH", None), 23: ("Telnet", None),
    69: ("TFTP", None), 873: ("Rsync", None),
    # DNS & NTP
    53: ("DNS", None), 853: ("DNS-over-TLS", None), 123: ("NTP", None),
    # VPN
    500: ("IKE/IPSec", "VPN"), 1194: ("OpenVPN", "VPN"),
    4500: ("IPSec-NAT", "VPN"), 51820: ("WireGuard", "VPN"),
    # Veritabani
    3306: ("MySQL", None), 5432: ("PostgreSQL", None),
    6379: ("Redis", None), 27017: ("MongoDB", None),
    # Mesajlasma / Push
    5222: ("XMPP", None), 5223: ("APNs", "Apple Push"),
    5228: ("GCM/FCM", "Google Push"), 5229: ("GCM/FCM", "Google Push"),
    5230: ("GCM/FCM", "Google Push"),
    5242: ("Viber", "Viber"), 4244: ("Viber", "Viber"),
    # IoT
    1883: ("MQTT", "IoT-MQTT"), 8883: ("MQTTS", "IoT-MQTT"),
    5683: ("CoAP", "IoT-CoAP"), 5684: ("CoAP-DTLS", "IoT-CoAP"),
    # STUN/TURN & WebRTC
    3478: ("STUN/TURN", None), 3479: ("STUN/TURN", None),
    19302: ("STUN/TURN", "Google Meet"),
    # Uzak masaustu
    3389: ("RDP", "Remote Desktop"), 5900: ("VNC", "Remote Desktop"),
    # Proxy / Diger
    1080: ("SOCKS", "Proxy"), 8888: ("HTTP-Alt", None),
    9090: ("HTTP-Alt", None),
    # Medya sunucu
    32400: ("Plex", "Plex Media Server"),
    8096: ("Jellyfin", "Jellyfin"), 8920: ("Jellyfin-HTTPS", "Jellyfin"),
    445: ("SMB", "File Sharing"), 139: ("NetBIOS", "File Sharing"),
    548: ("AFP", "File Sharing"), 631: ("IPP", "Printing"),
    9100: ("RAW-Print", "Printing"),
}

# Domain → Uygulama adi (port 443/80 icin detay tespiti)
_DOMAIN_APP_MAP: dict[str, str] = {
    # Nextcloud
    "nextcloud": "Nextcloud", "cloud.tonbil.com": "Nextcloud",
    # Google
    "google.com": "Google", "googleapis.com": "Google API",
    "youtube.com": "YouTube", "googlevideo.com": "YouTube",
    "ytimg.com": "YouTube", "gmail.com": "Gmail",
    "drive.google.com": "Google Drive", "meet.google.com": "Google Meet",
    "gstatic.com": "Google", "googleusercontent.com": "Google",
    # Apple
    "apple.com": "Apple", "icloud.com": "iCloud",
    "itunes.apple.com": "iTunes", "apps.apple.com": "App Store",
    "mzstatic.com": "Apple CDN",
    "akadns.net": "Apple CDN",
    # Microsoft
    "microsoft.com": "Microsoft", "office.com": "Office 365",
    "live.com": "Microsoft Live", "outlook.com": "Outlook",
    "teams.microsoft.com": "Teams", "onedrive.live.com": "OneDrive",
    "windows.com": "Windows Update", "windowsupdate.com": "Windows Update",
    "msftconnecttest.com": "Microsoft",
    # Sosyal medya
    "whatsapp.net": "WhatsApp", "whatsapp.com": "WhatsApp",
    "instagram.com": "Instagram", "facebook.com": "Facebook",
    "fbcdn.net": "Facebook CDN", "fb.com": "Facebook",
    "twitter.com": "Twitter", "x.com": "X (Twitter)",
    "tiktok.com": "TikTok", "tiktokcdn.com": "TikTok",
    "reddit.com": "Reddit", "telegram.org": "Telegram",
    "t.me": "Telegram",
    "discord.com": "Discord", "discord.gg": "Discord",
    "discordapp.com": "Discord",
    # Streaming
    "netflix.com": "Netflix", "nflxvideo.net": "Netflix",
    "spotify.com": "Spotify", "scdn.co": "Spotify",
    "twitch.tv": "Twitch", "ttvnw.net": "Twitch",
    "disneyplus.com": "Disney+", "primevideo.com": "Prime Video",
    # Gelistirici
    "github.com": "GitHub", "githubusercontent.com": "GitHub",
    "gitlab.com": "GitLab",
    "stackoverflow.com": "StackOverflow",
    "npmjs.org": "npm", "npmjs.com": "npm",
    "docker.io": "Docker", "docker.com": "Docker",
    # Alisveris
    "amazon.com": "Amazon", "trendyol.com": "Trendyol",
    "hepsiburada.com": "Hepsiburada",
    # CDN / Altyapi
    "cloudflare.com": "Cloudflare", "cloudflare-dns.com": "Cloudflare DNS",
    "akamai.net": "Akamai CDN", "akamaiedge.net": "Akamai CDN",
    "amazonaws.com": "AWS", "azure.com": "Azure",
    "fastly.net": "Fastly CDN",
    # Samsung
    "samsung.com": "Samsung", "samsungcloud.com": "Samsung Cloud",
    "samsungelectronics.com": "Samsung",
    "samsungosp.com": "Samsung", "samsungmdec.com": "Samsung",
    # AI
    "openai.com": "ChatGPT", "anthropic.com": "Claude",
    # Zoom
    "zoom.us": "Zoom", "zoom.com": "Zoom",
    # Oyun
    "steampowered.com": "Steam", "steamcommunity.com": "Steam",
    "epicgames.com": "Epic Games", "riotgames.com": "Riot Games",
    # Meta / VR
    "oculus.com": "Meta Quest", "meta.com": "Meta",
    # Adobe
    "adobe.io": "Adobe", "adobe.com": "Adobe",
    "typekit.com": "Adobe Fonts",
    # NTP
    "ntp.org": "NTP",
    # Hava durumu
    "windy.com": "Windy",
}


def _identify_service(dst_port: int | None, protocol: str,
                      dst_domain: str | None) -> tuple[str | None, str | None]:
    """Port ve domain'e gore servis/uygulama tespiti yap.

    Returns:
        (service_name, app_name) — service_name: protokol/servis adi,
        app_name: uygulama adi (varsa)
    """
    service_name = None
    app_name = None

    # Katman 1: Port bazli
    if dst_port and dst_port in _PORT_SERVICE_MAP:
        service_name, app_name = _PORT_SERVICE_MAP[dst_port]

    # Katman 2: Domain bazli (port 443/80 icin detay veya diger portlarda app tespiti)
    if dst_domain:
        d = dst_domain.lower().rstrip(".")
        # Tam eslesmeler
        if d in _DOMAIN_APP_MAP:
            app_name = _DOMAIN_APP_MAP[d]
        else:
            # Subdomain eslesme: edge.icloud.com → icloud.com
            for known_domain, known_app in _DOMAIN_APP_MAP.items():
                if d.endswith("." + known_domain):
                    app_name = known_app
                    break
            # "nextcloud" kelime icerme kontrolu
            if not app_name and "nextcloud" in d:
                app_name = "Nextcloud"

    # Katman 3: Port + domain ozel kurallar
    if dst_port in (5222, 5223) and dst_domain and "whatsapp" in dst_domain.lower():
        app_name = "WhatsApp"

    # Servis adi yoksa ve port yuksekse
    if not service_name and dst_port:
        if dst_port > 1024:
            service_name = f"TCP/{dst_port}" if protocol == "TCP" else f"UDP/{dst_port}"

    return service_name, app_name


def _compute_flow_id(src_ip: str, src_port: int, dst_ip: str,
                     dst_port: int, proto: str) -> str:
    """5-tuple'dan deterministik flow kimligi olustur."""
    raw = f"{src_ip}:{src_port}:{dst_ip}:{dst_port}:{proto}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _categorize_domain(domain: str) -> str | None:
    """Domain icin kategori bul."""
    if not domain:
        return None
    d = domain.lower().rstrip(".")
    if d in _KNOWN_CATEGORIES:
        return _KNOWN_CATEGORIES[d]
    for known, cat in _KNOWN_CATEGORIES.items():
        if d.endswith("." + known):
            return cat
    return None


def _parse_conntrack_line(line: str) -> dict | None:
    """Tek bir conntrack satirini parse et."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    proto_m = _PROTO_RE.match(line)
    if not proto_m:
        return None
    proto = proto_m.group(1).upper()
    if proto not in ("TCP", "UDP"):
        return None

    # State bul
    state_m = _STATE_RE.search(line)
    state = state_m.group(1) if state_m else None

    # Field=value ciftleri
    matches = _CONNTRACK_FIELD_RE.findall(line)
    if len(matches) < 4:
        return None

    # Iki yon ayir (orijinal + yanit)
    directions: list[dict] = []
    current: dict = {}
    seen_keys: set = set()

    for key, val in matches:
        if key in seen_keys:
            directions.append(current)
            current = {}
            seen_keys = set()
        current[key] = val
        seen_keys.add(key)
    if current:
        directions.append(current)

    if len(directions) < 2:
        return None

    orig = directions[0]
    reply = directions[1]

    try:
        return {
            "proto": proto,
            "state": state,
            "src_ip": orig.get("src", ""),
            "dst_ip": orig.get("dst", ""),
            "src_port": int(orig.get("sport", 0)),
            "dst_port": int(orig.get("dport", 0)),
            "bytes_sent": int(orig.get("bytes", 0)),
            "bytes_received": int(reply.get("bytes", 0)),
            "packets_sent": int(orig.get("packets", 0)),
            "packets_received": int(reply.get("packets", 0)),
        }
    except (ValueError, TypeError):
        return None


async def _run_conntrack() -> str:
    """conntrack komutunu calistir."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "/usr/sbin/conntrack", "-L", "-o", "extended",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        logger.error("conntrack zaman asimi")
        return ""
    except Exception as e:
        logger.error(f"conntrack hatasi: {e}")
        return ""


async def _resolve_bulk(redis_client, src_ips: list[str],
                        dst_ips: list[str]) -> tuple[dict, dict]:
    """Redis pipeline ile toplu device_id ve domain cozumleme."""
    pipe = redis_client.pipeline(transaction=False)
    for ip in src_ips:
        pipe.get(f"dns:ip_to_device:{ip}")
    for ip in dst_ips:
        pipe.get(f"dns:ip_to_domain:{ip}")

    try:
        results = await pipe.execute()
    except Exception as e:
        logger.error(f"Redis bulk resolve hatasi: {e}")
        return {}, {}

    device_map: dict[str, int | None] = {}
    for i, ip in enumerate(src_ips):
        val = results[i]
        device_map[ip] = int(val) if val else None

    domain_map: dict[str, str | None] = {}
    offset = len(src_ips)
    for i, ip in enumerate(dst_ips):
        val = results[offset + i]
        domain_map[ip] = val if val else None

    return device_map, domain_map


async def _resolve_dst_devices(redis_client, dst_ips: list[str]) -> dict[str, int | None]:
    """Internal flow hedef IP'lerini device_id'ye cozumle."""
    lan_ips = [ip for ip in dst_ips if ip.startswith(LAN_PREFIX)]
    if not lan_ips:
        return {}
    pipe = redis_client.pipeline(transaction=False)
    for ip in lan_ips:
        pipe.get(f"dns:ip_to_device:{ip}")
    try:
        results = await pipe.execute()
    except Exception:
        return {}
    return {ip: int(val) if val else None for ip, val in zip(lan_ips, results)}


async def _resolve_device_hostnames(redis_client, device_ids: set[int]) -> dict[int, str]:
    """Device hostname'lerini Redis veya DB'den coz."""
    if not device_ids:
        return {}
    # Basit: DB'den al
    hostnames = {}
    try:
        async with async_session_factory() as session:
            from app.models.device import Device
            result = await session.execute(
                select(Device.id, Device.hostname, Device.ip_address)
                .where(Device.id.in_(list(device_ids)))
            )
            for row in result.all():
                hostnames[row[0]] = row[1] or row[2] or f"#{row[0]}"
    except Exception:
        pass
    return hostnames


async def _process_conntrack(output: str, redis_client) -> dict[str, dict]:
    """Conntrack ciktisini isle, flow dict'i dondur.

    Returns:
        {flow_id: {tum flow verileri}} aktif flow'lar
    """
    now_mono = time.monotonic()
    lines = output.strip().split("\n")

    # Parse ve filtrele
    raw_flows: list[dict] = []
    for line in lines:
        entry = _parse_conntrack_line(line)
        if not entry:
            continue
        src = entry["src_ip"]
        dst = entry["dst_ip"]
        # 1) LAN -> External (cihaz disariya baglaniyor)
        if src.startswith(LAN_PREFIX) and not dst.startswith(LAN_PREFIX):
            if src != ROUTER_IP:
                entry["direction"] = "outbound"
                raw_flows.append(entry)
        # 2) External -> LAN (disaridan cihaza gelen — Nextcloud, SSH vb.)
        #    Perspektifi ceviriyoruz: LAN cihazi src, dis IP dst olarak gosterilir
        elif dst.startswith(LAN_PREFIX) and not src.startswith(LAN_PREFIX):
            if dst != ROUTER_IP:
                entry["src_ip"], entry["dst_ip"] = dst, src
                entry["src_port"], entry["dst_port"] = entry["dst_port"], entry["src_port"]
                entry["bytes_sent"], entry["bytes_received"] = entry["bytes_received"], entry["bytes_sent"]
                entry["packets_sent"], entry["packets_received"] = entry["packets_received"], entry["packets_sent"]
                entry["direction"] = "inbound"
                raw_flows.append(entry)
        # 3) LAN -> LAN (dahili trafik: Plex, SMB, NAS, printer vb.)
        elif src.startswith(LAN_PREFIX) and dst.startswith(LAN_PREFIX):
            if src != ROUTER_IP and dst != ROUTER_IP:
                entry["direction"] = "internal"
                raw_flows.append(entry)

    if not raw_flows:
        return {}

    # Unique flow'lar (5-tuple)
    seen: set[str] = set()
    unique: list[dict] = []
    for f in raw_flows:
        fid = _compute_flow_id(f["src_ip"], f["src_port"],
                               f["dst_ip"], f["dst_port"], f["proto"])
        if fid not in seen:
            seen.add(fid)
            f["flow_id"] = fid
            unique.append(f)

    # Bulk resolve
    src_ips = list({f["src_ip"] for f in unique})
    dst_ips = list({f["dst_ip"] for f in unique})
    device_map, domain_map = await _resolve_bulk(redis_client, src_ips, dst_ips)

    # Internal flow'lar icin hedef cihaz cozumleme
    dst_device_map = await _resolve_dst_devices(redis_client, dst_ips)

    # Flow dict olustur
    current_flows: dict[str, dict] = {}
    for f in unique:
        fid = f["flow_id"]
        device_id = device_map.get(f["src_ip"])
        direction = f.get("direction", "outbound")
        is_internal = direction == "internal"

        # Internal flow'larda domain yok, kategori "internal"
        domain = None if is_internal else domain_map.get(f["dst_ip"])
        category = "internal" if is_internal else (_categorize_domain(domain) if domain else None)

        # Servis/uygulama tespiti (port bazli her durumda calisir)
        svc_name, app_name = _identify_service(f["dst_port"], f["proto"], domain)

        # Hedef cihaz (internal flow'lar icin)
        dst_device_id = dst_device_map.get(f["dst_ip"]) if is_internal else None

        current_flows[fid] = {
            "flow_id": fid,
            "device_id": device_id,
            "dst_device_id": dst_device_id,
            "src_ip": f["src_ip"],
            "src_port": f["src_port"],
            "dst_ip": f["dst_ip"],
            "dst_port": f["dst_port"],
            "dst_domain": domain,
            "protocol": f["proto"],
            "state": f["state"],
            "direction": direction,
            "bytes_sent": f["bytes_sent"],
            "bytes_received": f["bytes_received"],
            "packets_sent": f["packets_sent"],
            "packets_received": f["packets_received"],
            "category": category,
            "service_name": svc_name,
            "app_name": app_name,
        }
        _last_seen[fid] = now_mono

    return current_flows


async def _update_redis_flows(current_flows: dict[str, dict],
                              redis_client, device_hostnames: dict):
    """Canli flow verisini Redis'e yaz."""
    now_ts = now_local().isoformat()
    pipe = redis_client.pipeline(transaction=False)

    active_ids = []
    device_flow_map: dict[int, list[str]] = defaultdict(list)
    large_transfers: list[tuple[str, int]] = []

    total_in = 0
    total_out = 0
    internal_count = 0
    device_ids_set: set[int] = set()

    for fid, flow in current_flows.items():
        # BPS hesapla (delta / interval)
        prev = _prev_counters.get(fid, {})
        prev_sent = prev.get("bytes_sent", 0)
        prev_recv = prev.get("bytes_received", 0)
        delta_sent = max(0, flow["bytes_sent"] - prev_sent)
        delta_recv = max(0, flow["bytes_received"] - prev_recv)
        bps_out = (delta_sent * 8) / FLOW_TRACK_INTERVAL if prev else 0
        bps_in = (delta_recv * 8) / FLOW_TRACK_INTERVAL if prev else 0

        bytes_total = flow["bytes_sent"] + flow["bytes_received"]
        total_in += flow["bytes_received"]
        total_out += flow["bytes_sent"]

        if flow.get("direction") == "internal":
            internal_count += 1

        device_id = flow.get("device_id")
        dst_device_id = flow.get("dst_device_id")
        hostname = device_hostnames.get(device_id, "") if device_id else ""
        dst_hostname = device_hostnames.get(dst_device_id, "") if dst_device_id else ""

        if device_id:
            device_ids_set.add(device_id)
            device_flow_map[device_id].append(fid)

        # Internal flow'lari hedef cihazin setine de ekle
        if dst_device_id:
            device_ids_set.add(dst_device_id)
            device_flow_map[dst_device_id].append(fid)

        # Flow hash
        flow_data = {
            "flow_id": fid,
            "device_id": str(device_id or ""),
            "device_hostname": hostname,
            "dst_device_id": str(dst_device_id or ""),
            "dst_device_hostname": dst_hostname,
            "src_ip": flow["src_ip"],
            "src_port": str(flow["src_port"]),
            "dst_ip": flow["dst_ip"],
            "dst_port": str(flow["dst_port"]),
            "dst_domain": flow.get("dst_domain") or "",
            "protocol": flow["protocol"],
            "state": flow.get("state") or "",
            "bytes_sent": str(flow["bytes_sent"]),
            "bytes_received": str(flow["bytes_received"]),
            "bytes_total": str(bytes_total),
            "packets_sent": str(flow["packets_sent"]),
            "packets_received": str(flow["packets_received"]),
            "bps_in": f"{bps_in:.0f}",
            "bps_out": f"{bps_out:.0f}",
            "category": flow.get("category") or "",
            "direction": flow.get("direction", "outbound"),
            "service_name": flow.get("service_name") or "",
            "app_name": flow.get("app_name") or "",
            "last_seen": now_ts,
        }

        pipe.hset(f"flow:live:{fid}", mapping=flow_data)
        pipe.expire(f"flow:live:{fid}", 60)

        active_ids.append(fid)

        if bytes_total >= LARGE_TRANSFER_THRESHOLD:
            large_transfers.append((fid, bytes_total))

        # Onceki sayaclari guncelle
        _prev_counters[fid] = {
            "bytes_sent": flow["bytes_sent"],
            "bytes_received": flow["bytes_received"],
        }

    # Aktif ID seti
    if active_ids:
        pipe.delete("flow:active_ids")
        pipe.sadd("flow:active_ids", *active_ids)
        pipe.expire("flow:active_ids", 60)

    # Cihaz bazli flow setleri
    for did, fids in device_flow_map.items():
        key = f"flow:device:{did}"
        pipe.delete(key)
        pipe.sadd(key, *fids)
        pipe.expire(key, 60)

    # Buyuk transferler
    pipe.delete("flow:large")
    for fid, total in large_transfers:
        pipe.zadd("flow:large", {fid: total})
    if large_transfers:
        pipe.expire("flow:large", 60)

    # Genel istatistikler
    pipe.hset("flow:stats", mapping={
        "total_active_flows": str(len(current_flows)),
        "total_bytes_in": str(total_in),
        "total_bytes_out": str(total_out),
        "total_devices_with_flows": str(len(device_ids_set)),
        "large_transfer_count": str(len(large_transfers)),
        "total_internal_flows": str(internal_count),
        "last_update": now_ts,
    })

    try:
        await pipe.execute()
    except Exception as e:
        logger.error(f"Redis flow yazma hatasi: {e}")


async def _sync_to_db(current_flows: dict[str, dict]):
    """Aktif flow'lari MariaDB'ye upsert et, bitmisleri isaretle."""
    now = now_local()

    try:
        async with async_session_factory() as session:
            # 1. Mevcut aktif flow'lari DB'den al
            active_flow_ids = list(current_flows.keys())

            if active_flow_ids:
                result = await session.execute(
                    select(ConnectionFlow.id, ConnectionFlow.flow_id)
                    .where(
                        and_(
                            ConnectionFlow.flow_id.in_(active_flow_ids),
                            ConnectionFlow.ended_at.is_(None),
                        )
                    )
                )
                existing = {row[1]: row[0] for row in result.all()}
            else:
                existing = {}

            # 2. Mevcut flow'lari guncelle, yenilerini ekle
            for fid, flow in current_flows.items():
                if fid in existing:
                    # UPDATE
                    await session.execute(
                        update(ConnectionFlow)
                        .where(ConnectionFlow.id == existing[fid])
                        .values(
                            bytes_sent=flow["bytes_sent"],
                            bytes_received=flow["bytes_received"],
                            packets_sent=flow["packets_sent"],
                            packets_received=flow["packets_received"],
                            state=flow.get("state"),
                            dst_domain=flow.get("dst_domain") or ConnectionFlow.dst_domain,
                            category=flow.get("category"),
                            direction=flow.get("direction"),
                            dst_device_id=flow.get("dst_device_id"),
                            last_seen=now,
                        )
                    )
                else:
                    # INSERT
                    session.add(ConnectionFlow(
                        flow_id=fid,
                        device_id=flow.get("device_id"),
                        dst_device_id=flow.get("dst_device_id"),
                        src_ip=flow["src_ip"],
                        src_port=flow["src_port"],
                        dst_ip=flow["dst_ip"],
                        dst_port=flow["dst_port"],
                        dst_domain=flow.get("dst_domain"),
                        protocol=flow["protocol"],
                        state=flow.get("state"),
                        direction=flow.get("direction"),
                        bytes_sent=flow["bytes_sent"],
                        bytes_received=flow["bytes_received"],
                        packets_sent=flow["packets_sent"],
                        packets_received=flow["packets_received"],
                        category=flow.get("category"),
                        first_seen=now,
                        last_seen=now,
                    ))

            # 3. Bitmis flow'lari isaretle
            # Son 2 dakikada conntrack'te gorulmeyen aktif flow'lar
            stale_cutoff = now - timedelta(seconds=_STALE_TIMEOUT)
            await session.execute(
                update(ConnectionFlow)
                .where(
                    and_(
                        ConnectionFlow.ended_at.is_(None),
                        ConnectionFlow.last_seen < stale_cutoff,
                    )
                )
                .values(ended_at=now)
            )

            await session.commit()
            logger.debug(f"DB sync: {len(current_flows)} flow guncellendi/eklendi")

    except Exception as e:
        logger.error(f"DB flow sync hatasi: {e}", exc_info=True)


async def _cleanup_old_flows():
    """Eski bitmis flow'lari sil (retention suresi gecenler)."""
    try:
        cutoff = now_local() - timedelta(days=FLOW_RETENTION_DAYS)
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM connection_flows "
                    "WHERE ended_at IS NOT NULL AND ended_at < :cutoff "
                    "LIMIT 5000"
                ),
                {"cutoff": cutoff},
            )
            await session.commit()
            if result.rowcount > 0:
                logger.info(f"Temizlik: {result.rowcount} eski flow silindi")
    except Exception as e:
        logger.error(f"Flow temizlik hatasi: {e}")


def _cleanup_stale_memory(now_mono: float):
    """Bellekteki eski flow kayitlarini temizle."""
    stale = [fid for fid, ts in _last_seen.items()
             if (now_mono - ts) > _STALE_TIMEOUT]
    for fid in stale:
        _prev_counters.pop(fid, None)
        _last_seen.pop(fid, None)
    if stale:
        logger.debug(f"Bellek temizligi: {len(stale)} stale flow silindi")


async def start_flow_tracker():
    """Ana flow takip dongusu."""
    logger.info("Flow tracker baslatiliyor...")
    await asyncio.sleep(15)  # Diger servislerin hazir olmasini bekle

    # Redis baglantisi
    redis_client = None
    for attempt in range(6):
        try:
            redis_client = await get_redis()
            await redis_client.ping()
            logger.info("Flow tracker: Redis baglantisi basarili")
            break
        except Exception as e:
            logger.warning(f"Flow tracker: Redis baglanti denemesi {attempt+1}: {e}")
            await asyncio.sleep(5)
    else:
        logger.error("Flow tracker: Redis'e baglanamadi, durduruluyor")
        return

    # Conntrack erisim testi
    test_out = await _run_conntrack()
    if not test_out:
        logger.error("Flow tracker: conntrack erisimi yok, durduruluyor")
        return

    initial_count = len(test_out.strip().splitlines())
    logger.info(f"Flow tracker AKTIF — {FLOW_TRACK_INTERVAL}s aralik, "
                f"{initial_count} baslangic baglantisi")

    # Ilk okuma (baseline)
    await _process_conntrack(test_out, redis_client)

    db_sync_counter = 0
    cleanup_counter = 0

    while True:
        try:
            output = await _run_conntrack()
            if not output:
                await asyncio.sleep(FLOW_TRACK_INTERVAL)
                continue

            # Flow'lari isle
            current_flows = await _process_conntrack(output, redis_client)

            if current_flows:
                # Device hostname'leri coz (src + dst cihazlar)
                device_ids = set()
                for f in current_flows.values():
                    if f.get("device_id"):
                        device_ids.add(f["device_id"])
                    if f.get("dst_device_id"):
                        device_ids.add(f["dst_device_id"])
                hostnames = await _resolve_device_hostnames(redis_client, device_ids)

                # Redis'e yaz
                await _update_redis_flows(current_flows, redis_client, hostnames)

            # DB sync (her FLOW_DB_SYNC_INTERVAL saniyede)
            db_sync_counter += FLOW_TRACK_INTERVAL
            if db_sync_counter >= FLOW_DB_SYNC_INTERVAL:
                db_sync_counter = 0
                if current_flows:
                    await _sync_to_db(current_flows)

            # Temizlik (her 1 saatte)
            cleanup_counter += FLOW_TRACK_INTERVAL
            if cleanup_counter >= 3600:
                cleanup_counter = 0
                await _cleanup_old_flows()

            # Bellek temizligi
            _cleanup_stale_memory(time.monotonic())

        except asyncio.CancelledError:
            logger.info("Flow tracker durduruluyor")
            raise
        except Exception as e:
            logger.error(f"Flow tracker dongu hatasi: {e}", exc_info=True)

        await asyncio.sleep(FLOW_TRACK_INTERVAL)

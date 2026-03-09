# --- Ajan: ANALIST (THE ANALYST) ---
# Per-device IP bazli nftables inet forward counter ile gercek zamanli bandwidth izleme.
# 10 saniyede bir counter'lari okur, delta hesaplar, Redis'e yazar.
# Saatlik agrega verileri DB'ye (DeviceTrafficSnapshot) kaydeder.
#
# v2: bridge MAC hook → inet forward IP hook gecisi.
# br_netfilter aktifken bridge hook'lari trafigin %99'unu kaciriyordu.
# inet forward hook tum routed trafigi gorur + WiFi (wlan0) trafigi de yakalanir.

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime

from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.hal import linux_nftables as nft
from app.services.timezone_service import now_local

logger = logging.getLogger("tonbilai.bandwidth_monitor")

# Polling aralığı (saniye) — 10s optimal: yeterli hassasiyet, düşük overhead
POLL_INTERVAL = 10

# Saatlik snapshot aralığı (saniye)
HOURLY_SNAPSHOT_INTERVAL = 3600

# Redis key'leri
REDIS_PREFIX_DEVICE = "bw:device:"      # HASH: upload_bps, download_bps, upload_total, download_total
REDIS_PREFIX_TOTAL = "bw:total"          # HASH: upload_bps, download_bps
REDIS_PREFIX_HISTORY = "bw:history:"     # LIST: son 300 JSON kayit
REDIS_HISTORY_TOTAL = "bw:history:total"
REDIS_KEY_TTL = 120  # 2 dakika TTL
HISTORY_MAX_LEN = 300  # ~50 dk (10s aralikla)

# nft reset semantigi: her read_ip_counters() cagrisi counter'lari sifirlar ve
# delta deger dondurur. Onceki counter takibine gerek kalmaz.
# Kumulatif toplam (upload_total/download_total) Redis'e yazilmak uzere burada izlenir.
_cumulative_totals: dict[str, dict[str, int]] = {}
_last_snapshot_hour: int = -1


async def _get_known_device_ips(redis_client) -> dict[str, int]:
    """Bilinen cihaz IP -> device_id eslesmesini DB'den al.
    Gateway ve Pi IP'si haric tutulur.
    """
    from app.models.device import Device
    from sqlalchemy import select

    ip_to_id: dict[str, int] = {}
    try:
        # Gateway IP'sini al — modem bandwidth izlemeden haric tutulacak
        from app.workers.device_discovery import _get_gateway_ip
        gateway_ip = _get_gateway_ip()

        # Pi'nin kendi IP'sini al
        pi_ip = None
        try:
            import subprocess
            result = subprocess.run(
                ["ip", "-4", "-o", "addr", "show", "br0"],
                capture_output=True, text=True, timeout=5,
            )
            import re
            m = re.search(r"inet\s+([\d.]+)/", result.stdout)
            if m:
                pi_ip = m.group(1)
        except Exception:
            pi_ip = "192.168.1.2"  # fallback

        async with async_session_factory() as session:
            result = await session.execute(
                select(Device.id, Device.ip_address).where(
                    Device.ip_address.isnot(None)
                )
            )
            for row in result.all():
                device_id, ip = row
                if not ip:
                    continue
                # Sadece yerel ag cihazlari (192.168.x.x)
                if not ip.startswith("192.168."):
                    continue
                # Gateway (modem) cihazini bandwidth izlemeden haric tut
                if ip == gateway_ip:
                    continue
                # Pi'nin kendisini haric tut
                if ip == pi_ip:
                    continue
                ip_to_id[ip] = device_id
    except Exception as e:
        logger.error(f"Cihaz IP listesi alinirken hata: {e}")

    return ip_to_id


async def _calculate_and_store_bandwidth(
    counters: dict[str, dict[str, int]],
    ip_to_id: dict[str, int],
    redis_client,
    elapsed_seconds: float,
):
    """nft reset counter delta'larini isleme, Redis'e yaz.

    nft reset semantigi: read_ip_counters() her cagrisinda counter'lar
    sifirlanir ve o araliktaki delta deger dondurulur. Dolayisiyla degerler
    DIREKT delta'dir — onceki degerden cikarma gerekmez.

    Total bps: _total counter'dan direkt alinir (per-device toplama yerine).
    Kumulatif toplam (upload_total / download_total) Redis'e yazmak icin
    modul seviyesi _cumulative_totals dict'i kullanilir.
    """
    global _cumulative_totals

    now_ts = int(time.time())

    # Total bps: _total counter'dan direkt
    total_data = counters.get("_total", {})
    if elapsed_seconds > 0:
        total_upload_bps = int(total_data.get("upload_bytes", 0) * 8 / elapsed_seconds)
        total_download_bps = int(total_data.get("download_bytes", 0) * 8 / elapsed_seconds)
    else:
        total_upload_bps = 0
        total_download_bps = 0

    pipe = redis_client.pipeline(transaction=False)

    for ip, current in counters.items():
        if ip == "_total":
            continue

        # nft reset: dondurilen degerler dogrudan delta'dir, cikarma gerekmez
        delta_up_bytes = current["upload_bytes"]
        delta_down_bytes = current["download_bytes"]
        delta_up_pkts = current["upload_packets"]
        delta_down_pkts = current["download_packets"]

        # bps hesapla (max 10 Gbps cap — Pi ethernet 1 Gbps, makul olmayan spike onleme)
        MAX_BPS = 10_000_000_000  # 10 Gbps
        if elapsed_seconds > 0:
            upload_bps = min(int(delta_up_bytes * 8 / elapsed_seconds), MAX_BPS)
            download_bps = min(int(delta_down_bytes * 8 / elapsed_seconds), MAX_BPS)
        else:
            upload_bps = 0
            download_bps = 0

        device_id = ip_to_id.get(ip)
        if device_id is None:
            continue

        # Kumulatif toplam izle (nft reset her cycle'da sifirladigi icin)
        if ip not in _cumulative_totals:
            _cumulative_totals[ip] = {"upload_bytes": 0, "download_bytes": 0,
                                       "upload_packets": 0, "download_packets": 0}
        _cumulative_totals[ip]["upload_bytes"] += delta_up_bytes
        _cumulative_totals[ip]["download_bytes"] += delta_down_bytes
        _cumulative_totals[ip]["upload_packets"] += delta_up_pkts
        _cumulative_totals[ip]["download_packets"] += delta_down_pkts

        cumulative = _cumulative_totals[ip]

        # Per-device Redis HASH
        device_key = f"{REDIS_PREFIX_DEVICE}{device_id}"
        pipe.hset(device_key, mapping={
            "upload_bps": upload_bps,
            "download_bps": download_bps,
            "upload_total": cumulative["upload_bytes"],
            "download_total": cumulative["download_bytes"],
            "upload_packets": cumulative["upload_packets"],
            "download_packets": cumulative["download_packets"],
            "ip": ip,
            "ts": now_ts,
        })
        pipe.expire(device_key, REDIS_KEY_TTL)

        # Per-device history
        history_key = f"{REDIS_PREFIX_HISTORY}{device_id}"
        history_entry = json.dumps({
            "ts": now_ts,
            "up": upload_bps,
            "down": download_bps,
        })
        pipe.lpush(history_key, history_entry)
        pipe.ltrim(history_key, 0, HISTORY_MAX_LEN - 1)
        pipe.expire(history_key, 7200)  # 2 saat TTL

    # Toplam bandwidth
    pipe.hset(REDIS_PREFIX_TOTAL, mapping={
        "upload_bps": total_upload_bps,
        "download_bps": total_download_bps,
        "ts": now_ts,
    })
    pipe.expire(REDIS_PREFIX_TOTAL, REDIS_KEY_TTL)

    # Toplam history
    total_entry = json.dumps({
        "ts": now_ts,
        "up": total_upload_bps,
        "down": total_download_bps,
    })
    pipe.lpush(REDIS_HISTORY_TOTAL, total_entry)
    pipe.ltrim(REDIS_HISTORY_TOTAL, 0, HISTORY_MAX_LEN - 1)
    pipe.expire(REDIS_HISTORY_TOTAL, 7200)

    try:
        await pipe.execute()
    except Exception as e:
        logger.error(f"Redis bandwidth yazma hatasi: {e}")

    return total_upload_bps, total_download_bps


async def _write_hourly_snapshot(
    counters: dict[str, dict[str, int]],
    ip_to_id: dict[str, int],
    redis_client,
):
    """Saatlik agrega snapshot'i DB'ye yaz.

    nft reset semantigi: counters sadece son 10s delta'yi icerir.
    Kumulatif toplamlar icin _cumulative_totals kullanilir.
    """
    global _last_snapshot_hour

    current_hour = now_local().replace(minute=0, second=0, microsecond=0)
    hour_key = int(current_hour.timestamp())

    if hour_key == _last_snapshot_hour:
        return

    _last_snapshot_hour = hour_key

    from app.models.device_traffic_snapshot import DeviceTrafficSnapshot

    try:
        async with async_session_factory() as session:
            # nft reset: kumulatif degerler icin _cumulative_totals kullanilir
            snapshot_source = _cumulative_totals if _cumulative_totals else counters
            for ip, data in snapshot_source.items():
                if ip == "_total":
                    continue
                device_id = ip_to_id.get(ip)
                if device_id is None:
                    continue

                # Peak bps degerlerini Redis'ten al
                device_key = f"{REDIS_PREFIX_DEVICE}{device_id}"
                bw_data = await redis_client.hgetall(device_key)

                snapshot = DeviceTrafficSnapshot(
                    device_id=device_id,
                    timestamp=current_hour,
                    period="hourly",
                    upload_bytes=data["upload_bytes"],
                    download_bytes=data["download_bytes"],
                    upload_packets=data["upload_packets"],
                    download_packets=data["download_packets"],
                    peak_upload_bps=int(bw_data.get("upload_bps", 0)),
                    peak_download_bps=int(bw_data.get("download_bps", 0)),
                )
                session.add(snapshot)

            await session.commit()
            logger.info(f"Saatlik snapshot yazildi: {len(snapshot_source)} cihaz, saat {current_hour}")
    except Exception as e:
        logger.error(f"Saatlik snapshot yazma hatasi: {e}")


async def start_bandwidth_monitor():
    """Ana bandwidth izleme dongusu (inet forward IP counter)."""
    logger.info("Bandwidth izleme iscisi baslatiliyor (inet forward IP counter)...")

    await asyncio.sleep(15)  # Diger servislerin hazir olmasini bekle

    redis_client = None
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        logger.info("Bandwidth monitor: Redis baglantisi basarili")
    except Exception as e:
        logger.error(f"Bandwidth monitor: Redis baglantisi basarisiz: {e}")
        for attempt in range(5):
            await asyncio.sleep(5)
            try:
                redis_client = await get_redis()
                await redis_client.ping()
                break
            except Exception:
                continue
        else:
            logger.error("Bandwidth monitor: Redis'e baglanamadi, isci durduruluyor.")
            return

    # NOT: Bridge accounting temizligi artik yapilmiyor.
    # Bridge chain'leri daha onceden kaldirildi, inet bw_accounting kullaniliyor.

    # Yeni inet bw_accounting tablosu olustur
    try:
        await nft.ensure_inet_bw_accounting()
        logger.info("inet bw_accounting tablosu hazir")
    except Exception as e:
        logger.error(f"inet bw_accounting tablosu olusturulamadi: {e}")
        return

    # Bilinen cihaz IP'lerini al ve counter'lari senkronize et
    ip_to_id = await _get_known_device_ips(redis_client)
    if ip_to_id:
        await nft.sync_ip_counters(list(ip_to_id.keys()))
        logger.info(f"IP counter'lar senkronize edildi: {len(ip_to_id)} cihaz")

    # Baseline okuma — onceki servis calismasindan kalan bayat counter degerlerini sifirlar.
    await nft.read_ip_counters()
    logger.info(f"Bandwidth monitor AKTIF - {POLL_INTERVAL}s aralikla inet forward counter okuma (nft reset)")

    last_sync_time = time.monotonic()
    ip_refresh_counter = 0
    _first_iteration = True  # Ilk iterasyonu atla (restart spike onleme)

    while True:
        try:
            loop_start = time.monotonic()

            # Her 6 dongu (~60s) bir IP listesini yenile
            ip_refresh_counter += 1
            if ip_refresh_counter >= 6:
                ip_refresh_counter = 0
                new_ip_to_id = await _get_known_device_ips(redis_client)
                if new_ip_to_id != ip_to_id:
                    ip_to_id = new_ip_to_id
                    await nft.sync_ip_counters(list(ip_to_id.keys()))

            # Counter'lari oku
            counters = await nft.read_ip_counters()
            if not counters:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            # Gecen sure
            elapsed = loop_start - last_sync_time
            last_sync_time = loop_start

            # Ilk iterasyonu atla — restart sonrasi bayat counter spike onleme
            if _first_iteration:
                _first_iteration = False
                logger.debug("Ilk iterasyon atlandi (restart spike onleme)")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            # Elapsed cok kucukse atla (0'a bolme / spike onleme)
            if elapsed < 2.0:
                logger.debug(f"Elapsed cok kucuk ({elapsed:.1f}s), atlanıyor")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            # Delta hesapla ve Redis'e yaz
            up_bps, down_bps = await _calculate_and_store_bandwidth(
                counters, ip_to_id, redis_client, elapsed
            )

            if up_bps > 0 or down_bps > 0:
                logger.debug(
                    f"Bandwidth: upload {up_bps:,} bps, download {down_bps:,} bps"
                )

            # Saatlik snapshot
            await _write_hourly_snapshot(counters, ip_to_id, redis_client)

        except asyncio.CancelledError:
            logger.info("Bandwidth monitor durduruluyor.")
            raise
        except Exception as e:
            logger.error(f"Bandwidth monitor dongu hatasi: {e}", exc_info=True)

        await asyncio.sleep(POLL_INTERVAL)

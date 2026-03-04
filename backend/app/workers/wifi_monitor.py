# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WiFi Monitor Worker: Her 30 saniyede bagli istemci bilgilerini Redis'e yazar.
# iw dev wlan0 station dump → parse → Redis HASH

import asyncio
import logging
import re

from app.db.redis_client import get_redis

logger = logging.getLogger("tonbilai.wifi_monitor")

POLL_INTERVAL = 30  # saniye
REDIS_TTL = 90  # saniye


async def _run_cmd(cmd: list, timeout: float = 10) -> str:
    """Komut calistir."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ""
    return stdout.decode().strip()


async def _parse_station_dump() -> list[dict]:
    """iw dev wlan0 station dump ciktisini parse et."""
    out = await _run_cmd(["iw", "dev", "wlan0", "station", "dump"])
    if not out:
        return []

    clients = []
    current = None

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Station "):
            if current:
                clients.append(current)
            mac = line.split()[1].upper()
            current = {
                "mac": mac,
                "signal": 0,
                "tx_bitrate": 0.0,
                "rx_bitrate": 0.0,
                "connected_time": 0,
            }
        elif current:
            if "signal:" in line:
                m = re.search(r"signal:\s*(-?\d+)", line)
                if m:
                    current["signal"] = int(m.group(1))
            elif "tx bitrate:" in line:
                m = re.search(r"tx bitrate:\s*([\d.]+)", line)
                if m:
                    current["tx_bitrate"] = float(m.group(1))
            elif "rx bitrate:" in line:
                m = re.search(r"rx bitrate:\s*([\d.]+)", line)
                if m:
                    current["rx_bitrate"] = float(m.group(1))
            elif "connected time:" in line:
                m = re.search(r"connected time:\s*(\d+)", line)
                if m:
                    current["connected_time"] = int(m.group(1))

    if current:
        clients.append(current)

    return clients


async def _get_arp_map() -> dict[str, str]:
    """ARP tablosundan MAC → IP eslesmesi."""
    out = await _run_cmd(["ip", "neigh", "show"])
    arp_map = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and "lladdr" in parts:
            idx = parts.index("lladdr")
            if idx + 1 < len(parts):
                ip = parts[0]
                mac = parts[idx + 1].upper()
                arp_map[mac] = ip
    return arp_map


async def _wifi_monitor_loop():
    """Ana izleme dongusu."""
    redis = await get_redis()
    logger.info("WiFi monitor worker baslatildi (30sn aralik)")

    while True:
        try:
            # hostapd calisiyor mu?
            active = await _run_cmd(["systemctl", "is-active", "hostapd"])
            if active.strip() != "active":
                # WiFi kapali, Redis'i temizle
                await redis.delete("wifi:stats")
                # Eski client key'lerini temizle
                keys = []
                async for key in redis.scan_iter("wifi:client:*"):
                    keys.append(key)
                if keys:
                    await redis.delete(*keys)
                await asyncio.sleep(POLL_INTERVAL)
                continue

            clients = await _parse_station_dump()
            arp_map = await _get_arp_map()

            # Her istemciyi Redis'e yaz
            pipe = redis.pipeline()
            active_macs = []

            for client in clients:
                mac = client["mac"]
                active_macs.append(mac)
                ip = arp_map.get(mac, "")

                key = f"wifi:client:{mac}"
                pipe.hset(key, mapping={
                    "mac": mac,
                    "ip": ip,
                    "signal": str(client["signal"]),
                    "tx_bitrate": str(client["tx_bitrate"]),
                    "rx_bitrate": str(client["rx_bitrate"]),
                    "connected_time": str(client["connected_time"]),
                })
                pipe.expire(key, REDIS_TTL)

            # Genel istatistikler
            pipe.hset("wifi:stats", mapping={
                "total_clients": str(len(clients)),
                "active": "1",
            })
            pipe.expire("wifi:stats", REDIS_TTL)

            await pipe.execute()

            # Eski istemci key'lerini temizle (artik bagli olmayanlar)
            old_keys = []
            async for key in redis.scan_iter("wifi:client:*"):
                mac_part = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
                if mac_part not in active_macs:
                    old_keys.append(key)
            if old_keys:
                await redis.delete(*old_keys)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"WiFi monitor hatasi: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def start_wifi_monitor():
    """WiFi monitor worker baslat."""
    await _wifi_monitor_loop()

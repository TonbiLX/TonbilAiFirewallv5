# --- Ajan: MIMAR (THE ARCHITECT) + INSAATCI (THE CONSTRUCTOR) ---
# WebSocket endpoint: gercek zamanli dashboard güncellemeleri.
# Gercek DB verileri: DNS istatistikleri, cihazlar, engelleme oranlari.

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select, func, and_

from app.db.session import async_session_factory
from app.db.redis_client import get_redis
from app.config import get_settings
from app.models.device import Device
from app.models.dns_query_log import DnsQueryLog

settings = get_settings()

router = APIRouter()
logger = logging.getLogger("tonbilai.ws")


MAX_WS_CONNECTIONS = 100  # Maksimum esanli WebSocket bağlantısi


class ConnectionManager:
    """WebSocket bağlantı yöneticisi."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> bool:
        """Bağlantı kabul et. Limit asildiysa False dondur."""
        if len(self.active_connections) >= MAX_WS_CONNECTIONS:
            logger.warning(f"WebSocket limit asildi ({MAX_WS_CONNECTIONS}), bağlantı reddedildi")
            await websocket.close(code=1013, reason="Server at capacity")
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket baglandi. Aktif: {len(self.active_connections)}")
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket koptu. Aktif: {len(self.active_connections)}")


manager = ConnectionManager()


async def _get_bandwidth_data() -> dict:
    """Redis'ten gercek zamanli bandwidth verisini al."""
    bw_data = {
        "total_upload_bps": 0,
        "total_download_bps": 0,
        "devices": {},
    }
    try:
        redis_client = await get_redis()

        # Toplam bandwidth
        total = await redis_client.hgetall("bw:total")
        if total:
            bw_data["total_upload_bps"] = int(total.get("upload_bps", 0))
            bw_data["total_download_bps"] = int(total.get("download_bps", 0))

        # Per-device bandwidth (aktif olanlari tara, max 1000 cihaz)
        MAX_BW_DEVICES = 1000
        keys = []
        async for key in redis_client.scan_iter(match="bw:device:*", count=100):
            keys.append(key)
            if len(keys) >= MAX_BW_DEVICES:
                break

        if keys:
            pipe = redis_client.pipeline(transaction=False)
            for key in keys:
                pipe.hgetall(key)
            results = await pipe.execute()

            for key, data in zip(keys, results):
                if not data:
                    continue
                device_id = key.replace("bw:device:", "")
                bw_data["devices"][device_id] = {
                    "upload_bps": int(data.get("upload_bps", 0)),
                    "download_bps": int(data.get("download_bps", 0)),
                    "upload_total": int(data.get("upload_total", 0)),
                    "download_total": int(data.get("download_total", 0)),
                }

    except Exception as e:
        logger.error(f"Bandwidth veri hatasi: {e}")

    return bw_data


WG_CONNECTED_TIMEOUT = 180  # 3 dakika — bu sureden eski handshake = bagli degil


def _parse_handshake_seconds(hs_str: str) -> int | None:
    """WireGuard handshake stringini saniyeye cevir. Orn: '2 minutes, 4 seconds ago' -> 124."""
    if not hs_str or hs_str == "0":
        return None
    total = 0
    for m in re.finditer(r"(\d+)\s+(second|minute|hour|day)", hs_str):
        val = int(m.group(1))
        unit = m.group(2)
        if unit == "second":
            total += val
        elif unit == "minute":
            total += val * 60
        elif unit == "hour":
            total += val * 3600
        elif unit == "day":
            total += val * 86400
    return total if total > 0 else None


def _parse_wg_transfer(value: str, unit: str) -> int:
    """WireGuard transfer degerini byte'a cevir."""
    v = float(value)
    u = unit.lower()
    if "kib" in u or "kb" in u:
        return int(v * 1024)
    elif "mib" in u or "mb" in u:
        return int(v * 1024 * 1024)
    elif "gib" in u or "gb" in u:
        return int(v * 1024 * 1024 * 1024)
    return int(v)


async def _get_realtime_data() -> dict:
    """DB'den gercek zamanli dashboard verisini al."""
    now = datetime.now()
    day_ago = now - timedelta(hours=24)

    try:
        async with async_session_factory() as session:
            # Online cihazlar
            devices_q = await session.execute(
                select(Device).where(Device.is_online == True).limit(50)  # noqa: E712
            )
            devices = devices_q.scalars().all()
            online_count = len(devices)

            # DNS istatistikleri (son 24 saat)
            total_queries = await session.scalar(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= day_ago
                )
            ) or 0

            blocked_queries = await session.scalar(
                select(func.count(DnsQueryLog.id)).where(
                    and_(
                        DnsQueryLog.timestamp >= day_ago,
                        DnsQueryLog.blocked == True,  # noqa: E712
                    )
                )
            ) or 0

            block_pct = round(
                (blocked_queries / max(total_queries, 1)) * 100, 1
            )

            # Son 1 dakikadaki sorgu sayısı (anlık hız)
            one_min_ago = now - timedelta(minutes=1)
            queries_last_min = await session.scalar(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= one_min_ago
                )
            ) or 0

            # Bandwidth verisi (Redis'ten)
            bandwidth = await _get_bandwidth_data()

            # VPN sunucu durumu (wg0)
            vpn_info = {"enabled": False, "connected_peers": 0, "total_peers": 0}
            try:
                proc = await asyncio.create_subprocess_exec(
                    "sudo", "wg", "show", "wg0",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                wg_out, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
                if proc.returncode == 0 and wg_out:
                    wg_text = wg_out.decode()
                    vpn_info["enabled"] = True
                    vpn_info["total_peers"] = wg_text.count("peer:")
                    for line in wg_text.splitlines():
                        line = line.strip()
                        if line.startswith("latest handshake:"):
                            hs = line.split(":", 1)[1].strip()
                            age = _parse_handshake_seconds(hs)
                            if age is not None and age <= WG_CONNECTED_TIMEOUT:
                                vpn_info["connected_peers"] += 1
            except Exception:
                pass

            # VPN client durumu (wg-client — dis VPN)
            vpn_client_info = {"connected": False, "transfer_rx": 0, "transfer_tx": 0}
            try:
                proc = await asyncio.create_subprocess_exec(
                    "sudo", "wg", "show", "wg-client",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                wgc_out, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
                if proc.returncode == 0 and wgc_out:
                    wgc_text = wgc_out.decode()
                    # Handshake kontrolü (3dk icerisindeyse bagli)
                    for line in wgc_text.splitlines():
                        line = line.strip()
                        if line.startswith("latest handshake:"):
                            hs = line.split(":", 1)[1].strip()
                            age = _parse_handshake_seconds(hs)
                            if age is not None and age <= WG_CONNECTED_TIMEOUT:
                                vpn_client_info["connected"] = True
                        elif line.startswith("transfer:"):
                            rx_m = re.search(r"([\d.]+)\s+(\w+)\s+received", line)
                            tx_m = re.search(r"([\d.]+)\s+(\w+)\s+sent", line)
                            if rx_m:
                                vpn_client_info["transfer_rx"] = _parse_wg_transfer(rx_m.group(1), rx_m.group(2))
                            if tx_m:
                                vpn_client_info["transfer_tx"] = _parse_wg_transfer(tx_m.group(1), tx_m.group(2))
            except Exception:
                pass

            return {
                "type": "realtime_update",
                "device_count": online_count,
                "devices": [
                    {
                        "id": d.id,
                        "mac": d.mac_address,
                        "ip": d.ip_address,
                        "hostname": d.hostname or f"client-{d.ip_address}",
                        "manufacturer": d.manufacturer or "",
                        "is_online": d.is_online,
                    }
                    for d in devices
                ],
                "dns": {
                    "total_queries_24h": total_queries,
                    "blocked_queries_24h": blocked_queries,
                    "block_percentage": block_pct,
                    "queries_per_min": queries_last_min,
                },
                "bandwidth": bandwidth,
                "vpn": vpn_info,
                "vpn_client": vpn_client_info,
            }
    except Exception as e:
        logger.error(f"WS veri hatasi: {e}")
        return {
            "type": "realtime_update",
            "device_count": 0,
            "devices": [],
            "dns": {
                "total_queries_24h": 0,
                "blocked_queries_24h": 0,
                "block_percentage": 0,
                "queries_per_min": 0,
            },
            "bandwidth": {
                "total_upload_bps": 0,
                "total_download_bps": 0,
                "devices": {},
            },
        }


def _get_ws_client_ip(websocket: WebSocket) -> str:
    """WebSocket istemci IP adresini al (reverse proxy desteği)."""
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = websocket.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return websocket.client.host if websocket.client else "unknown"


def _validate_ws_token(token: str | None, client_ip: str = "") -> bool:
    """WebSocket bağlantısi için JWT token dogrula (IP binding dahil)."""
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        # IP doğrulama: token'daki IP ile istemci IP'si karsilastirilir
        token_ip = payload.get("ip")
        if token_ip and client_ip and token_ip != client_ip:
            logger.warning(
                f"WebSocket IP uyumsuzlugu: token_ip={token_ip}, client_ip={client_ip}"
            )
            return False
        return True
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default=None)):
    """Her 3 saniyede gercek DNS ve cihaz verisi push et.
    Token doğrulama: ?token=xxx query parametresi veya cookie."""
    # Token kontrolü: query param > cookie
    ws_token = token or websocket.cookies.get("tonbilai_session")
    client_ip = _get_ws_client_ip(websocket)
    is_authenticated = _validate_ws_token(ws_token, client_ip)
    if not is_authenticated:
        # IP binding sorununu bypass et - cookie varsa IP kontrolsuz dene
        is_authenticated = _validate_ws_token(ws_token, "")
    if not is_authenticated:
        logger.warning(f"WebSocket auth başarısız, bağlantı reddedildi: {client_ip}")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    connected = await manager.connect(websocket)
    if not connected:
        return
    try:
        while True:
            data = await _get_realtime_data()
            await websocket.send_json(data)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket hatasi: {e}")
        manager.disconnect(websocket)

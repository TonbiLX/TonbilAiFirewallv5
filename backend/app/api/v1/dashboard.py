# --- Ajan: MIMAR (THE ARCHITECT) ---
# Dashboard agrege endpoint: AdGuard Home tarzi gercek DNS istatistikleri.
# Mock bandwidth verileri kaldırıldı - gercek DNS sorgu verileri gösterilir.

import asyncio
import logging
import re

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.db.redis_client import get_redis
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.device import Device
from app.models.dns_query_log import DnsQueryLog
from app.models.blocklist import Blocklist

logger = logging.getLogger("tonbilai.api.dashboard")
router = APIRouter()


def _parse_transfer_value(value: str, unit: str) -> int:
    """Transfer degerini byte'a cevir."""
    v = float(value)
    u = unit.lower()
    if "kib" in u or "kb" in u:
        return int(v * 1024)
    elif "mib" in u or "mb" in u:
        return int(v * 1024 * 1024)
    elif "gib" in u or "gb" in u:
        return int(v * 1024 * 1024 * 1024)
    return int(v)


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


REDIS_PEER_BASELINE_PREFIX = "vpn:peer:baseline:"


async def _get_vpn_summary() -> dict:
    """wg show wg0 ciktisini parse edip VPN özet bilgisi dondur."""
    vpn = {"enabled": False, "total_peers": 0, "connected_peers": 0, "total_rx": 0, "total_tx": 0}
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "wg", "show", "wg0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode != 0 or not stdout:
            return vpn
        out = stdout.decode()
        vpn["enabled"] = True
        vpn["total_peers"] = out.count("peer:")

        # Peer bloklarini parse et
        current_pubkey = None
        current_connected = False
        current_rx = 0
        current_tx = 0

        redis = await get_redis()

        for line in out.splitlines():
            line = line.strip()
            if line.startswith("peer:"):
                # Onceki peer'i isle
                if current_pubkey and current_connected:
                    key = f"{REDIS_PEER_BASELINE_PREFIX}{current_pubkey[:16]}"
                    baseline = await redis.hgetall(key)
                    base_rx = int(baseline.get("rx", 0)) if baseline else 0
                    base_tx = int(baseline.get("tx", 0)) if baseline else 0
                    s_rx = max(0, current_rx - base_rx) if current_rx >= base_rx else 0
                    s_tx = max(0, current_tx - base_tx) if current_tx >= base_tx else 0
                    vpn["total_rx"] += s_rx
                    vpn["total_tx"] += s_tx
                # Yeni peer blogu
                current_pubkey = line.split(":", 1)[1].strip()
                current_connected = False
                current_rx = 0
                current_tx = 0
            elif line.startswith("latest handshake:"):
                hs = line.split(":", 1)[1].strip()
                age = _parse_handshake_seconds(hs)
                if age is not None and age <= WG_CONNECTED_TIMEOUT:
                    vpn["connected_peers"] += 1
                    current_connected = True
            elif line.startswith("transfer:"):
                transfer = line.split(":", 1)[1].strip()
                rx_m = re.search(r"([\d.]+)\s+(\w+)\s+received", transfer)
                tx_m = re.search(r"([\d.]+)\s+(\w+)\s+sent", transfer)
                if rx_m:
                    current_rx = _parse_transfer_value(rx_m.group(1), rx_m.group(2))
                if tx_m:
                    current_tx = _parse_transfer_value(tx_m.group(1), tx_m.group(2))

        # Son peer'i isle
        if current_pubkey and current_connected:
            key = f"{REDIS_PEER_BASELINE_PREFIX}{current_pubkey[:16]}"
            baseline = await redis.hgetall(key)
            base_rx = int(baseline.get("rx", 0)) if baseline else 0
            base_tx = int(baseline.get("tx", 0)) if baseline else 0
            s_rx = max(0, current_rx - base_rx) if current_rx >= base_rx else 0
            s_tx = max(0, current_tx - base_tx) if current_tx >= base_tx else 0
            vpn["total_rx"] += s_rx
            vpn["total_tx"] += s_tx
    except Exception as e:
        logger.warning(f"WireGuard VPN durum alma hatasi: {e}")
    return vpn


@router.get("/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ana dashboard için agrege veri - AdGuard Home tarzi."""
    now = datetime.now()
    day_ago = now - timedelta(hours=24)

    # Cihaz sayilari (gercek, DNS sorgularindan kesfedilen)
    total_devices = await db.scalar(select(func.count(Device.id))) or 0
    online_devices = await db.scalar(
        select(func.count(Device.id)).where(Device.is_online == True)  # noqa: E712
    ) or 0
    blocked_devices = await db.scalar(
        select(func.count(Device.id)).where(Device.is_blocked == True)  # noqa: E712
    ) or 0

    # DNS istatistikleri (son 24 saat)
    total_queries = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(DnsQueryLog.timestamp >= day_ago)
    ) or 0
    blocked_queries = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(
            and_(DnsQueryLog.timestamp >= day_ago, DnsQueryLog.blocked == True)  # noqa: E712
        )
    ) or 0
    block_percentage = round((blocked_queries / max(total_queries, 1)) * 100, 1)

    # Aktif blocklist sayısı ve toplam engelli domain
    active_blocklists = await db.scalar(
        select(func.count(Blocklist.id)).where(Blocklist.enabled == True)  # noqa: E712
    ) or 0
    total_blocked_domains = await db.scalar(
        select(func.sum(Blocklist.domain_count)).where(Blocklist.enabled == True)  # noqa: E712
    ) or 0

    # En aktif istemciler (top 5)
    top_clients_q = await db.execute(
        select(
            DnsQueryLog.client_ip,
            func.count(DnsQueryLog.id).label("query_count"),
        )
        .where(DnsQueryLog.timestamp >= day_ago)
        .group_by(DnsQueryLog.client_ip)
        .order_by(desc("query_count"))
        .limit(5)
    )
    top_clients = [
        {"client_ip": r[0], "query_count": r[1]}
        for r in top_clients_q.all()
    ]

    # En cok sorgulanan domainler (top 5)
    top_queried_q = await db.execute(
        select(
            DnsQueryLog.domain,
            func.count(DnsQueryLog.id).label("count"),
        )
        .where(DnsQueryLog.timestamp >= day_ago)
        .group_by(DnsQueryLog.domain)
        .order_by(desc("count"))
        .limit(5)
    )
    top_queried = [{"domain": r[0], "count": r[1]} for r in top_queried_q.all()]

    # En cok engellenen domainler (top 5)
    top_blocked_q = await db.execute(
        select(
            DnsQueryLog.domain,
            func.count(DnsQueryLog.id).label("count"),
        )
        .where(
            and_(DnsQueryLog.timestamp >= day_ago, DnsQueryLog.blocked == True)  # noqa: E712
        )
        .group_by(DnsQueryLog.domain)
        .order_by(desc("count"))
        .limit(5)
    )
    top_blocked = [{"domain": r[0], "count": r[1]} for r in top_blocked_q.all()]

    # VPN durumu
    vpn = await _get_vpn_summary()

    return {
        "devices": {
            "total": total_devices,
            "online": online_devices,
            "blocked": blocked_devices,
        },
        "dns": {
            "total_queries_24h": total_queries,
            "blocked_queries_24h": blocked_queries,
            "block_percentage": block_percentage,
            "active_blocklists": active_blocklists,
            "total_blocked_domains": total_blocked_domains,
        },
        "vpn": vpn,
        "top_clients": top_clients,
        "top_queried_domains": top_queried,
        "top_blocked_domains": top_blocked,
    }

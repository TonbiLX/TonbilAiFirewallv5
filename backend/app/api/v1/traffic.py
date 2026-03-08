# --- Ajan: MIMAR (THE ARCHITECT) + ANALIST (THE ANALYST) ---
# Trafik log API endpointleri: per-device trafik, bandwidth, aktif bağlantılar.

import json
from fastapi import APIRouter, Depends, Query, Path
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import aliased
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.redis_client import get_redis
from app.models.traffic_log import TrafficLog
from app.models.device import Device
from app.models.device_traffic_snapshot import DeviceTrafficSnapshot
from app.models.dns_query_log import DnsQueryLog
from app.models.connection_flow import ConnectionFlow
from app.schemas.traffic_log import TrafficLogResponse
from app.schemas.connection_flow import (
    LiveFlowResponse, FlowHistoryResponse, FlowStatsResponse, DeviceFlowSummary,
)

router = APIRouter()


@router.get("/", response_model=List[TrafficLogResponse])
async def list_traffic_logs(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    device_id: Optional[int] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trafik loglarını filtrele ve listele (cihaz bilgisi ile)."""
    query = (
        select(
            TrafficLog.id, TrafficLog.timestamp, TrafficLog.device_id,
            TrafficLog.destination_domain, TrafficLog.category,
            TrafficLog.bytes_sent, TrafficLog.bytes_received, TrafficLog.protocol,
            Device.hostname, Device.ip_address, Device.mac_address,
        )
        .outerjoin(Device, TrafficLog.device_id == Device.id)
        .order_by(desc(TrafficLog.timestamp))
    )

    if device_id:
        query = query.where(TrafficLog.device_id == device_id)
    if category:
        query = query.where(TrafficLog.category == category)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return [
        TrafficLogResponse(
            id=r.id, timestamp=r.timestamp, device_id=r.device_id,
            hostname=r.hostname, ip_address=r.ip_address, mac_address=r.mac_address,
            destination_domain=r.destination_domain, category=r.category,
            bytes_sent=r.bytes_sent or 0, bytes_received=r.bytes_received or 0,
            protocol=r.protocol,
        )
        for r in rows
    ]


@router.get("/categories")
async def traffic_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Benzersiz trafik kategorilerini dondur."""
    result = await db.execute(
        select(TrafficLog.category, func.count(TrafficLog.id).label("count"))
        .where(TrafficLog.category.isnot(None))
        .group_by(TrafficLog.category)
        .order_by(desc("count"))
    )
    return [{"category": row[0], "count": row[1]} for row in result.all()]


@router.get("/per-device")
async def per_device_traffic(
    period: str = Query(default="24h", description="Zaman aralığı: 1h, 6h, 24h, 7d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Her cihazin toplam upload/download/paket bilgisi."""
    hours_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    hours = hours_map.get(period, 24)
    since = datetime.now() - timedelta(hours=hours)

    result = await db.execute(
        select(
            TrafficLog.device_id,
            func.sum(TrafficLog.bytes_sent).label("upload_bytes"),
            func.sum(TrafficLog.bytes_received).label("download_bytes"),
            func.count(TrafficLog.id).label("connection_count"),
        )
        .where(TrafficLog.timestamp >= since)
        .group_by(TrafficLog.device_id)
        .order_by(desc("download_bytes"))
    )
    rows = result.all()

    # Cihaz bilgilerini al
    device_ids = [r[0] for r in rows]
    devices_result = await db.execute(
        select(Device).where(Device.id.in_(device_ids))
    )
    devices_map = {d.id: d for d in devices_result.scalars().all()}

    # Redis'ten anlik bandwidth
    redis_client = await get_redis()
    bw_data = {}
    if device_ids:
        pipe = redis_client.pipeline(transaction=False)
        for did in device_ids:
            pipe.hgetall(f"bw:device:{did}")
        bw_results = await pipe.execute()
        for did, bw in zip(device_ids, bw_results):
            if bw:
                bw_data[did] = bw

    items = []
    for row in rows:
        device_id, upload, download, conn_count = row
        d = devices_map.get(device_id)
        bw = bw_data.get(device_id, {})
        items.append({
            "device_id": device_id,
            "hostname": d.hostname if d else None,
            "mac_address": d.mac_address if d else None,
            "ip_address": d.ip_address if d else None,
            "is_online": d.is_online if d else False,
            "upload_bytes": upload or 0,
            "download_bytes": download or 0,
            "connection_count": conn_count or 0,
            "upload_bps": int(bw.get("upload_bps", 0)),
            "download_bps": int(bw.get("download_bps", 0)),
        })

    return items


@router.get("/per-device/{device_id}/history")
async def device_traffic_history(
    device_id: int = Path(...),
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tek cihazin bandwidth trendi (grafik verisi).

    Kısa sureler için Redis gercek zamanli veri (10s aralık, ~50dk),
    uzun sureler için DB saatlik snapshot kullanir.
    """
    redis_client = await get_redis()
    items = []

    # 1) Redis'ten gercek zamanli bandwidth gecmisi (10s aralıkla, son ~50dk)
    redis_history_raw = await redis_client.lrange(f"bw:history:{device_id}", 0, 299)
    if redis_history_raw:
        for entry in reversed(redis_history_raw):  # eski -> yeni sirayla
            try:
                data = json.loads(entry)
                items.append({
                    "timestamp": datetime.utcfromtimestamp(data["ts"]).isoformat(),
                    "upload_bps": data.get("up", 0),
                    "download_bps": data.get("down", 0),
                    "source": "realtime",
                })
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    # 2) DB saatlik snapshot'lar (daha uzun periyotlar için)
    since = datetime.now() - timedelta(hours=hours)
    result = await db.execute(
        select(DeviceTrafficSnapshot)
        .where(
            and_(
                DeviceTrafficSnapshot.device_id == device_id,
                DeviceTrafficSnapshot.timestamp >= since,
                DeviceTrafficSnapshot.period == "hourly",
            )
        )
        .order_by(DeviceTrafficSnapshot.timestamp)
    )
    snapshots = result.scalars().all()

    for s in snapshots:
        items.append({
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "upload_bps": s.peak_upload_bps or 0,
            "download_bps": s.peak_download_bps or 0,
            "upload_bytes": s.upload_bytes,
            "download_bytes": s.download_bytes,
            "source": "hourly",
        })

    # Eger Redis verisi varsa onu öncelikli goster, yoksa DB
    # Karmasik birlestime yerine: Redis verisi varsa onu, yoksa DB'yi dondur
    if redis_history_raw and len(items) > len(snapshots):
        # Redis verisi var - sadece realtime verileri dondur (daha granular)
        return [i for i in items if i.get("source") == "realtime"]

    # Sadece DB snapshot varsa veya hicbir sey yoksa
    return [i for i in items if i.get("source") == "hourly"] if snapshots else items


@router.get("/per-device/{device_id}/connections")
async def device_active_connections(
    device_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cihazin aktif bağlantılari (conntrack'ten canlı)."""
    from app.hal import linux_nftables as nft

    # Cihaz IP adresini al
    device = await db.get(Device, device_id)
    if not device or not device.ip_address:
        return []

    device_ip = device.ip_address
    all_conns = await nft.get_active_connections()

    # DNS IP->domain cache
    redis_client = await get_redis()
    device_conns = []

    for conn in all_conns:
        if conn["src_ip"] == device_ip or conn["dst_ip"] == device_ip:
            # Hedef domain'i bul
            dst_ip = conn["dst_ip"] if conn["src_ip"] == device_ip else conn["src_ip"]
            domain = await redis_client.get(f"dns:ip_to_domain:{dst_ip}")

            device_conns.append({
                "protocol": conn["protocol"],
                "src_ip": conn["src_ip"],
                "src_port": conn["src_port"],
                "dst_ip": conn["dst_ip"],
                "dst_port": conn["dst_port"],
                "dst_domain": domain or None,
                "bytes_sent": conn["bytes_sent"],
                "bytes_received": conn["bytes_received"],
                "state": conn["state"],
            })

    return device_conns


@router.get("/per-device/{device_id}/top-destinations")
async def device_top_destinations(
    device_id: int = Path(...),
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cihazin en cok eristigi hedefler."""
    since = datetime.now() - timedelta(hours=hours)

    result = await db.execute(
        select(
            TrafficLog.destination_domain,
            TrafficLog.category,
            func.sum(TrafficLog.bytes_sent).label("total_sent"),
            func.sum(TrafficLog.bytes_received).label("total_received"),
            func.count(TrafficLog.id).label("conn_count"),
        )
        .where(
            and_(
                TrafficLog.device_id == device_id,
                TrafficLog.timestamp >= since,
                TrafficLog.destination_domain.isnot(None),
            )
        )
        .group_by(TrafficLog.destination_domain, TrafficLog.category)
        .order_by(desc("total_received"))
        .limit(limit)
    )

    return [
        {
            "domain": row[0],
            "category": row[1],
            "bytes_sent": row[2] or 0,
            "bytes_received": row[3] or 0,
            "total_bytes": (row[2] or 0) + (row[3] or 0),
            "connection_count": row[4] or 0,
        }
        for row in result.all()
    ]


@router.get("/per-device/{device_id}/dns-queries")
async def device_dns_queries(
    device_id: int = Path(...),
    limit: int = Query(default=50, ge=1, le=200),
    blocked_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cihazin DNS sorgu gecmisi."""
    query = (
        select(DnsQueryLog)
        .where(DnsQueryLog.device_id == device_id)
        .order_by(desc(DnsQueryLog.timestamp))
        .limit(limit)
    )
    if blocked_only:
        query = query.where(DnsQueryLog.blocked == True)  # noqa: E712

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "domain": log.domain,
            "query_type": log.query_type,
            "blocked": log.blocked,
            "block_reason": log.block_reason,
            "response_ip": log.answer_ip,
        }
        for log in logs
    ]


@router.get("/realtime")
async def realtime_bandwidth(
    current_user: User = Depends(get_current_user),
):
    """Anlik toplam bandwidth (Redis'ten)."""
    redis_client = await get_redis()
    total = await redis_client.hgetall("bw:total")

    # History
    history_raw = await redis_client.lrange("bw:history:total", 0, 29)
    history = []
    for entry in history_raw:
        try:
            history.append(json.loads(entry))
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "upload_bps": int(total.get("upload_bps", 0)) if total else 0,
        "download_bps": int(total.get("download_bps", 0)) if total else 0,
        "history": list(reversed(history)),
    }


@router.get("/total")
async def total_traffic_stats(
    period: str = Query(default="24h"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toplam trafik istatistikleri."""
    hours_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    hours = hours_map.get(period, 24)
    since = datetime.now() - timedelta(hours=hours)

    # Toplam byte sayilari
    totals = await db.execute(
        select(
            func.sum(TrafficLog.bytes_sent).label("total_upload"),
            func.sum(TrafficLog.bytes_received).label("total_download"),
            func.count(func.distinct(TrafficLog.device_id)).label("devices_with_traffic"),
            func.count(TrafficLog.id).label("total_connections"),
        )
        .where(TrafficLog.timestamp >= since)
    )
    row = totals.one()

    # Aktif bağlantı sayısı
    from app.hal import linux_nftables as nft
    conn_count = await nft.get_connection_count()

    return {
        "total_upload": row[0] or 0,
        "total_download": row[1] or 0,
        "devices_with_traffic": row[2] or 0,
        "total_connections": row[3] or 0,
        "active_connections": conn_count["active"],
        "max_connections": conn_count["max"],
        "period": period,
    }


# ─── Flow Endpointleri (Per-Flow Baglanti Takibi) ─────────────────────


def _redis_hash_to_flow(h: dict) -> dict:
    """Redis hash'ini LiveFlowResponse formatina cevir."""
    return {
        "flow_id": h.get("flow_id", ""),
        "device_id": int(h["device_id"]) if h.get("device_id") else None,
        "device_hostname": h.get("device_hostname") or None,
        "device_ip": h.get("src_ip") or None,
        "src_ip": h.get("src_ip", ""),
        "src_port": int(h["src_port"]) if h.get("src_port") else None,
        "dst_ip": h.get("dst_ip", ""),
        "dst_port": int(h["dst_port"]) if h.get("dst_port") else None,
        "dst_domain": h.get("dst_domain") or None,
        "protocol": h.get("protocol", ""),
        "state": h.get("state") or None,
        "direction": h.get("direction") or None,
        "service_name": h.get("service_name") or None,
        "app_name": h.get("app_name") or None,
        "bytes_sent": int(h.get("bytes_sent", 0)),
        "bytes_received": int(h.get("bytes_received", 0)),
        "bytes_total": int(h.get("bytes_total", 0)),
        "packets_sent": int(h.get("packets_sent", 0)),
        "packets_received": int(h.get("packets_received", 0)),
        "bps_in": float(h.get("bps_in", 0)),
        "bps_out": float(h.get("bps_out", 0)),
        "first_seen": None,
        "last_seen": h.get("last_seen"),
        "ended_at": None,
        "category": h.get("category") or None,
        "dst_device_id": int(h["dst_device_id"]) if h.get("dst_device_id") else None,
        "dst_device_hostname": h.get("dst_device_hostname") or None,
    }


@router.get("/flows/stats", response_model=FlowStatsResponse)
async def flow_stats(
    current_user: User = Depends(get_current_user),
):
    """Genel flow istatistikleri (Redis'ten)."""
    redis_client = await get_redis()
    stats = await redis_client.hgetall("flow:stats")
    if not stats:
        return FlowStatsResponse()

    return FlowStatsResponse(
        total_active_flows=int(stats.get("total_active_flows", 0)),
        total_bytes_in=int(stats.get("total_bytes_in", 0)),
        total_bytes_out=int(stats.get("total_bytes_out", 0)),
        total_devices_with_flows=int(stats.get("total_devices_with_flows", 0)),
        large_transfer_count=int(stats.get("large_transfer_count", 0)),
        total_internal_flows=int(stats.get("total_internal_flows", 0)),
        last_update=stats.get("last_update"),
    )


@router.get("/flows/live", response_model=List[LiveFlowResponse])
async def live_flows(
    device_id: Optional[int] = None,
    protocol: Optional[str] = None,
    dst_port: Optional[int] = None,
    dst_domain: Optional[str] = None,
    min_bytes: Optional[int] = None,
    direction: Optional[str] = None,
    state: Optional[str] = Query(None, description="Filter by connection state (e.g. SYN_RECV, ESTABLISHED)"),
    sort_by: str = Query(default="bytes_total"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
):
    """Canli aktif flow'lar (Redis'ten, gercek zamanli)."""
    redis_client = await get_redis()

    # Aktif flow ID'lerini al
    flow_ids = await redis_client.smembers("flow:active_ids")
    if not flow_ids:
        return []

    # Toplu okuma
    pipe = redis_client.pipeline(transaction=False)
    for fid in flow_ids:
        pipe.hgetall(f"flow:live:{fid}")
    results = await pipe.execute()

    flows = []
    for h in results:
        if not h:
            continue
        flow = _redis_hash_to_flow(h)

        # Filtreler
        if state and (flow.get("state") or "").upper() != state.upper():
            continue
        if direction and flow.get("direction") != direction:
            continue
        if device_id is not None:
            # device_id veya dst_device_id eslesmesi (internal flow'larda her iki taraf)
            if flow.get("device_id") != device_id and flow.get("dst_device_id") != device_id:
                continue
        if protocol and flow.get("protocol", "").upper() != protocol.upper():
            continue
        if dst_port is not None and flow.get("dst_port") != dst_port:
            continue
        if dst_domain and dst_domain.lower() not in (flow.get("dst_domain") or "").lower():
            continue
        if min_bytes is not None and flow.get("bytes_total", 0) < min_bytes:
            continue

        flows.append(flow)

    # Siralama
    reverse = sort_order == "desc"
    sort_key = sort_by if sort_by in ("bytes_total", "bps_in", "bps_out",
                                       "bytes_sent", "bytes_received",
                                       "last_seen", "first_seen") else "bytes_total"
    flows.sort(key=lambda f: f.get(sort_key, 0) or 0, reverse=reverse)

    return flows[:limit]


@router.get("/flows/large-transfers", response_model=List[LiveFlowResponse])
async def large_transfers(
    min_bytes: int = Query(default=1_000_000),
    current_user: User = Depends(get_current_user),
):
    """Buyuk aktif transferler (>1MB, Redis ZSET'ten)."""
    redis_client = await get_redis()

    # ZSET'ten buyukten kucuge
    flow_ids = await redis_client.zrevrange("flow:large", 0, -1)
    if not flow_ids:
        return []

    pipe = redis_client.pipeline(transaction=False)
    for fid in flow_ids:
        pipe.hgetall(f"flow:live:{fid}")
    results = await pipe.execute()

    flows = []
    for h in results:
        if not h:
            continue
        flow = _redis_hash_to_flow(h)
        if flow.get("bytes_total", 0) >= min_bytes:
            flows.append(flow)

    flows.sort(key=lambda f: f.get("bytes_total", 0), reverse=True)
    return flows


@router.get("/flows/history", response_model=FlowHistoryResponse)
async def flow_history(
    device_id: Optional[int] = None,
    dst_domain: Optional[str] = None,
    dst_port: Optional[int] = None,
    protocol: Optional[str] = None,
    min_bytes: Optional[int] = None,
    direction: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="last_seen"),
    sort_order: str = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gecmis flow kayitlari (MariaDB'den, sayfalamali)."""
    since = datetime.now() - timedelta(hours=hours)

    # Temel sorgu
    conditions = [ConnectionFlow.first_seen >= since]
    if device_id is not None:
        conditions.append(
            or_(ConnectionFlow.device_id == device_id,
                ConnectionFlow.dst_device_id == device_id)
        )
    if direction:
        conditions.append(ConnectionFlow.direction == direction)
    if dst_domain:
        conditions.append(ConnectionFlow.dst_domain.contains(dst_domain))
    if dst_port is not None:
        conditions.append(ConnectionFlow.dst_port == dst_port)
    if protocol:
        conditions.append(ConnectionFlow.protocol == protocol.upper())
    if min_bytes is not None:
        conditions.append(
            (ConnectionFlow.bytes_sent + ConnectionFlow.bytes_received) >= min_bytes
        )

    where_clause = and_(*conditions)

    # Toplam sayisi
    count_result = await db.execute(
        select(func.count(ConnectionFlow.id)).where(where_clause)
    )
    total = count_result.scalar() or 0

    # Siralama
    order_col_map = {
        "last_seen": ConnectionFlow.last_seen,
        "first_seen": ConnectionFlow.first_seen,
        "bytes_total": (ConnectionFlow.bytes_sent + ConnectionFlow.bytes_received),
        "dst_domain": ConnectionFlow.dst_domain,
    }
    order_col = order_col_map.get(sort_by, ConnectionFlow.last_seen)
    order_func = desc(order_col) if sort_order == "desc" else order_col

    # Veri sorgusu (Device JOIN — src + dst)
    DstDevice = aliased(Device)
    result = await db.execute(
        select(
            ConnectionFlow,
            Device.hostname.label("device_hostname"),
            DstDevice.hostname.label("dst_device_hostname"),
        )
        .outerjoin(Device, ConnectionFlow.device_id == Device.id)
        .outerjoin(DstDevice, ConnectionFlow.dst_device_id == DstDevice.id)
        .where(where_clause)
        .order_by(order_func)
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    items = []
    for row in rows:
        cf = row[0]
        hostname = row[1]
        dst_hostname = row[2]
        items.append(LiveFlowResponse(
            flow_id=cf.flow_id,
            device_id=cf.device_id,
            device_hostname=hostname,
            device_ip=cf.src_ip,
            src_ip=cf.src_ip,
            src_port=cf.src_port,
            dst_ip=cf.dst_ip,
            dst_port=cf.dst_port,
            dst_domain=cf.dst_domain,
            protocol=cf.protocol,
            state=cf.state,
            direction=cf.direction,
            bytes_sent=cf.bytes_sent or 0,
            bytes_received=cf.bytes_received or 0,
            bytes_total=(cf.bytes_sent or 0) + (cf.bytes_received or 0),
            packets_sent=cf.packets_sent or 0,
            packets_received=cf.packets_received or 0,
            first_seen=cf.first_seen,
            last_seen=cf.last_seen,
            ended_at=cf.ended_at,
            category=cf.category,
            dst_device_id=cf.dst_device_id,
            dst_device_hostname=dst_hostname,
        ))

    return FlowHistoryResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/flows/device/{device_id}/summary", response_model=DeviceFlowSummary)
async def device_flow_summary(
    device_id: int = Path(...),
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cihaz bazli flow ozeti: top domain'ler, top port'lar."""
    since = datetime.now() - timedelta(hours=hours)
    where = and_(
        or_(ConnectionFlow.device_id == device_id,
            ConnectionFlow.dst_device_id == device_id),
        ConnectionFlow.first_seen >= since,
    )

    # Cihaz bilgisi
    device = await db.get(Device, device_id)

    # Aktif flow sayisi (Redis)
    redis_client = await get_redis()
    active_fids = await redis_client.smembers(f"flow:device:{device_id}")
    active_count = len(active_fids) if active_fids else 0

    # Toplam istatistikler
    totals = await db.execute(
        select(
            func.count(ConnectionFlow.id),
            func.sum(ConnectionFlow.bytes_sent),
            func.sum(ConnectionFlow.bytes_received),
        ).where(where)
    )
    t = totals.one()

    # Top domain'ler
    domains = await db.execute(
        select(
            ConnectionFlow.dst_domain,
            func.sum(ConnectionFlow.bytes_sent + ConnectionFlow.bytes_received).label("total"),
            func.count(ConnectionFlow.id).label("cnt"),
        )
        .where(and_(where, ConnectionFlow.dst_domain.isnot(None)))
        .group_by(ConnectionFlow.dst_domain)
        .order_by(desc("total"))
        .limit(10)
    )

    # Top port'lar
    ports = await db.execute(
        select(
            ConnectionFlow.dst_port,
            ConnectionFlow.protocol,
            func.sum(ConnectionFlow.bytes_sent + ConnectionFlow.bytes_received).label("total"),
            func.count(ConnectionFlow.id).label("cnt"),
        )
        .where(and_(where, ConnectionFlow.dst_port.isnot(None)))
        .group_by(ConnectionFlow.dst_port, ConnectionFlow.protocol)
        .order_by(desc("total"))
        .limit(10)
    )

    return DeviceFlowSummary(
        device_id=device_id,
        device_hostname=device.hostname if device else None,
        active_flows=active_count,
        total_flows_period=t[0] or 0,
        total_bytes_sent=t[1] or 0,
        total_bytes_received=t[2] or 0,
        top_domains=[
            {"domain": r[0], "bytes_total": r[1] or 0, "flow_count": r[2] or 0}
            for r in domains.all()
        ],
        top_ports=[
            {"port": r[0], "protocol": r[1], "bytes_total": r[2] or 0, "flow_count": r[3] or 0}
            for r in ports.all()
        ],
    )

# --- Ajan: MIMAR (THE ARCHITECT) ---
# Cihaz API endpointleri: CRUD + canlı cihazlar + engelleme/engel kaldirma.

import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc, or_, and_
from typing import List, Optional

import logging

import redis.asyncio as aioredis

from app.db.session import get_db
from app.api.deps import get_driver_dep, get_redis_dep
from app.api.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse, BandwidthLimitUpdate
from app.models.device_connection_log import DeviceConnectionLog
from app.schemas.device_connection_log import DeviceConnectionLogResponse
from app.models.connection_flow import ConnectionFlow
from app.hal.base_driver import BaseNetworkDriver

router = APIRouter()

# Scan rate limit — art arda taramalari onle
_last_scan_time: float = 0
_SCAN_COOLDOWN = 30  # saniye


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "desc",
    status: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum kayıtlı cihazlari listele. Siralama, filtre ve sayfalama desteği."""
    query = select(Device)

    # Durum filtresi
    if status == "online":
        query = query.where(Device.is_online == True)  # noqa: E712
    elif status == "offline":
        query = query.where(Device.is_online == False)  # noqa: E712

    # Siralama
    sort_column = Device.last_seen  # varsayilan
    if sort_by == "hostname":
        sort_column = Device.hostname
    elif sort_by == "ip_address":
        sort_column = Device.ip_address
    elif sort_by == "first_seen":
        sort_column = Device.first_seen
    elif sort_by == "is_online":
        sort_column = Device.is_online

    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/live")
async def live_devices(
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """HAL'dan su an bagli cihazlari al (mock veya gercek)."""
    return await driver.get_connected_devices()


@router.post("/scan")
async def scan_devices(
    current_user: User = Depends(get_current_user),
):
    """Ag taramasi tetikle: broadcast ping + ip neigh + offline isaretleme.
    Tarama ~5-8 saniye surer. 30 saniye cooldown uygulanir."""
    global _last_scan_time
    now = time.monotonic()
    if now - _last_scan_time < _SCAN_COOLDOWN:
        remaining = int(_SCAN_COOLDOWN - (now - _last_scan_time))
        raise HTTPException(status_code=429, detail=f"Tarama bekleme suresi: {remaining}s")
    _last_scan_time = now

    from app.workers.device_discovery import _active_network_scan, mark_offline_devices
    from app.db.session import async_session_factory

    await _active_network_scan()
    await mark_offline_devices()

    async with async_session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.ip_address.isnot(None))
        )
        devices = result.scalars().all()

    return {
        "message": "Ag taramasi tamamlandi",
        "online": sum(1 for d in devices if d.is_online),
        "offline": sum(1 for d in devices if not d.is_online),
        "total": len(devices),
    }


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ID ile cihaz getir."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    return device


@router.post("/", response_model=DeviceResponse, status_code=201)
async def create_device(
    data: DeviceCreate, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Yeni cihaz kaydet."""
    device = Device(**data.model_dump())
    db.add(device)
    await db.flush()
    await db.refresh(device)
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihaz bilgilerini güncelle. Profil degisikliginde bandwidth ve DNS filtresi uygulanir."""
    _logger = logging.getLogger("tonbilai.devices")
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    update_data = data.model_dump(exclude_unset=True)
    old_profile_id = device.profile_id

    for key, value in update_data.items():
        setattr(device, key, value)

    await db.flush()

    # Profil degistiyse Redis cache ve bandwidth guncelle
    if "profile_id" in update_data and device.profile_id != old_profile_id:
        if device.profile_id:
            # Yeni profil atandi
            await redis_client.set(
                f"dns:device_profile:{device.id}",
                str(device.profile_id),
            )
            # Profilin bandwidth limitini cihaza uygula
            profile = await db.get(Profile, device.profile_id)
            if profile and profile.bandwidth_limit_mbps:
                device.bandwidth_limit_mbps = profile.bandwidth_limit_mbps
                try:
                    await driver.set_bandwidth_limit(
                        device.mac_address, profile.bandwidth_limit_mbps
                    )
                except Exception as e:
                    _logger.warning(f"BW limit uygulama hatasi ({device.mac_address}): {e}")
            await db.flush()
        else:
            # Profil kaldirildi
            await redis_client.delete(f"dns:device_profile:{device.id}")
            # Bandwidth limiti sifirla
            if old_profile_id:
                device.bandwidth_limit_mbps = None
                try:
                    await driver.set_bandwidth_limit(device.mac_address, 0)
                except Exception as e:
                    _logger.warning(f"BW limit sifirla hatasi ({device.mac_address}): {e}")
                await db.flush()

    # IPTV cihaz degisikligi → Redis iptv:device_ids SET guncelle
    if "is_iptv" in update_data and device.ip_address:
        if device.is_iptv:
            await redis_client.sadd("iptv:device_ids", device.ip_address)
            _logger.info(f"IPTV cihaz eklendi: {device.hostname} ({device.ip_address})")
        else:
            await redis_client.srem("iptv:device_ids", device.ip_address)
            _logger.info(f"IPTV cihaz cikarildi: {device.hostname} ({device.ip_address})")

    await db.refresh(device)
    return device


@router.post("/{device_id}/block")
async def block_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihazi engelle."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await driver.block_device(device.mac_address)
    device.is_blocked = True
    await db.flush()
    # DNS proxy'ye engelli cihazi bildir (block page gostermesi icin)
    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()
        await redis.sadd("dns:blocked_device_ids", str(device_id))
    except Exception:
        pass
    return {"status": "blocked", "mac": device.mac_address}


@router.post("/{device_id}/unblock")
async def unblock_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihazin engelini kaldir."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await driver.unblock_device(device.mac_address)
    device.is_blocked = False
    await db.flush()
    # DNS proxy'den engelli cihazi cikar
    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()
        await redis.srem("dns:blocked_device_ids", str(device_id))
    except Exception:
        pass
    return {"status": "unblocked", "mac": device.mac_address}


@router.patch("/{device_id}/bandwidth")
async def set_device_bandwidth(
    device_id: int,
    data: BandwidthLimitUpdate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihaz için bant genisligi siniri ayarla/kaldir."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    if device.mac_address.startswith(("AA:00:", "DD:0T:")):
        raise HTTPException(
            status_code=400,
            detail="Sentetik MAC adresli cihaza limit uygulanamaz"
        )

    limit = data.limit_mbps or 0
    success = await driver.set_bandwidth_limit(device.mac_address, limit)
    if not success:
        raise HTTPException(status_code=500, detail="Bant genişliği siniri uygulanamadi")

    device.bandwidth_limit_mbps = data.limit_mbps  # None = limitsiz
    await db.flush()

    if limit > 0:
        return {"status": "limited", "mac": device.mac_address, "limit_mbps": limit}
    return {"status": "unlimited", "mac": device.mac_address}


@router.get("/{device_id}/connection-history", response_model=List[DeviceConnectionLogResponse])
async def get_connection_history(
    device_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cihazin bağlantı gecmisini getir."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    result = await db.execute(
        select(DeviceConnectionLog)
        .where(DeviceConnectionLog.device_id == device_id)
        .order_by(DeviceConnectionLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


# Bilinen DoH sunucusu IP'leri
_DOH_IPS = {
    "8.8.8.8", "8.8.4.4",           # Google
    "1.1.1.1", "1.0.0.1",           # Cloudflare
    "9.9.9.9", "149.112.112.112",    # Quad9
    "208.67.222.222", "208.67.220.220",  # OpenDNS
    "94.140.14.14", "94.140.15.15",  # AdGuard
}

_PI_IP = "192.168.1.2"


@router.get("/external-dns-connections")
async def get_external_dns_connections(
    hours: int = Query(default=1, ge=1, le=24, description="Kaç saat geriye bakılsın"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dış DNS bağlantıları tespiti: DoT (port 853), DoH (port 443 + bilinen IP),
    DNS Bypass (port 53 -> Pi dışı hedef) yapan cihazları listele.

    Gerçek trafik verilerinden (connection_flows tablosu) hesaplanır.
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    # DoT: port 853 herhangi bir hedefe
    dot_condition = ConnectionFlow.dst_port == 853

    # DoH: port 443 + bilinen DoH IP'lerinden birine
    doh_condition = and_(
        ConnectionFlow.dst_port == 443,
        or_(*[ConnectionFlow.dst_ip == ip for ip in _DOH_IPS]),
    )

    # DNS Bypass: port 53 + Pi'nin IP'si değil
    bypass_condition = and_(
        ConnectionFlow.dst_port == 53,
        ConnectionFlow.dst_ip != _PI_IP,
    )

    query = (
        select(
            ConnectionFlow.device_id,
            ConnectionFlow.src_ip,
            ConnectionFlow.dst_ip,
            ConnectionFlow.dst_port,
            ConnectionFlow.dst_domain,
            ConnectionFlow.last_seen,
        )
        .where(
            and_(
                ConnectionFlow.last_seen >= since,
                or_(dot_condition, doh_condition, bypass_condition),
            )
        )
        .order_by(ConnectionFlow.last_seen.desc())
        .limit(200)
    )

    rows = (await db.execute(query)).all()

    # Cihaz bilgilerini toplu çek
    device_ids = {r.device_id for r in rows if r.device_id}
    devices_map: dict = {}
    if device_ids:
        dev_result = await db.execute(
            select(Device).where(Device.id.in_(device_ids))
        )
        for dev in dev_result.scalars().all():
            devices_map[dev.id] = dev

    results = []
    seen = set()
    for r in rows:
        # detection_type belirle
        if r.dst_port == 853:
            detection_type = "dot"
        elif r.dst_port == 443 and r.dst_ip in _DOH_IPS:
            detection_type = "doh"
        else:
            detection_type = "dns_bypass"

        key = (r.src_ip, r.dst_ip, r.dst_port, detection_type)
        if key in seen:
            continue
        seen.add(key)

        dev = devices_map.get(r.device_id) if r.device_id else None
        results.append({
            "device_id": r.device_id,
            "device_ip": r.src_ip,
            "mac_address": dev.mac_address if dev else None,
            "hostname": dev.hostname if dev else None,
            "os_type": dev.device_type if dev else None,
            "detection_type": detection_type,
            "dst_ip": r.dst_ip,
            "dst_port": r.dst_port,
            "dst_domain": r.dst_domain,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
        })

    return {"connections": results, "total": len(results), "hours": hours}

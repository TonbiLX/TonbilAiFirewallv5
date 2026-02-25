# --- Ajan: MIMAR (THE ARCHITECT) ---
# DHCP Sunucu API endpointleri: havuz yönetimi, kiralama takibi, statik atama.
# dnsmasq host'ta çalışır, backend volume mount ile kontrol eder.

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

_MAC_RE = re.compile(r'^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$')


def _validate_mac_param(mac: str) -> str:
    """MAC adres parametresini dogrula ve normalize et."""
    if not _MAC_RE.match(mac):
        raise HTTPException(status_code=400, detail="Gecersiz MAC adresi")
    return mac.upper()

logger = logging.getLogger("tonbilai.dhcp_api")

from app.db.session import get_db
from app.api.deps import get_driver_dep
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dhcp_pool import DhcpPool
from app.models.dhcp_lease import DhcpLease
from app.schemas.dhcp_pool import DhcpPoolCreate, DhcpPoolUpdate, DhcpPoolResponse
from app.schemas.dhcp_lease import (
    DhcpLeaseResponse, StaticLeaseCreate, DhcpStatsResponse,
    DhcpServiceStatusResponse, DhcpLiveLeaseResponse,
)
from app.hal.base_driver import BaseNetworkDriver
from app.hal.linux_dhcp_driver import is_dnsmasq_running, parse_leases_file, remove_lease_from_file, DNSMASQ_CONF_DIR, DNSMASQ_LEASES_FILE
from app.workers.dhcp_worker import mark_mac_deleted

router = APIRouter()


# ===== DHCP HAVUZ ENDPOINTLERI =====

@router.get("/pools", response_model=List[DhcpPoolResponse])
async def list_pools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum DHCP havuzlarini listele."""
    result = await db.execute(select(DhcpPool).order_by(DhcpPool.id))
    return result.scalars().all()


@router.post("/pools", response_model=DhcpPoolResponse, status_code=201)
async def create_pool(
    data: DhcpPoolCreate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Yeni DHCP havuzu oluştur."""
    pool = DhcpPool(**data.model_dump())
    db.add(pool)
    await db.flush()
    await db.refresh(pool)
    # HAL'a bildir
    await driver.configure_dhcp_pool(data.model_dump() | {"id": pool.id})
    return pool


@router.patch("/pools/{pool_id}", response_model=DhcpPoolResponse)
async def update_pool(
    pool_id: int,
    data: DhcpPoolUpdate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """DHCP havuzunu güncelle."""
    pool = await db.get(DhcpPool, pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="DHCP havuzu bulunamadı")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pool, key, value)
    await db.flush()
    await db.refresh(pool)
    # HAL'a bildir
    pool_dict = {
        "id": pool.id, "name": pool.name, "subnet": pool.subnet,
        "netmask": pool.netmask, "range_start": pool.range_start,
        "range_end": pool.range_end, "gateway": pool.gateway,
        "enabled": pool.enabled, "lease_time_seconds": pool.lease_time_seconds,
        "dns_servers": pool.dns_servers or [],
    }
    await driver.configure_dhcp_pool(pool_dict)
    return pool


@router.delete("/pools/{pool_id}", status_code=204)
async def delete_pool(
    pool_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """DHCP havuzunu sil."""
    pool = await db.get(DhcpPool, pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="DHCP havuzu bulunamadı")
    await driver.remove_dhcp_pool(str(pool_id))
    await db.delete(pool)


@router.post("/pools/{pool_id}/toggle")
async def toggle_pool(
    pool_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """DHCP havuzunu etkinlestir/devre disi birak."""
    pool = await db.get(DhcpPool, pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="DHCP havuzu bulunamadı")
    pool.enabled = not pool.enabled
    await db.flush()
    await db.refresh(pool)
    # Config dosyasini güncelle
    pool_dict = {
        "id": pool.id, "name": pool.name, "subnet": pool.subnet,
        "netmask": pool.netmask, "range_start": pool.range_start,
        "range_end": pool.range_end, "gateway": pool.gateway,
        "enabled": pool.enabled, "lease_time_seconds": pool.lease_time_seconds,
        "dns_servers": pool.dns_servers or [],
    }
    await driver.configure_dhcp_pool(pool_dict)
    return {"id": pool_id, "enabled": pool.enabled}


# ===== DHCP KIRALAMA ENDPOINTLERI =====

@router.get("/leases", response_model=List[DhcpLeaseResponse])
async def list_leases(
    static_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aktif DHCP kiralamalarini listele."""
    query = select(DhcpLease).order_by(DhcpLease.lease_start.desc())
    if static_only:
        query = query.where(DhcpLease.is_static == True)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/leases/live", response_model=List[DhcpLiveLeaseResponse])
async def live_leases(
    current_user: User = Depends(get_current_user),
):
    """dnsmasq lease dosyasindan canlı kiralamalari oku (DB degil)."""
    raw_leases = parse_leases_file()
    return [
        DhcpLiveLeaseResponse(
            mac_address=l["mac_address"],
            ip_address=l["ip_address"],
            hostname=l["hostname"],
            lease_end=l.get("lease_end"),
            is_expired=l.get("is_expired", False),
        )
        for l in raw_leases
    ]


@router.get("/leases/{mac_address}", response_model=DhcpLeaseResponse)
async def get_lease(
    mac_address: str, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tek cihaz kiralama detayi."""
    mac_address = _validate_mac_param(mac_address)
    result = await db.execute(
        select(DhcpLease).where(DhcpLease.mac_address == mac_address)
    )
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Kiralama bulunamadı")
    return lease


# ===== DHCP SERVIS DURUMU =====

@router.get("/service/status", response_model=DhcpServiceStatusResponse)
async def dhcp_service_status(
    current_user: User = Depends(get_current_user),
):
    """dnsmasq servis durumunu kontrol et."""
    pool_config_count = 0
    try:
        if DNSMASQ_CONF_DIR.exists():
            pool_config_count = len(list(DNSMASQ_CONF_DIR.glob("pool-*.conf")))
    except Exception:
        pass

    active_leases = parse_leases_file()
    active_count = len([l for l in active_leases if not l.get("is_expired")])

    return DhcpServiceStatusResponse(
        dnsmasq_running=is_dnsmasq_running(),
        config_dir_exists=DNSMASQ_CONF_DIR.exists(),
        lease_file_exists=DNSMASQ_LEASES_FILE.exists(),
        pool_config_count=pool_config_count,
        active_leases_count=active_count,
    )


@router.post("/leases/static", response_model=DhcpLeaseResponse, status_code=201)
async def create_static_lease(
    data: StaticLeaseCreate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Statik IP ataması (MAC-IP reservasyonu) oluştur."""
    # 1) MAC ile mevcut lease ara
    result = await db.execute(
        select(DhcpLease).where(DhcpLease.mac_address == data.mac_address)
    )
    existing_by_mac = result.scalar_one_or_none()

    # 2) IP ile cakısan lease ara (farkli MAC)
    result2 = await db.execute(
        select(DhcpLease).where(
            DhcpLease.ip_address == data.ip_address,
            DhcpLease.mac_address != data.mac_address,
        )
    )
    conflict_by_ip = result2.scalar_one_or_none()

    # 3) IP cakismasi varsa: eski lease'i sil veya IP'sini bosalt
    if conflict_by_ip:
        if conflict_by_ip.is_static:
            # Diger statik lease'in IP'sini serbest birak
            conflict_by_ip.is_static = False
        await db.delete(conflict_by_ip)
        await db.flush()

    # 4) MAC ile mevcut lease varsa güncelle, yoksa oluştur
    if existing_by_mac:
        existing_by_mac.ip_address = data.ip_address
        existing_by_mac.hostname = data.hostname
        existing_by_mac.is_static = True
        lease = existing_by_mac
    else:
        lease = DhcpLease(
            mac_address=data.mac_address,
            ip_address=data.ip_address,
            hostname=data.hostname,
            is_static=True,
        )
        db.add(lease)

    await driver.add_static_lease(data.mac_address, data.ip_address, data.hostname or "")
    await db.flush()
    await db.refresh(lease)
    return lease


@router.delete("/leases/static/{mac_address}", status_code=204)
async def delete_static_lease(
    mac_address: str,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Statik IP atamasıni kaldir."""
    mac_address = _validate_mac_param(mac_address)
    result = await db.execute(
        select(DhcpLease).where(
            DhcpLease.mac_address == mac_address,
            DhcpLease.is_static == True,  # noqa: E712
        )
    )
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Statik atama bulunamadı")
    try:
        await driver.remove_static_lease(mac_address)
    except Exception:
        pass  # dnsmasq config yazma başarısız olsa bile DB'den sil
    lease.is_static = False
    await db.flush()

    # Sync worker'in bu lease'i yeniden oluşturmasini engelle
    mark_mac_deleted(mac_address)


@router.delete("/leases/{mac_address}", status_code=204)
async def delete_lease(
    mac_address: str,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Herhangi bir lease kaydini sil (dinamik veya statik)."""
    mac_address = _validate_mac_param(mac_address)
    result = await db.execute(
        select(DhcpLease).where(DhcpLease.mac_address == mac_address)
    )
    lease = result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease bulunamadı")

    # Statik lease ise dnsmasq config'den de kaldir
    if lease.is_static:
        try:
            await driver.remove_static_lease(mac_address)
        except Exception:
            pass

    # Ilgili device kaydinin IP'sini temizle (lease silindiyse IP artik gecersiz)
    from app.models.device import Device
    dev_result = await db.execute(
        select(Device).where(Device.mac_address == mac_address)
    )
    device = dev_result.scalar_one_or_none()
    if device and device.ip_address == lease.ip_address:
        device.ip_address = None
        device.is_online = False
        logger.info(
            f"Lease silme: device {device.mac_address} ({device.hostname}) "
            f"IP {lease.ip_address} temizlendi"
        )

    await db.delete(lease)
    await db.flush()

    # dnsmasq lease dosyasindan da sil (sync worker tekrar oluşturmasin)
    try:
        remove_lease_from_file(mac_address)
    except Exception:
        pass
    # Ek güvenlik: sync worker'in bu lease'i yeniden oluşturmasini engelle
    mark_mac_deleted(mac_address)


# ===== DHCP ISTATISTIKLER =====

@router.get("/stats", response_model=DhcpStatsResponse)
async def dhcp_stats(
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """DHCP istatistikleri."""
    total_pools = await db.scalar(select(func.count(DhcpPool.id))) or 0
    active_pools = await db.scalar(
        select(func.count(DhcpPool.id)).where(DhcpPool.enabled == True)  # noqa: E712
    ) or 0

    total_leases = await db.scalar(select(func.count(DhcpLease.id))) or 0
    static_leases = await db.scalar(
        select(func.count(DhcpLease.id)).where(DhcpLease.is_static == True)  # noqa: E712
    ) or 0

    # Toplam IP hesapla
    pools = (await db.execute(select(DhcpPool).where(DhcpPool.enabled == True))).scalars().all()  # noqa: E712
    total_ips = 0
    for pool in pools:
        try:
            start_last = int(pool.range_start.split(".")[-1])
            end_last = int(pool.range_end.split(".")[-1])
            total_ips += end_last - start_last + 1
        except (ValueError, IndexError):
            pass

    return DhcpStatsResponse(
        total_pools=total_pools,
        active_pools=active_pools,
        total_ips=total_ips,
        assigned_ips=total_leases,
        available_ips=max(0, total_ips - total_leases),
        static_leases=static_leases,
        dynamic_leases=total_leases - static_leases,
        dnsmasq_running=is_dnsmasq_running(),
    )

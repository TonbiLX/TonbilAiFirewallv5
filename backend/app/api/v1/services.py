# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Servis Engelleme API: AdGuard Home tarzi cihaz bazinda
# servis engelleme (YouTube, Netflix, WhatsApp vb.)

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc

import redis.asyncio as aioredis

from app.db.session import get_db
from app.api.deps import get_redis_dep, get_current_user
from app.models.user import User
from app.models.blocked_service import BlockedService
from app.models.device_blocked_service import DeviceBlockedService
from app.models.device import Device
from app.schemas.blocked_service import (
    BlockedServiceResponse,
    DeviceBlockedServiceResponse,
    DeviceServiceToggle,
    DeviceServiceBulkUpdate,
    ServiceGroupResponse,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.services")


@router.get("/", response_model=List[BlockedServiceResponse])
async def list_services(
    group: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum engelleme servislerini listele. Opsiyonel grup filtresi."""
    query = select(BlockedService).where(
        BlockedService.enabled == True  # noqa: E712
    ).order_by(BlockedService.group_name, BlockedService.name)
    if group:
        query = query.where(BlockedService.group_name == group)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/groups", response_model=List[ServiceGroupResponse])
async def list_service_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Servis gruplarini servis sayısıyla listele."""
    result = await db.execute(
        select(
            BlockedService.group_name,
            sqlfunc.count(BlockedService.id).label("count"),
        )
        .where(BlockedService.enabled == True)  # noqa: E712
        .group_by(BlockedService.group_name)
        .order_by(BlockedService.group_name)
    )
    return [
        ServiceGroupResponse(group=row[0], count=row[1])
        for row in result.all()
    ]


@router.get("/devices/{device_id}", response_model=List[DeviceBlockedServiceResponse])
async def get_device_services(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bir cihazin tum servis durumlarini getir (engelli/açık)."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    # Tum servisleri al
    all_services = (
        await db.execute(
            select(BlockedService)
            .where(BlockedService.enabled == True)  # noqa: E712
            .order_by(BlockedService.group_name, BlockedService.name)
        )
    ).scalars().all()

    # Cihazin engelli servislerini al
    device_blocks = (
        await db.execute(
            select(DeviceBlockedService).where(
                DeviceBlockedService.device_id == device_id,
                DeviceBlockedService.blocked == True,  # noqa: E712
            )
        )
    ).scalars().all()
    blocked_map = {dbs.service_id: dbs for dbs in device_blocks}

    result = []
    for svc in all_services:
        dbs = blocked_map.get(svc.id)
        result.append(
            DeviceBlockedServiceResponse(
                service_id=svc.service_id,
                name=svc.name,
                group_name=svc.group_name,
                icon_svg=svc.icon_svg,
                blocked=dbs is not None,
                schedule=dbs.schedule if dbs else None,
            )
        )
    return result


@router.put("/devices/{device_id}/toggle")
async def toggle_device_service(
    device_id: int,
    data: DeviceServiceToggle,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Bir cihaz için tek servis toggle (engelle/ac)."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    # Servisi bul
    svc = (
        await db.execute(
            select(BlockedService).where(
                BlockedService.service_id == data.service_id
            )
        )
    ).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="Servis bulunamadı")

    # Upsert
    existing = (
        await db.execute(
            select(DeviceBlockedService).where(
                DeviceBlockedService.device_id == device_id,
                DeviceBlockedService.service_id == svc.id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.blocked = data.blocked
        existing.schedule = data.schedule
    else:
        dbs = DeviceBlockedService(
            device_id=device_id,
            service_id=svc.id,
            blocked=data.blocked,
            schedule=data.schedule,
        )
        db.add(dbs)

    await db.flush()

    # Redis güncelle
    await sync_device_services_to_redis(device_id, db, redis_client)

    action = "engellendi" if data.blocked else "acildi"
    logger.info(f"Cihaz {device_id}: {svc.name} {action}")

    return {
        "status": "ok",
        "device_id": device_id,
        "service_id": data.service_id,
        "service_name": svc.name,
        "blocked": data.blocked,
    }


@router.put("/devices/{device_id}/bulk")
async def bulk_update_device_services(
    device_id: int,
    data: DeviceServiceBulkUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Bir cihaz için toplu servis güncelleme.
    Gönderilen service_id listesi engellenir, geri kalani acilir."""
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    # Tum servisleri al
    all_services = (
        await db.execute(select(BlockedService))
    ).scalars().all()
    svc_map = {s.service_id: s.id for s in all_services}

    # Mevcut kayitlari temizle
    existing = (
        await db.execute(
            select(DeviceBlockedService).where(
                DeviceBlockedService.device_id == device_id
            )
        )
    ).scalars().all()

    existing_map = {e.service_id: e for e in existing}

    blocked_ids = set()
    for sid in data.blocked_service_ids:
        db_svc_id = svc_map.get(sid)
        if db_svc_id:
            blocked_ids.add(db_svc_id)

    # Güncelle/oluştur
    for db_svc_id in svc_map.values():
        should_block = db_svc_id in blocked_ids
        ex = existing_map.get(db_svc_id)
        if ex:
            ex.blocked = should_block
        elif should_block:
            db.add(DeviceBlockedService(
                device_id=device_id,
                service_id=db_svc_id,
                blocked=True,
            ))

    await db.flush()
    await sync_device_services_to_redis(device_id, db, redis_client)

    return {
        "status": "ok",
        "device_id": device_id,
        "blocked_count": len(blocked_ids),
    }


async def sync_device_services_to_redis(
    device_id: int,
    db: AsyncSession,
    redis_client: aioredis.Redis,
):
    """Bir cihazin engelli servislerini Redis'e senkronize et."""
    result = await db.execute(
        select(DeviceBlockedService, BlockedService)
        .join(BlockedService, DeviceBlockedService.service_id == BlockedService.id)
        .where(
            DeviceBlockedService.device_id == device_id,
            DeviceBlockedService.blocked == True,  # noqa: E712
        )
    )

    redis_key = f"dns:device_blocked_services:{device_id}"
    await redis_client.delete(redis_key)

    service_ids = []
    for dbs, svc in result.all():
        service_ids.append(svc.service_id)

    if service_ids:
        await redis_client.sadd(redis_key, *service_ids)

    logger.debug(
        f"Cihaz {device_id} Redis sync: {len(service_ids)} engelli servis"
    )


async def rebuild_all_device_services_redis(redis_client: aioredis.Redis):
    """Başlangicta tum cihazlarin servis engellemelerini Redis'e yukle."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(DeviceBlockedService, BlockedService)
            .join(BlockedService, DeviceBlockedService.service_id == BlockedService.id)
            .where(DeviceBlockedService.blocked == True)  # noqa: E712
        )

        device_services: dict[int, list[str]] = {}
        for dbs, svc in result.all():
            device_services.setdefault(dbs.device_id, []).append(svc.service_id)

        for device_id, svc_ids in device_services.items():
            redis_key = f"dns:device_blocked_services:{device_id}"
            await redis_client.delete(redis_key)
            if svc_ids:
                await redis_client.sadd(redis_key, *svc_ids)

        logger.info(
            f"Device-service Redis rebuild: {len(device_services)} cihaz yuklendi"
        )


# rebuild_all için session factory gerekli
from app.db.session import async_session_factory  # noqa: E402

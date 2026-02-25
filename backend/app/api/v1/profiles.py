# --- Ajan: MIMAR (THE ARCHITECT) ---
# Profil CRUD API endpointleri.
# Profil olusturma/guncelleme sirasinda kategori domain setleri ve
# bant genisligi limitleri otomatik uygulanir.

import logging

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user, get_redis_dep, get_driver_dep
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

import redis.asyncio as aioredis

from app.db.session import get_db
from app.models.profile import Profile, ProfileType
from app.models.device import Device
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.hal.base_driver import BaseNetworkDriver
from app.workers.blocklist_worker import rebuild_profile_domains

router = APIRouter()
logger = logging.getLogger("tonbilai.profiles")


@router.get("/", response_model=List[ProfileResponse])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum profilleri listele."""
    result = await db.execute(select(Profile).order_by(Profile.id))
    return result.scalars().all()


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ID ile profil getir."""
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil bulunamadi")
    return profile


@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(
    data: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Yeni profil olustur."""
    profile = Profile(
        name=data.name,
        profile_type=ProfileType(data.profile_type),
        allowed_hours=data.allowed_hours,
        content_filters=data.content_filters,
        bandwidth_limit_mbps=data.bandwidth_limit_mbps,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    # Profil domain setini Redis'te olustur
    if profile.content_filters:
        await rebuild_profile_domains(profile.id, redis_client)

    return profile


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Profil guncelle."""
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil bulunamadi")

    update_data = data.model_dump(exclude_unset=True)
    old_content_filters = profile.content_filters
    old_bandwidth = profile.bandwidth_limit_mbps

    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.flush()
    await db.refresh(profile)

    # content_filters degistiyse profil domain setini yeniden olustur
    if "content_filters" in update_data and profile.content_filters != old_content_filters:
        await rebuild_profile_domains(profile.id, redis_client)

    # bandwidth degistiyse tum profil cihazlarina uygula
    if "bandwidth_limit_mbps" in update_data and profile.bandwidth_limit_mbps != old_bandwidth:
        devices_result = await db.execute(
            select(Device).where(Device.profile_id == profile_id)
        )
        for device in devices_result.scalars().all():
            new_limit = profile.bandwidth_limit_mbps or 0
            device.bandwidth_limit_mbps = profile.bandwidth_limit_mbps
            try:
                await driver.set_bandwidth_limit(device.mac_address, new_limit)
            except Exception as e:
                logger.warning(
                    f"BW limit uygulama hatasi ({device.mac_address}): {e}"
                )
        await db.flush()

    return profile


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Profil sil. Bagli cihazlarin profil atamasi ve bandwidth limiti kaldirilir."""
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profil bulunamadi")

    # Bagli cihazlarin profilini kaldir ve bandwidth sifirla
    devices_result = await db.execute(
        select(Device).where(Device.profile_id == profile_id)
    )
    for device in devices_result.scalars().all():
        device.profile_id = None
        # Bandwidth limiti sifirla
        if device.bandwidth_limit_mbps:
            device.bandwidth_limit_mbps = None
            try:
                await driver.set_bandwidth_limit(device.mac_address, 0)
            except Exception:
                pass
        # Redis cache temizle
        await redis_client.delete(f"dns:device_profile:{device.id}")

    await db.delete(profile)
    await db.flush()

    # Redis'ten profil domain setini sil
    await redis_client.delete(f"dns:profile_domains:{profile_id}")

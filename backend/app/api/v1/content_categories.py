# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Icerik filtre kategorisi API: engelleme gruplari yonetimi.
# Kategoriler blocklist'lere ve ozel domainlere baglanir, profiller uzerinden
# cihaz bazinda DNS filtreleme saglar.

import logging

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user, get_redis_dep
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

import redis.asyncio as aioredis

from app.db.session import get_db
from app.models.content_category import ContentCategory
from app.models.category_blocklist import CategoryBlocklist
from app.models.blocklist import Blocklist
from app.models.profile import Profile
from app.schemas.content_category import (
    ContentCategoryCreate, ContentCategoryUpdate,
)
from app.workers.blocklist_worker import (
    rebuild_category_domains,
    rebuild_profile_domains,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.content_categories")


async def _rebuild_affected_profiles(
    category_key: str,
    db: AsyncSession,
    redis_client: aioredis.Redis,
):
    """Bu kategoriyi kullanan tum profillerin domain setlerini yeniden olustur."""
    result = await db.execute(select(Profile))
    profiles = result.scalars().all()
    for profile in profiles:
        if profile.content_filters and category_key in profile.content_filters:
            await rebuild_profile_domains(profile.id, redis_client)


async def _build_category_response(
    category: ContentCategory, db: AsyncSession
) -> dict:
    """Kategori objesinden blocklist bilgileriyle zenginlestirilmis response dict olustur."""
    # Linked blocklist ID'leri
    bl_result = await db.execute(
        select(CategoryBlocklist.blocklist_id).where(
            CategoryBlocklist.category_id == category.id
        )
    )
    bl_ids = [row[0] for row in bl_result.all()]

    # Blocklist detaylari
    blocklists = []
    if bl_ids:
        bl_detail = await db.execute(
            select(Blocklist).where(Blocklist.id.in_(bl_ids))
        )
        for bl in bl_detail.scalars().all():
            blocklists.append({
                "id": bl.id,
                "name": bl.name,
                "domain_count": bl.domain_count or 0,
                "enabled": bl.enabled,
            })

    return {
        "id": category.id,
        "key": category.key,
        "name": category.name,
        "description": category.description,
        "icon": category.icon,
        "color": category.color,
        "example_domains": category.example_domains,
        "custom_domains": category.custom_domains,
        "domain_count": category.domain_count,
        "enabled": category.enabled,
        "blocklist_ids": bl_ids,
        "blocklists": blocklists,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


@router.get("/")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum icerik filtre kategorilerini listele (blocklist bilgileriyle)."""
    result = await db.execute(select(ContentCategory).order_by(ContentCategory.key))
    categories = result.scalars().all()

    response = []
    for cat in categories:
        response.append(await _build_category_response(cat, db))
    return response


@router.post("/", status_code=201)
async def create_category(
    data: ContentCategoryCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Yeni icerik filtre kategorisi olustur."""
    existing = await db.execute(
        select(ContentCategory).where(ContentCategory.key == data.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"'{data.key}' anahtari zaten mevcut")

    # Kategori olustur (blocklist_ids haric)
    cat_data = data.model_dump(exclude={"blocklist_ids"})
    category = ContentCategory(**cat_data)
    db.add(category)
    await db.flush()

    # Blocklist'leri bagla
    if data.blocklist_ids:
        for bl_id in data.blocklist_ids:
            # Blocklist var mi kontrol et
            bl = await db.get(Blocklist, bl_id)
            if bl:
                db.add(CategoryBlocklist(
                    category_id=category.id, blocklist_id=bl_id
                ))
        await db.flush()

    await db.commit()
    await db.refresh(category)

    # Kategori domain setini olustur
    await rebuild_category_domains(category.key, redis_client)

    # Etkilenen profilleri yeniden olustur
    await _rebuild_affected_profiles(category.key, db, redis_client)

    return await _build_category_response(category, db)


@router.patch("/{category_id}")
async def update_category(
    category_id: int,
    data: ContentCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Kategoriyi guncelle."""
    category = await db.get(ContentCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadi")

    update_data = data.model_dump(exclude_unset=True)
    blocklist_ids = update_data.pop("blocklist_ids", None)

    # Model alanlarini guncelle
    for key, value in update_data.items():
        setattr(category, key, value)

    # Blocklist baglantilarini guncelle
    if blocklist_ids is not None:
        # Eski baglantilari sil
        await db.execute(
            delete(CategoryBlocklist).where(
                CategoryBlocklist.category_id == category.id
            )
        )
        # Yeni baglantilari ekle
        for bl_id in blocklist_ids:
            bl = await db.get(Blocklist, bl_id)
            if bl:
                db.add(CategoryBlocklist(
                    category_id=category.id, blocklist_id=bl_id
                ))

    await db.flush()
    await db.commit()
    await db.refresh(category)

    # Domain setini yeniden olustur
    needs_rebuild = (
        blocklist_ids is not None
        or "custom_domains" in data.model_dump(exclude_unset=True)
        or "enabled" in data.model_dump(exclude_unset=True)
    )
    if needs_rebuild:
        await rebuild_category_domains(category.key, redis_client)
        await _rebuild_affected_profiles(category.key, db, redis_client)

    return await _build_category_response(category, db)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Kategoriyi sil."""
    category = await db.get(ContentCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadi")

    category_key = category.key

    # Blocklist baglantilarini sil
    await db.execute(
        delete(CategoryBlocklist).where(
            CategoryBlocklist.category_id == category.id
        )
    )

    await db.delete(category)
    await db.commit()

    # Redis'ten kategori domain setini sil
    await redis_client.delete(f"dns:category_domains:{category_key}")

    # Etkilenen profilleri yeniden olustur
    await _rebuild_affected_profiles(category_key, db, redis_client)

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Cihaz bazinda özel DNS kurallari API: belirli bir cihaz için
# domain engelleme veya izin verme CRUD işlemleri + Redis senkronizasyonu.

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import redis.asyncio as aioredis

from app.db.session import get_db, async_session_factory
from app.api.deps import get_redis_dep, get_current_user
from app.models.user import User
from app.models.device_custom_rule import DeviceCustomRule, DeviceCustomRuleType
from app.models.device import Device
from app.schemas.device_custom_rule import DeviceCustomRuleCreate, DeviceCustomRuleUpdate, DeviceCustomRuleSummary

router = APIRouter()
logger = logging.getLogger("tonbilai.device_custom_rules")


# ===== REDIS SYNC =====

async def sync_device_custom_rules_to_redis(
    device_id: int,
    db: AsyncSession,
    redis_client: aioredis.Redis,
):
    """Bir cihazin özel kurallarini Redis'e senkronize et."""
    result = await db.execute(
        select(DeviceCustomRule).where(DeviceCustomRule.device_id == device_id)
    )
    rules = result.scalars().all()

    blocked_key = f"dns:device_custom_blocked:{device_id}"
    allowed_key = f"dns:device_custom_allowed:{device_id}"
    await redis_client.delete(blocked_key)
    await redis_client.delete(allowed_key)

    blocked_domains = []
    allowed_domains = []
    for rule in rules:
        if rule.rule_type == DeviceCustomRuleType.BLOCK:
            blocked_domains.append(rule.domain.lower())
        elif rule.rule_type == DeviceCustomRuleType.ALLOW:
            allowed_domains.append(rule.domain.lower())

    if blocked_domains:
        await redis_client.sadd(blocked_key, *blocked_domains)
    if allowed_domains:
        await redis_client.sadd(allowed_key, *allowed_domains)

    logger.debug(
        f"Cihaz {device_id} özel kural Redis sync: "
        f"{len(blocked_domains)} engel, {len(allowed_domains)} izin"
    )


async def rebuild_all_device_custom_rules_redis(redis_client: aioredis.Redis):
    """Başlangicta tum cihazlarin özel kurallarini Redis'e yukle."""
    async with async_session_factory() as session:
        result = await session.execute(select(DeviceCustomRule))
        rules = result.scalars().all()

        device_blocked: dict[int, list[str]] = {}
        device_allowed: dict[int, list[str]] = {}

        for rule in rules:
            if rule.rule_type == DeviceCustomRuleType.BLOCK:
                device_blocked.setdefault(rule.device_id, []).append(rule.domain.lower())
            elif rule.rule_type == DeviceCustomRuleType.ALLOW:
                device_allowed.setdefault(rule.device_id, []).append(rule.domain.lower())

        all_device_ids = set(device_blocked.keys()) | set(device_allowed.keys())
        for device_id in all_device_ids:
            blocked_key = f"dns:device_custom_blocked:{device_id}"
            allowed_key = f"dns:device_custom_allowed:{device_id}"
            await redis_client.delete(blocked_key)
            await redis_client.delete(allowed_key)

            blocked = device_blocked.get(device_id, [])
            allowed = device_allowed.get(device_id, [])
            if blocked:
                await redis_client.sadd(blocked_key, *blocked)
            if allowed:
                await redis_client.sadd(allowed_key, *allowed)

        logger.info(
            f"Device custom rules Redis rebuild: "
            f"{len(all_device_ids)} cihaz, {len(rules)} kural yuklendi"
        )


# ===== API ENDPOINTLERI =====

@router.get("/", response_model=List[DeviceCustomRuleSummary])
async def list_device_custom_rules(
    device_id: int | None = Query(None, description="Cihaz ID filtresi"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum cihaz özel kurallarini listele (opsiyonel device_id filtresi)."""
    query = (
        select(DeviceCustomRule, Device)
        .join(Device, DeviceCustomRule.device_id == Device.id)
        .order_by(DeviceCustomRule.created_at.desc())
    )
    if device_id is not None:
        query = query.where(DeviceCustomRule.device_id == device_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        DeviceCustomRuleSummary(
            id=rule.id,
            device_id=rule.device_id,
            device_hostname=device.hostname,
            device_ip=device.ip_address,
            domain=rule.domain,
            rule_type=rule.rule_type.value,
            reason=rule.reason,
            added_by=rule.added_by,
            created_at=rule.created_at,
        )
        for rule, device in rows
    ]


@router.post("/devices/{device_id}", response_model=DeviceCustomRuleSummary, status_code=201)
async def create_device_custom_rule(
    device_id: int,
    data: DeviceCustomRuleCreate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihaz için özel DNS kuralı ekle."""
    # Cihaz var mi?
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    # rule_type dogrula
    try:
        rule_type = DeviceCustomRuleType(data.rule_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="rule_type 'block' veya 'allow' olmali")

    domain = data.domain.lower().strip()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain bos olamaz")

    # Ayni cihaz+domain kontrolü
    existing = await db.scalar(
        select(DeviceCustomRule).where(
            DeviceCustomRule.device_id == device_id,
            DeviceCustomRule.domain == domain,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Bu cihaz için '{domain}' kuralı zaten mevcut"
        )

    rule = DeviceCustomRule(
        device_id=device_id,
        domain=domain,
        rule_type=rule_type,
        reason=data.reason,
        added_by="user",
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    # Redis sync
    await sync_device_custom_rules_to_redis(device_id, db, redis)

    logger.info(f"Cihaz özel kural eklendi: device={device_id} domain={domain} type={rule_type.value}")
    return DeviceCustomRuleSummary(
        id=rule.id,
        device_id=rule.device_id,
        device_hostname=device.hostname,
        device_ip=device.ip_address,
        domain=rule.domain,
        rule_type=rule.rule_type.value,
        reason=rule.reason,
        added_by=rule.added_by,
        created_at=rule.created_at,
    )


@router.put("/{rule_id}", response_model=DeviceCustomRuleSummary)
async def update_device_custom_rule(
    rule_id: int,
    data: DeviceCustomRuleUpdate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihaz özel kuralıni güncelle (domain, rule_type, reason)."""
    rule = await db.get(DeviceCustomRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Kural bulunamadı")

    # Cihaz bilgisi (response için)
    device = await db.get(Device, rule.device_id)

    if data.domain is not None:
        new_domain = data.domain.lower().strip()
        if not new_domain:
            raise HTTPException(status_code=400, detail="Domain bos olamaz")
        # Ayni cihazda baska bir kural ayni domain'e sahip mi?
        if new_domain != rule.domain:
            existing = await db.scalar(
                select(DeviceCustomRule).where(
                    DeviceCustomRule.device_id == rule.device_id,
                    DeviceCustomRule.domain == new_domain,
                )
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Bu cihaz için '{new_domain}' kuralı zaten mevcut"
                )
        rule.domain = new_domain

    if data.rule_type is not None:
        try:
            rule.rule_type = DeviceCustomRuleType(data.rule_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="rule_type 'block' veya 'allow' olmali")

    if data.reason is not None:
        rule.reason = data.reason

    await db.flush()
    await db.refresh(rule)

    # Redis sync
    await sync_device_custom_rules_to_redis(rule.device_id, db, redis)

    logger.info(f"Cihaz özel kural güncellendi: id={rule_id} device={rule.device_id} domain={rule.domain}")
    return DeviceCustomRuleSummary(
        id=rule.id,
        device_id=rule.device_id,
        device_hostname=device.hostname if device else None,
        device_ip=device.ip_address if device else None,
        domain=rule.domain,
        rule_type=rule.rule_type.value,
        reason=rule.reason,
        added_by=rule.added_by,
        created_at=rule.created_at,
    )


@router.delete("/{rule_id}", status_code=204)
async def delete_device_custom_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    """Cihaz özel kuralıni sil."""
    rule = await db.get(DeviceCustomRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Kural bulunamadı")

    device_id = rule.device_id
    domain = rule.domain
    await db.delete(rule)
    await db.flush()

    # Redis sync
    await sync_device_custom_rules_to_redis(device_id, db, redis)

    logger.info(f"Cihaz özel kural silindi: device={device_id} domain={domain}")

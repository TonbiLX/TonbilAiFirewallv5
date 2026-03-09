# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# IP Yönetimi API: Güvenilir IP ve Engellenen IP CRUD işlemleri.
# Güvenilir IP'ler threat_analyzer'in TRUSTED_IPS set'ine senkronize edilir.
# Engellenen IP'ler hem DB'de (kalici) hem Redis'te (DNS proxy uyumlu) tutulur.

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from typing import List
from datetime import datetime, timedelta, timezone
import logging

from app.db.session import get_db
from app.models.trusted_ip import TrustedIp
from app.models.blocked_ip import BlockedIp
from app.schemas.trusted_ip import TrustedIpCreate, TrustedIpResponse
from app.schemas.blocked_ip import (
    BlockedIpCreate, BlockedIpResponse, BlockedIpUnblock,
    BlockedIpUpdateDuration, IpManagementStats,
    BlockedIpBulkUnblock, BlockedIpBulkUpdateDuration, BulkOperationResult,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.ip_management")


# ===== ISTATISTIKLER =====

@router.get("/stats", response_model=IpManagementStats)
async def ip_management_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """IP yönetimi istatistikleri."""
    trusted_count = await db.scalar(select(sa_func.count(TrustedIp.id))) or 0
    blocked_total = await db.scalar(select(sa_func.count(BlockedIp.id))) or 0
    manual_count = await db.scalar(
        select(sa_func.count(BlockedIp.id)).where(BlockedIp.is_manual == True)
    ) or 0

    # Redis'teki auto-blocked IP'leri de say
    from app.workers.threat_analyzer import get_blocked_ips
    redis_blocked = await get_blocked_ips()

    return {
        "trusted_ip_count": trusted_count,
        "blocked_ip_count": blocked_total + len(redis_blocked),
        "manual_block_count": manual_count,
        "auto_block_count": len(redis_blocked),
    }


# ===== GUVENILIR IP CRUD =====

@router.get("/trusted", response_model=List[TrustedIpResponse])
async def list_trusted_ips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Güvenilir IP listesi."""
    result = await db.execute(
        select(TrustedIp).order_by(TrustedIp.created_at.desc())
    )
    return result.scalars().all()


@router.post("/trusted", response_model=TrustedIpResponse, status_code=201)
async def add_trusted_ip(
    data: TrustedIpCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Güvenilir IP ekle ve threat_analyzer'a bildir."""
    # Zaten var mi kontrol et
    existing = await db.scalar(
        select(TrustedIp).where(TrustedIp.ip_address == data.ip_address)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Bu IP zaten guvenilir listesinde")

    trusted = TrustedIp(**data.model_dump())
    db.add(trusted)
    await db.flush()
    await db.refresh(trusted)

    # Threat analyzer'in in-memory set'ini güncelle
    await _sync_trusted_ips_to_analyzer(db)

    logger.info(f"Güvenilir IP eklendi: {data.ip_address}")
    return trusted


@router.delete("/trusted/{trusted_id}", status_code=204)
async def delete_trusted_ip(
    trusted_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Güvenilir IP sil."""
    trusted = await db.get(TrustedIp, trusted_id)
    if not trusted:
        raise HTTPException(status_code=404, detail="Güvenilir IP bulunamadı")

    ip_addr = trusted.ip_address
    await db.delete(trusted)
    await db.flush()

    # Threat analyzer'i güncelle
    await _sync_trusted_ips_to_analyzer(db)

    logger.info(f"Güvenilir IP silindi: {ip_addr}")


# ===== ENGELLENEN IP CRUD =====

def _calc_remaining(expires_at) -> int | None:
    """expires_at'ten kalan sureyi saniye cinsinden hesapla."""
    if expires_at is None:
        return None
    now = datetime.now(timezone.utc)
    # expires_at naive ise UTC kabul et
    if expires_at.tzinfo is None:
        exp = expires_at.replace(tzinfo=timezone.utc)
    else:
        exp = expires_at
    remaining = (exp - now).total_seconds()
    return max(int(remaining), 0)


@router.get("/blocked", response_model=List[BlockedIpResponse])
async def list_blocked_ips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Engellenen IP listesi (DB + Redis birlestirmesi)."""
    now = datetime.now(timezone.utc)

    # 1. DB'deki engeller
    result = await db.execute(
        select(BlockedIp).order_by(BlockedIp.blocked_at.desc())
    )
    db_blocked = result.scalars().all()

    # 2. Redis'teki gecici engeller (auto-blocked)
    from app.workers.threat_analyzer import get_blocked_ips
    redis_blocked = await get_blocked_ips()

    # DB kayitlarinin IP'lerini set olarak tut (cakisma onleme)
    db_ips = {b.ip_address for b in db_blocked}

    # Birlestir: DB kayitlarini don, süresi dolanlari filtrele
    combined: list[BlockedIpResponse] = []
    expired_ids: list[int] = []

    for b in db_blocked:
        remaining = _calc_remaining(b.expires_at)
        # Süresi dolmus — temizle
        if remaining is not None and remaining <= 0:
            expired_ids.append(b.id)
            continue
        combined.append(BlockedIpResponse(
            id=b.id,
            ip_address=b.ip_address,
            reason=b.reason,
            blocked_at=b.blocked_at,
            expires_at=b.expires_at,
            is_manual=b.is_manual,
            source=b.source,
            remaining_seconds=remaining,
        ))

    # Süresi dolmus DB kayitlarini temizle
    if expired_ids:
        for eid in expired_ids:
            obj = await db.get(BlockedIp, eid)
            if obj:
                await db.delete(obj)
        await db.flush()
        logger.info(f"Süresi dolan {len(expired_ids)} IP engeli temizlendi")

    # Redis'ten gelen ama DB'de olmayanlari ekle
    for r in redis_blocked:
        if r["ip"] not in db_ips:
            combined.append(BlockedIpResponse(
                id=None,
                ip_address=r["ip"],
                reason=r["reason"],
                blocked_at=r.get("blocked_at"),
                expires_at=None,
                is_manual=False,
                source="threat_analyzer",
                remaining_seconds=r["remaining_seconds"],
            ))

    return combined


@router.post("/blocked", response_model=BlockedIpResponse, status_code=201)
async def add_blocked_ip(
    data: BlockedIpCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """IP'yi manuel olarak engelle (DB + Redis)."""
    # Güvenilir IP kontrolü
    trusted = await db.scalar(
        select(TrustedIp).where(TrustedIp.ip_address == data.ip_address)
    )
    if trusted:
        raise HTTPException(
            status_code=400,
            detail="Bu IP guvenilir listesinde. Engellemek için once guvenilir listesinden cikarin."
        )

    # Zaten engelli mi (DB)?
    existing = await db.scalar(
        select(BlockedIp).where(BlockedIp.ip_address == data.ip_address)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Bu IP zaten engelli")

    # expires_at hesapla
    expires_at = None
    ttl_seconds = None
    if data.duration_minutes is not None and data.duration_minutes > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=data.duration_minutes)
        ttl_seconds = data.duration_minutes * 60

    blocked = BlockedIp(
        ip_address=data.ip_address,
        reason=data.reason,
        expires_at=expires_at,
        is_manual=True,
        source="manual",
    )
    db.add(blocked)
    await db.flush()
    await db.refresh(blocked)

    # Redis'e de ekle (DNS proxy uyumlulugu)
    from app.workers.threat_analyzer import manual_block_ip
    await manual_block_ip(data.ip_address, data.reason, ttl_seconds=ttl_seconds)

    remaining = _calc_remaining(expires_at)
    logger.info(f"IP engellendi: {data.ip_address} - {data.reason} (sure: {data.duration_minutes or 'kalici'} dk)")
    return BlockedIpResponse(
        id=blocked.id,
        ip_address=blocked.ip_address,
        reason=blocked.reason,
        blocked_at=blocked.blocked_at,
        expires_at=blocked.expires_at,
        is_manual=blocked.is_manual,
        source=blocked.source,
        remaining_seconds=remaining,
    )


@router.put("/blocked/duration", response_model=BlockedIpResponse)
async def update_blocked_ip_duration(
    data: BlockedIpUpdateDuration,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """IP engelinin süresini değiştir (DB + Redis-only her iki tur için çalışır)."""
    from app.workers.threat_analyzer import update_block_ttl, is_ip_blocked

    # expires_at ve ttl hesapla
    if data.duration_minutes is not None and data.duration_minutes > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=data.duration_minutes)
        ttl_seconds = data.duration_minutes * 60
    else:
        expires_at = None
        ttl_seconds = None

    # DB'de var mi?
    blocked = await db.scalar(
        select(BlockedIp).where(BlockedIp.ip_address == data.ip_address)
    )

    if blocked:
        # DB kaydini güncelle
        blocked.expires_at = expires_at
        await db.flush()
        await db.refresh(blocked)
        await update_block_ttl(blocked.ip_address, ttl_seconds)

        remaining = _calc_remaining(blocked.expires_at)
        logger.info(f"IP engel süresi güncellendi: {blocked.ip_address} -> {data.duration_minutes or 'kalici'} dk")
        return BlockedIpResponse(
            id=blocked.id,
            ip_address=blocked.ip_address,
            reason=blocked.reason,
            blocked_at=blocked.blocked_at,
            expires_at=blocked.expires_at,
            is_manual=blocked.is_manual,
            source=blocked.source,
            remaining_seconds=remaining,
        )

    # DB'de yok — Redis-only (otomatik engel). Redis TTL'i güncelle.
    redis_updated = await update_block_ttl(data.ip_address, ttl_seconds)
    if not redis_updated:
        raise HTTPException(status_code=404, detail="Engellenen IP bulunamadı")

    remaining = ttl_seconds if ttl_seconds else None
    logger.info(f"Redis IP engel süresi güncellendi: {data.ip_address} -> {data.duration_minutes or 'kalici'} dk")
    return BlockedIpResponse(
        id=None,
        ip_address=data.ip_address,
        reason=None,
        blocked_at=None,
        expires_at=expires_at,
        is_manual=False,
        source="threat_analyzer",
        remaining_seconds=remaining,
    )


@router.post("/unblock")
async def unblock_ip(
    data: BlockedIpUnblock,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """IP engelini kaldir (DB + Redis)."""
    # DB'den sil
    existing = await db.scalar(
        select(BlockedIp).where(BlockedIp.ip_address == data.ip_address)
    )
    if existing:
        await db.delete(existing)
        await db.flush()

    # Redis'ten de kaldir
    from app.workers.threat_analyzer import manual_unblock_ip
    redis_removed = await manual_unblock_ip(data.ip_address)

    if existing or redis_removed:
        logger.info(f"IP engeli kaldırıldı: {data.ip_address}")
        return {"status": "ok", "message": f"{data.ip_address} engeli kaldırıldı."}
    raise HTTPException(status_code=404, detail="Bu IP engelli degil.")


# ===== TOPLU ISLEMLER =====

@router.put("/blocked/bulk-unblock", response_model=BulkOperationResult)
async def bulk_unblock_ips(
    data: BlockedIpBulkUnblock,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Birden fazla IP'nin engelini toplu kaldir."""
    from app.workers.threat_analyzer import manual_unblock_ip

    success = 0
    failed_ips: list[str] = []

    for ip in data.ip_addresses:
        try:
            # DB'den sil
            existing = await db.scalar(
                select(BlockedIp).where(BlockedIp.ip_address == ip)
            )
            if existing:
                await db.delete(existing)
                await db.flush()

            # Redis'ten de kaldir
            await manual_unblock_ip(ip)

            logger.info(f"[Toplu] IP engeli kaldırıldı: {ip}")
            success += 1
        except Exception as e:
            logger.warning(f"[Toplu] IP engel kaldirma hatasi {ip}: {e}")
            failed_ips.append(ip)

    return BulkOperationResult(
        success_count=success,
        failed_count=len(failed_ips),
        failed_ips=failed_ips,
    )


@router.put("/blocked/bulk-duration", response_model=BulkOperationResult)
async def bulk_update_duration(
    data: BlockedIpBulkUpdateDuration,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Birden fazla IP'nin engel suresini toplu guncelle."""
    from app.workers.threat_analyzer import update_block_ttl

    # expires_at ve ttl hesapla
    if data.duration_minutes is not None and data.duration_minutes > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=data.duration_minutes)
        ttl_seconds = data.duration_minutes * 60
    else:
        expires_at = None
        ttl_seconds = None

    success = 0
    failed_ips: list[str] = []

    for ip in data.ip_addresses:
        try:
            # DB'de var mi?
            blocked = await db.scalar(
                select(BlockedIp).where(BlockedIp.ip_address == ip)
            )
            if blocked:
                blocked.expires_at = expires_at
                await db.flush()

            # Redis TTL guncelle (DB kaydı olsun ya da olmasin)
            await update_block_ttl(ip, ttl_seconds)

            logger.info(f"[Toplu] IP engel suresi güncellendi: {ip} -> {data.duration_minutes or 'kalici'} dk")
            success += 1
        except Exception as e:
            logger.warning(f"[Toplu] IP sure guncelleme hatasi {ip}: {e}")
            failed_ips.append(ip)

    return BulkOperationResult(
        success_count=success,
        failed_count=len(failed_ips),
        failed_ips=failed_ips,
    )


# ===== YARDIMCI FONKSIYONLAR =====

async def _sync_trusted_ips_to_analyzer(db: AsyncSession):
    """DB'deki guvenilir IP'leri threat_analyzer'in TRUSTED_IPS set'ine senkronize et.
    Ayrica Redis'teki engel listesinden guvenilir IP'leri temizle.
    """
    from app.workers.threat_analyzer import TRUSTED_IPS, _load_trusted_ips, _get_redis

    # Öncelikle dosyadan varsayilan degerler yukle
    _load_trusted_ips()

    # DB'deki IP'leri ekle
    result = await db.execute(select(TrustedIp.ip_address))
    db_ips = {row[0] for row in result.all()}
    TRUSTED_IPS.update(db_ips)
    logger.info(f"Güvenilir IP senkronizasyonu: {len(TRUSTED_IPS)} IP (DB: {len(db_ips)})")

    # Redis'teki engel listesinden guvenilir IP'leri temizle
    try:
        redis = await _get_redis()
        for ip in TRUSTED_IPS:
            removed = await redis.srem("dns:threat:blocked", ip)
            if removed:
                await redis.delete(f"dns:threat:block_expire:{ip}")
                logger.info(f"Güvenilir IP Redis engel listesinden temizlendi: {ip}")
    except Exception as e:
        logger.warning(f"Redis guvenilir IP temizleme hatasi: {e}")


async def sync_trusted_ips_on_startup():
    """Uygulama başlatildiginda DB'deki guvenilir IP'leri yukle.
    main.py lifespan'dan cagirilir.
    Ayrica Redis'teki engel listesinden guvenilir IP'leri temizler.
    """
    from app.db.session import async_session_factory
    from app.workers.threat_analyzer import TRUSTED_IPS, _load_trusted_ips, _get_redis

    _load_trusted_ips()  # Dosya/varsayilan degerler

    try:
        async with async_session_factory() as session:
            result = await session.execute(select(TrustedIp.ip_address))
            db_ips = {row[0] for row in result.all()}
            TRUSTED_IPS.update(db_ips)
            logger.info(f"Başlangic guvenilir IP yükleme: {len(TRUSTED_IPS)} IP (DB: {len(db_ips)})")
    except Exception as e:
        logger.warning(f"Güvenilir IP başlangıç yükleme hatasi (tablo henüz yok olabilir): {e}")

    # Redis'teki engel listesinden guvenilir IP'leri temizle
    try:
        redis = await _get_redis()
        for ip in TRUSTED_IPS:
            removed = await redis.srem("dns:threat:blocked", ip)
            if removed:
                await redis.delete(f"dns:threat:block_expire:{ip}")
                logger.info(f"Başlangic: Güvenilir IP Redis engelinden temizlendi: {ip}")
    except Exception as e:
        logger.warning(f"Başlangic Redis guvenilir IP temizleme hatasi: {e}")

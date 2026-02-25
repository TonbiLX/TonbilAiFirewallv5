# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DNS Engelleme API endpointleri: blocklist CRUD, kural yönetimi, istatistikler.
# Pi-hole / AdGuard tarzi DNS sinkhole yönetimi.
# Yeni: Blocklist refresh endpoint'leri ve güncelleme istatistikleri.

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.api.deps import get_driver_dep, get_current_user, escape_like
from app.models.user import User
from app.models.blocklist import Blocklist
from app.models.dns_rule import DnsRule, DnsRuleType
from app.models.dns_query_log import DnsQueryLog
from app.schemas.blocklist import (
    BlocklistCreate, BlocklistUpdate, BlocklistResponse,
    BlocklistRefreshResponse, BulkRefreshResponse,
)
from app.schemas.dns_rule import DnsRuleCreate, DnsRuleResponse
from app.schemas.dns_query_log import DnsQueryLogResponse, DnsStatsResponse
from app.hal.base_driver import BaseNetworkDriver

logger = logging.getLogger("tonbilai.api.dns")
_DOMAIN_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$")
router = APIRouter()


# ===== BLOCKLIST ENDPOINTLERI =====

@router.get("/blocklists", response_model=List[BlocklistResponse])
async def list_blocklists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum blocklist kaynaklarini listele."""
    result = await db.execute(select(Blocklist).order_by(Blocklist.id))
    return result.scalars().all()


@router.post("/blocklists", response_model=BlocklistResponse, status_code=201)
async def create_blocklist(
    data: BlocklistCreate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Yeni blocklist kaynagi ekle. URL'den gercek indirme yapar."""
    from app.workers.blocklist_worker import (
        fetch_and_parse_blocklist, rebuild_blocked_domains_set,
        save_domains_to_cache,
    )

    dump = data.model_dump()

    # Format belirtilmediyse domain_list varsay (otomatik algilanacak)
    if dump.get("format") in (None, "auto"):
        dump["format"] = "domain_list"

    blocklist = Blocklist(**dump)
    db.add(blocklist)
    await db.flush()

    # URL'den gercek indirme yap ve domain sayısıni hesapla
    try:
        domains, content_hash = await fetch_and_parse_blocklist(blocklist)
        save_domains_to_cache(blocklist.id, domains)
        blocklist.domain_count = len(domains)
        blocklist.content_hash = content_hash
        blocklist.last_updated = datetime.utcnow()
        blocklist.last_error = None
        await db.flush()
    except Exception as e:
        blocklist.last_error = str(e)
        blocklist.domain_count = 0
        await db.flush()

    await db.refresh(blocklist)

    # Redis engelleme setini güncelle (cache'den okur - hizli)
    try:
        await rebuild_blocked_domains_set(driver)
    except Exception as e:
        logger.warning(f"Redis engelleme seti güncelleme hatasi (create): {e}")

    return blocklist


@router.patch("/blocklists/{blocklist_id}", response_model=BlocklistResponse)
async def update_blocklist(
    blocklist_id: int,
    data: BlocklistUpdate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Blocklist kaynagini güncelle. URL degismisse yeniden indir."""
    from app.workers.blocklist_worker import (
        fetch_and_parse_blocklist, rebuild_blocked_domains_set,
        save_domains_to_cache,
    )

    blocklist = await db.get(Blocklist, blocklist_id)
    if not blocklist:
        raise HTTPException(status_code=404, detail="Blocklist bulunamadı")

    update_data = data.model_dump(exclude_unset=True)
    url_changed = "url" in update_data and update_data["url"] != blocklist.url

    for key, value in update_data.items():
        setattr(blocklist, key, value)

    # URL degismisse otomatik yeniden indir
    if url_changed and blocklist.url:
        try:
            domains, content_hash = await fetch_and_parse_blocklist(blocklist)
            save_domains_to_cache(blocklist.id, domains)
            blocklist.domain_count = len(domains)
            blocklist.content_hash = content_hash
            blocklist.last_updated = datetime.utcnow()
            blocklist.last_error = None
        except Exception as e:
            blocklist.last_error = str(e)
            blocklist.domain_count = 0

        # Redis güncelle (cache'den okur - hizli)
        try:
            await rebuild_blocked_domains_set(driver)
        except Exception as e:
            logger.warning(f"Redis engelleme seti güncelleme hatasi (update): {e}")

    await db.flush()
    await db.refresh(blocklist)
    return blocklist


@router.delete("/blocklists/{blocklist_id}", status_code=204)
async def delete_blocklist(
    blocklist_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Blocklist kaynagini sil ve Redis engelleme setini güncelle."""
    from app.workers.blocklist_worker import rebuild_blocked_domains_set, delete_domain_cache

    blocklist = await db.get(Blocklist, blocklist_id)
    if not blocklist:
        raise HTTPException(status_code=404, detail="Blocklist bulunamadı")
    bl_id = blocklist.id
    await db.delete(blocklist)
    await db.commit()  # Commit BEFORE rebuild (rebuild opens new session)

    # Cache dosyasini sil
    delete_domain_cache(bl_id)

    # Redis engelleme setini yeniden oluştur (cache'den okur - hizli)
    try:
        await rebuild_blocked_domains_set(driver)
    except Exception as e:
        logger.warning(f"Redis engelleme seti güncelleme hatasi (delete): {e}")


@router.post("/blocklists/{blocklist_id}/toggle")
async def toggle_blocklist(
    blocklist_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Blocklist kaynagini etkinlestir/devre disi birak."""
    from app.workers.blocklist_worker import rebuild_blocked_domains_set

    blocklist = await db.get(Blocklist, blocklist_id)
    if not blocklist:
        raise HTTPException(status_code=404, detail="Blocklist bulunamadı")
    blocklist.enabled = not blocklist.enabled
    new_enabled = blocklist.enabled
    await db.commit()  # Commit BEFORE rebuild (rebuild opens new session)

    # Redis engelleme setini yeniden oluştur (cache'den okur - hizli)
    try:
        await rebuild_blocked_domains_set(driver)
    except Exception as e:
        logger.warning(f"Redis engelleme seti güncelleme hatasi (toggle): {e}")

    return {"id": blocklist_id, "enabled": new_enabled}


# ===== BLOCKLIST GUNCELLEME (REFRESH) ENDPOINTLERI =====

@router.post(
    "/blocklists/{blocklist_id}/refresh",
    response_model=BlocklistRefreshResponse,
)
async def refresh_blocklist(
    blocklist_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Tek bir blocklist'i URL'den yeniden indir ve istatistik dondur."""
    from app.workers.blocklist_worker import (
        refresh_single_blocklist, rebuild_blocked_domains_set,
    )

    blocklist = await db.get(Blocklist, blocklist_id)
    if not blocklist:
        raise HTTPException(status_code=404, detail="Blocklist bulunamadı")

    result = await refresh_single_blocklist(blocklist, db, driver)
    await db.flush()

    # Redis engelleme setini yeniden oluştur
    try:
        await rebuild_blocked_domains_set(driver)
    except Exception as e:
        logger.warning(f"Redis engelleme seti güncelleme hatasi (refresh): {e}")

    return BlocklistRefreshResponse(**result)


@router.post("/blocklists/refresh-all", response_model=BulkRefreshResponse)
async def refresh_all_blocklists_endpoint(
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Tum aktif blocklist'leri güncelle ve toplu istatistik dondur."""
    from app.workers.blocklist_worker import refresh_all_blocklists

    summary = await refresh_all_blocklists(driver)
    return BulkRefreshResponse(
        total_blocklists=summary["total_blocklists"],
        updated_count=summary["updated_count"],
        unchanged_count=summary["unchanged_count"],
        failed_count=summary["failed_count"],
        total_domains_before=summary["total_domains_before"],
        total_domains_after=summary["total_domains_after"],
        new_domains_added=summary["new_domains_added"],
        results=[BlocklistRefreshResponse(**r) for r in summary["results"]],
    )


# ===== DNS KURAL ENDPOINTLERI =====

@router.get("/rules", response_model=List[DnsRuleResponse])
async def list_dns_rules(
    rule_type: Optional[str] = None,
    profile_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DNS kurallarini listele (opsiyonel filtreleme)."""
    query = select(DnsRule).order_by(desc(DnsRule.created_at))
    if rule_type:
        query = query.where(DnsRule.rule_type == rule_type)
    if profile_id is not None:
        query = query.where(DnsRule.profile_id == profile_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/rules", response_model=DnsRuleResponse, status_code=201)
async def create_dns_rule(
    data: DnsRuleCreate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Yeni DNS kuralı ekle (domain engelle veya izin ver)."""
    rule = DnsRule(**data.model_dump(), added_by="user")
    db.add(rule)
    if data.rule_type == "block":
        await driver.add_blocked_domain(data.domain)
    elif data.rule_type == "allow":
        await driver.remove_blocked_domain(data.domain)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_dns_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """DNS kuralıni sil."""
    rule = await db.get(DnsRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Kural bulunamadı")
    if rule.rule_type == DnsRuleType.BLOCK:
        await driver.remove_blocked_domain(rule.domain)
    await db.delete(rule)


# ===== DNS SORGU LOG ENDPOINTLERI =====

@router.get("/queries", response_model=List[DnsQueryLogResponse])
async def list_dns_queries(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    blocked_only: bool = False,
    domain_search: Optional[str] = None,
    device_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DNS sorgu loglarını filtrele ve listele."""
    query = select(DnsQueryLog).order_by(desc(DnsQueryLog.timestamp))
    if blocked_only:
        query = query.where(DnsQueryLog.blocked == True)  # noqa: E712
    if domain_search:
        query = query.where(DnsQueryLog.domain.contains(escape_like(domain_search)))
    if device_id:
        query = query.where(DnsQueryLog.device_id == device_id)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ===== DNS ISTATISTIKLER =====

@router.get("/stats", response_model=DnsStatsResponse)
async def dns_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DNS engelleme istatistikleri (Pi-hole tarzi dashboard)."""
    now = datetime.now()
    day_ago = now - timedelta(hours=24)

    total_24h = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(DnsQueryLog.timestamp >= day_ago)
    ) or 0

    blocked_24h = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(
            and_(DnsQueryLog.timestamp >= day_ago, DnsQueryLog.blocked == True)  # noqa: E712
        )
    ) or 0

    active_lists = await db.scalar(
        select(func.count(Blocklist.id)).where(Blocklist.enabled == True)  # noqa: E712
    ) or 0

    total_bl_domains = await db.scalar(
        select(func.sum(Blocklist.domain_count)).where(Blocklist.enabled == True)  # noqa: E712
    ) or 0

    # Top engellenen domainler
    top_blocked_q = await db.execute(
        select(DnsQueryLog.domain, func.count(DnsQueryLog.id).label("count"))
        .where(and_(DnsQueryLog.timestamp >= day_ago, DnsQueryLog.blocked == True))  # noqa: E712
        .group_by(DnsQueryLog.domain)
        .order_by(desc("count"))
        .limit(10)
    )
    top_blocked = [{"domain": r[0], "count": r[1]} for r in top_blocked_q.all()]

    # Top sorgulanan domainler
    top_queried_q = await db.execute(
        select(DnsQueryLog.domain, func.count(DnsQueryLog.id).label("count"))
        .where(DnsQueryLog.timestamp >= day_ago)
        .group_by(DnsQueryLog.domain)
        .order_by(desc("count"))
        .limit(10)
    )
    top_queried = [{"domain": r[0], "count": r[1]} for r in top_queried_q.all()]

    # Top istemciler
    top_clients_q = await db.execute(
        select(
            DnsQueryLog.device_id,
            DnsQueryLog.client_ip,
            func.count(DnsQueryLog.id).label("query_count"),
        )
        .where(DnsQueryLog.timestamp >= day_ago)
        .group_by(DnsQueryLog.device_id, DnsQueryLog.client_ip)
        .order_by(desc("query_count"))
        .limit(10)
    )
    top_clients = [
        {"device_id": r[0], "client_ip": r[1], "query_count": r[2]}
        for r in top_clients_q.all()
    ]

    block_pct = round((blocked_24h / max(total_24h, 1)) * 100, 1)

    return DnsStatsResponse(
        total_queries_24h=total_24h,
        blocked_queries_24h=blocked_24h,
        block_percentage=block_pct,
        total_blocklist_domains=total_bl_domains,
        active_blocklists=active_lists,
        top_blocked_domains=top_blocked,
        top_queried_domains=top_queried,
        top_clients=top_clients,
    )


# ===== DOMAIN ARAMA =====

@router.get("/lookup/{domain}")
async def lookup_domain(
    domain: str,
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bir domainin engelli olup olmadigini kontrol et."""
    domain = domain.strip().lower()
    if not domain or len(domain) > 253 or not _DOMAIN_RE.match(domain):
        raise HTTPException(status_code=400, detail="Geçersiz domain formati")
    is_blocked = await driver.is_domain_blocked(domain)

    rule_result = await db.execute(
        select(DnsRule).where(DnsRule.domain == domain)
    )
    custom_rule = rule_result.scalar_one_or_none()

    recent_count = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(DnsQueryLog.domain == domain)
    ) or 0

    return {
        "domain": domain,
        "is_blocked": is_blocked,
        "custom_rule": {
            "type": custom_rule.rule_type.value if custom_rule else None,
            "reason": custom_rule.reason if custom_rule else None,
        } if custom_rule else None,
        "recent_query_count": recent_count,
    }


@router.get("/blockpage")
async def get_block_page_info(
    domain: str = Query(..., min_length=1, max_length=253),
):
    """Engellenen domain hakkinda bilgi don (block page icin).
    Auth gerektirmez - block page'den cagirilir."""
    from app.db.redis_client import get_redis

    domain = domain.strip().lower()
    reason = "blocklist"
    reason_tr = "Engelleme listesi"

    try:
        redis_client = await get_redis()
        stored_reason = await redis_client.get(f"dns:block_info:{domain}")
        if stored_reason:
            reason = stored_reason
    except Exception:
        pass

    # Sebep cevirisi
    reason_map = {
        "blocklist": "Engelleme listesi (reklam/izleyici/zararli)",
        "device_custom_rule": "Cihaza ozel engelleme kurali",
        "query_type_block": "Yasakli DNS sorgu tipi",
        "reputation_block": "Dusuk itibar puani (zararli site)",
        "device_blocked": "Cihaz internet erisimi engellendi",
    }
    if reason.startswith("service:"):
        reason_tr = "Servis bazli engelleme"
    else:
        reason_tr = reason_map.get(reason, reason)

    return {
        "domain": domain,
        "blocked": True,
        "reason": reason,
        "reason_tr": reason_tr,
        "firewall": "TonbilAiOS",
    }

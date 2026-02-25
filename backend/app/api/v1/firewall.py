# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Firewall API endpointleri: port yönetimi, kural CRUD, port tarama.

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_driver_dep
from app.api.deps import get_current_user
from app.models.user import User
from app.models.firewall_rule import FirewallRule, FirewallDirection
from app.schemas.firewall_rule import (
    FirewallRuleCreate, FirewallRuleUpdate, FirewallRuleResponse,
    PortScanResult, FirewallStatsResponse,
)
from app.hal.base_driver import BaseNetworkDriver

router = APIRouter()


# ===== FIREWALL KURAL CRUD =====

@router.get("/rules", response_model=List[FirewallRuleResponse])
async def list_firewall_rules(
    direction: Optional[str] = None,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum firewall kurallarini listele."""
    query = select(FirewallRule).order_by(FirewallRule.priority, FirewallRule.id)
    if direction:
        query = query.where(FirewallRule.direction == direction)
    if enabled_only:
        query = query.where(FirewallRule.enabled == True)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/rules", response_model=FirewallRuleResponse, status_code=201)
async def create_firewall_rule(
    data: FirewallRuleCreate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Yeni firewall kuralı ekle."""
    rule = FirewallRule(**data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    if rule.enabled:
        await driver.add_port_rule(data.model_dump())
    return rule


@router.patch("/rules/{rule_id}", response_model=FirewallRuleResponse)
async def update_firewall_rule(
    rule_id: int,
    data: FirewallRuleUpdate,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Firewall kuralıni güncelle."""
    rule = await db.get(FirewallRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Kural bulunamadı")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_firewall_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Firewall kuralıni sil."""
    rule = await db.get(FirewallRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Kural bulunamadı")
    await driver.remove_port_rule(str(rule_id))
    await db.delete(rule)


@router.post("/rules/{rule_id}/toggle")
async def toggle_firewall_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Firewall kuralıni etkinlestir/devre disi birak."""
    rule = await db.get(FirewallRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Kural bulunamadı")
    rule.enabled = not rule.enabled
    if rule.enabled:
        await driver.add_port_rule({
            "port": rule.port, "protocol": rule.protocol.value if hasattr(rule.protocol, 'value') else rule.protocol,
            "action": rule.action.value if hasattr(rule.action, 'value') else rule.action,
            "direction": rule.direction.value if hasattr(rule.direction, 'value') else rule.direction,
        })
    else:
        await driver.remove_port_rule(str(rule_id))
    await db.flush()
    return {"id": rule_id, "enabled": rule.enabled}


# ===== PORT TARAMA =====

@router.get("/scan")
async def scan_ports(
    target_ip: str = Query(default="192.168.1.1", description="Hedef IP"),
    port_range: str = Query(default="1-1024", description="Port aralığı"),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Port taramasi yap (mock modda simule edilir)."""
    import ipaddress as _ipa
    import re as _re
    # IP doğrulama
    try:
        _ipa.ip_address(target_ip)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz IP adresi")
    # Sadece yerel ag taranabilir
    if not target_ip.startswith(("192.168.", "10.", "172.")):
        raise HTTPException(status_code=400, detail="Sadece yerel ag IP adresleri taranabilir")
    # Port range doğrulama
    if not _re.match(r'^\d{1,5}-\d{1,5}$', port_range):
        raise HTTPException(status_code=400, detail="Geçersiz port aralığı (örnek: 1-1024)")
    results = await driver.scan_ports(target_ip, port_range)
    return {
        "target": target_ip,
        "port_range": port_range,
        "results": results,
        "open_count": sum(1 for r in results if r["state"] == "open"),
        "closed_count": sum(1 for r in results if r["state"] == "closed"),
        "filtered_count": sum(1 for r in results if r["state"] == "filtered"),
    }


# ===== AKTIF BAGLANTILAR =====

@router.get("/connections")
async def active_connections(
    limit: int = Query(default=200, ge=1, le=500),
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    protocol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Aktif bağlantılari listele (conntrack'ten)."""
    from app.hal import linux_nftables as nft
    from app.db.redis_client import get_redis

    all_conns = await nft.get_active_connections()
    redis_client = await get_redis()

    # Filtreleme
    filtered = []
    for conn in all_conns:
        if src_ip and conn["src_ip"] != src_ip:
            continue
        if dst_ip and conn["dst_ip"] != dst_ip:
            continue
        if protocol and conn["protocol"] != protocol.upper():
            continue
        filtered.append(conn)

    # Domain cozumleme (ilk N bağlantı için)
    conns_to_show = filtered[:limit]
    dst_ips = list({c["dst_ip"] for c in conns_to_show})

    if dst_ips:
        pipe = redis_client.pipeline(transaction=False)
        for ip in dst_ips:
            pipe.get(f"dns:ip_to_domain:{ip}")
        domain_results = await pipe.execute()
        domain_map = dict(zip(dst_ips, domain_results))
    else:
        domain_map = {}

    for conn in conns_to_show:
        conn["dst_domain"] = domain_map.get(conn["dst_ip"]) or None

    return {
        "total": len(filtered),
        "showing": len(conns_to_show),
        "connections": conns_to_show,
    }


@router.get("/connections/count")
async def connection_count(
    current_user: User = Depends(get_current_user),
):
    """Aktif ve maksimum bağlantı sayısı."""
    from app.hal import linux_nftables as nft
    return await nft.get_connection_count()


# ===== ISTATISTIKLER =====

@router.get("/stats")
async def firewall_stats(
    db: AsyncSession = Depends(get_db),
    driver: BaseNetworkDriver = Depends(get_driver_dep),
    current_user: User = Depends(get_current_user),
):
    """Firewall istatistikleri."""
    total = await db.scalar(select(func.count(FirewallRule.id))) or 0
    active = await db.scalar(
        select(func.count(FirewallRule.id)).where(FirewallRule.enabled == True)  # noqa: E712
    ) or 0
    inbound = await db.scalar(
        select(func.count(FirewallRule.id)).where(FirewallRule.direction == "inbound")
    ) or 0
    outbound = await db.scalar(
        select(func.count(FirewallRule.id)).where(FirewallRule.direction == "outbound")
    ) or 0

    hal_stats = await driver.get_firewall_stats()

    # Kural bazli hit count
    from app.hal import linux_nftables as nft
    hit_counts = await nft.get_rule_hit_counts()
    conn_count = await nft.get_connection_count()

    return {
        "total_rules": total,
        "active_rules": active,
        "inbound_rules": inbound,
        "outbound_rules": outbound,
        "blocked_packets_24h": hal_stats.get("blocked_packets_24h", 0),
        "open_ports": hal_stats.get("open_ports", []),
        "rule_hit_counts": hit_counts,
        "active_connections": conn_count["active"],
        "max_connections": conn_count["max"],
    }

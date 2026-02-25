# --- Ajan: ANALIST (THE ANALYST) ---
# AI Insight API endpointleri + Tehdit Yönetimi API.

import ipaddress
import re

from fastapi import APIRouter, Depends, Query, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional

# Domain format doğrulama (path traversal onleme)
_DOMAIN_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$")

from app.db.session import get_db
from app.models.ai_insight import AiInsight
from app.schemas.ai_insight import AiInsightResponse
from app.workers.threat_analyzer import (
    get_threat_stats, get_blocked_ips,
    manual_block_ip, manual_unblock_ip,
)

router = APIRouter()


# --- AI Insight Endpointleri ---

@router.get("/", response_model=List[AiInsightResponse])
async def list_insights(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    severity: Optional[str] = None,
    category: Optional[str] = None,
    show_dismissed: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI icgoruleri filtrele ve listele."""
    query = select(AiInsight).order_by(desc(AiInsight.timestamp))

    if not show_dismissed:
        query = query.where(AiInsight.is_dismissed == False)
    if severity:
        query = query.where(AiInsight.severity == severity)
    if category:
        query = query.where(AiInsight.category == category)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/critical-count")
async def critical_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Kritik uyari sayısıni dondur."""
    from sqlalchemy import func
    count = await db.scalar(
        select(func.count(AiInsight.id)).where(AiInsight.severity == "critical")
    )
    return {"critical_count": count or 0}


@router.post("/{insight_id}/dismiss")
async def dismiss_insight(
    insight_id: int, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Insight'i gormezden gel (dismiss)."""
    result = await db.execute(select(AiInsight).where(AiInsight.id == insight_id))
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight bulunamadı.")
    insight.is_dismissed = True
    await db.flush()
    return {"status": "ok", "message": f"Insight #{insight_id} gormezden gelindi."}


# --- Tehdit Yönetimi Endpointleri ---

class IpBlockRequest(BaseModel):
    ip: str
    reason: str = "Manuel engelleme"

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError("Geçersiz IP adresi")
        return v.strip()


class IpUnblockRequest(BaseModel):
    ip: str

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError("Geçersiz IP adresi")
        return v.strip()


@router.get("/threat-stats")
async def threat_stats(
    current_user: User = Depends(get_current_user),
):
    """Tehdit istatistiklerini dondur."""
    return await get_threat_stats()


@router.get("/blocked-ips")
async def blocked_ips(
    current_user: User = Depends(get_current_user),
):
    """Engellenen IP listesini dondur."""
    return await get_blocked_ips()


@router.post("/block-ip")
async def block_ip(
    data: IpBlockRequest,
    current_user: User = Depends(get_current_user),
):
    """IP'yi manuel olarak engelle."""
    success = await manual_block_ip(data.ip, data.reason)
    if success:
        return {"status": "ok", "message": f"{data.ip} engellendi."}
    return {"status": "error", "message": "IP engellenemedi."}


@router.post("/unblock-ip")
async def unblock_ip(
    data: IpUnblockRequest,
    current_user: User = Depends(get_current_user),
):
    """IP engelini kaldir."""
    success = await manual_unblock_ip(data.ip)
    if success:
        return {"status": "ok", "message": f"{data.ip} engeli kaldırıldı."}
    return {"status": "error", "message": "IP engeli kaldirilamadi veya zaten engelli degil."}


# --- Saatlik Trend Endpointi ---

@router.get("/hourly-trends")
async def hourly_trends(
    hours: int = Query(default=24, le=72, ge=1),
    current_user: User = Depends(get_current_user),
):
    """Son X saatlik DNS trend verilerini dondur."""
    from app.workers.threat_analyzer import get_hourly_trends
    data = await get_hourly_trends(hours)
    return {"hours": hours, "trends": data}


# --- Domain Reputation Endpointi ---

@router.get("/domain-reputation/{domain:path}")
async def check_domain_reputation(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Domain reputation skorunu sorgula.
    Returns: {"domain": str, "score": 0-100, "risk_level": str, "factors": list}
    """
    # Domain format doğrulama (path traversal / injection onleme)
    domain = domain.strip().lower()
    if not domain or len(domain) > 253 or not _DOMAIN_RE.match(domain):
        raise HTTPException(status_code=400, detail="Geçersiz domain formati")
    from app.services.domain_reputation import calculate_reputation
    result = await calculate_reputation(domain)
    return {"domain": domain, **result}

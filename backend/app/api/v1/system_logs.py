# --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
# Sistem Logları API: kapsamli log görüntüleme, filtreleme, sayfalama.
# Veri kaynagi: dns_query_logs LEFT JOIN devices + ai_insights
# 5651 Kanun Uyumu: CSV/JSON export, imza doğrulama endpoint'leri.

import csv
import hashlib
import io
import math
import os
import re

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_user, escape_like
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_, case
from typing import Optional
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.models.dns_query_log import DnsQueryLog
from app.models.traffic_log import TrafficLog
from app.models.device import Device
from app.models.ai_insight import AiInsight, Severity
from app.models.log_signature import LogSignature
from app.schemas.system_log import SystemLogEntry, SystemLogListResponse, SystemLogSummary

router = APIRouter()


@router.get("/", response_model=SystemLogListResponse)
async def list_system_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=10, le=100),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source_ip: Optional[str] = None,
    dest_ip: Optional[str] = None,
    domain_search: Optional[str] = None,
    action: Optional[str] = None,  # block / allow / query
    severity: Optional[str] = None,  # info / warning / critical
    category: Optional[str] = None,  # dns / ai / security
    search: Optional[str] = None,  # serbest metin arama
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sayfalanmis ve filtrelenmis sistem log listesi (DNS + Trafik)."""

    # Trafik loglarını atla mi?
    skip_traffic = (
        action == "block"
        or severity in ("critical", "warning")
        or category in ("security", "ai", "dns", "ddos")
    )
    skip_dns = (category in ("traffic", "ddos"))
    skip_insights = (category in ("traffic", "dns"))
    if action == "allow":
        skip_insights = True

    items = []
    dns_total = 0
    traffic_total = 0
    insight_total = 0

    # ============================================================
    # DNS QUERY LOGS
    # ============================================================
    if not skip_dns:
        dns_query = (
            select(
                DnsQueryLog.id,
                DnsQueryLog.timestamp,
                DnsQueryLog.client_ip,
                DnsQueryLog.domain,
                DnsQueryLog.query_type,
                DnsQueryLog.blocked,
                DnsQueryLog.block_reason,
                DnsQueryLog.answer_ip,
                DnsQueryLog.upstream_response_ms,
                Device.mac_address,
                Device.hostname,
            )
            .outerjoin(Device, DnsQueryLog.device_id == Device.id)
        )
        dns_count_query = (
            select(func.count(DnsQueryLog.id))
            .outerjoin(Device, DnsQueryLog.device_id == Device.id)
        )

        dns_filters = []
        if date_from:
            try:
                dns_filters.append(DnsQueryLog.timestamp >= datetime.fromisoformat(date_from))
            except ValueError:
                pass
        if date_to:
            try:
                dns_filters.append(DnsQueryLog.timestamp <= datetime.fromisoformat(date_to))
            except ValueError:
                pass
        if source_ip:
            dns_filters.append(DnsQueryLog.client_ip.contains(escape_like(source_ip)))
        if dest_ip:
            dns_filters.append(or_(
                DnsQueryLog.answer_ip.contains(escape_like(dest_ip)),
                DnsQueryLog.domain.contains(escape_like(dest_ip)),
            ))
        if domain_search:
            dns_filters.append(DnsQueryLog.domain.contains(escape_like(domain_search)))
        if action == "block":
            dns_filters.append(DnsQueryLog.blocked == True)  # noqa: E712
        elif action == "allow":
            dns_filters.append(DnsQueryLog.blocked == False)  # noqa: E712
        if severity == "critical":
            dns_filters.append(and_(
                DnsQueryLog.blocked == True,  # noqa: E712
                DnsQueryLog.block_reason.isnot(None),
            ))
        elif severity == "warning":
            dns_filters.append(DnsQueryLog.blocked == True)  # noqa: E712
        if category == "security":
            dns_filters.append(or_(
                DnsQueryLog.block_reason.contains("threat"),
                DnsQueryLog.block_reason.contains("flood"),
                DnsQueryLog.block_reason.contains("auto_block"),
            ))
        elif category == "ai":
            dns_filters.append(or_(
                DnsQueryLog.block_reason.contains("ai"),
                DnsQueryLog.block_reason.contains("dga"),
                DnsQueryLog.block_reason.contains("entropy"),
            ))
        if search:
            _s = escape_like(search)
            dns_filters.append(or_(
                DnsQueryLog.domain.contains(_s),
                DnsQueryLog.client_ip.contains(_s),
                DnsQueryLog.answer_ip.contains(_s),
                DnsQueryLog.block_reason.contains(_s),
                Device.hostname.contains(_s),
                Device.mac_address.contains(_s),
            ))

        if dns_filters:
            dns_query = dns_query.where(and_(*dns_filters))
            dns_count_query = dns_count_query.where(and_(*dns_filters))

        dns_total = await db.scalar(dns_count_query) or 0

        # Fetch: per_page * 2 for merge headroom
        dns_query = dns_query.order_by(desc(DnsQueryLog.timestamp))
        dns_query = dns_query.offset((page - 1) * per_page).limit(per_page * 2)
        dns_result = await db.execute(dns_query)
        dns_rows = dns_result.all()

        for row in dns_rows:
            act = "block" if row.blocked else "allow"
            cat = "dns"
            if row.block_reason:
                br = row.block_reason.lower()
                if any(k in br for k in ("threat", "flood", "auto_block")):
                    cat = "security"
                elif any(k in br for k in ("ai", "dga", "entropy")):
                    cat = "ai"
            sev = "info"
            if row.blocked:
                sev = "warning"
                if row.block_reason and any(
                    k in row.block_reason.lower()
                    for k in ("threat", "flood", "critical", "auto_block")
                ):
                    sev = "critical"

            items.append(SystemLogEntry(
                id=row.id,
                timestamp=row.timestamp,
                client_ip=row.client_ip,
                dest_ip=row.answer_ip,
                mac_address=row.mac_address,
                hostname=row.hostname,
                domain=row.domain,
                query_type=row.query_type or "A",
                action=act,
                category=cat,
                severity=sev,
                answer_ip=row.answer_ip,
                block_reason=row.block_reason,
                upstream_response_ms=row.upstream_response_ms,
                source_type="dns",
            ))

    # ============================================================
    # TRAFFIC LOGS
    # ============================================================
    if not skip_traffic:
        traffic_query = (
            select(
                TrafficLog.id,
                TrafficLog.timestamp,
                TrafficLog.destination_domain,
                TrafficLog.category,
                TrafficLog.bytes_sent,
                TrafficLog.bytes_received,
                TrafficLog.protocol,
                Device.mac_address,
                Device.hostname,
                Device.ip_address,
            )
            .outerjoin(Device, TrafficLog.device_id == Device.id)
        )
        traffic_count_query = (
            select(func.count(TrafficLog.id))
            .outerjoin(Device, TrafficLog.device_id == Device.id)
        )

        traffic_filters = []
        if date_from:
            try:
                traffic_filters.append(TrafficLog.timestamp >= datetime.fromisoformat(date_from))
            except ValueError:
                pass
        if date_to:
            try:
                traffic_filters.append(TrafficLog.timestamp <= datetime.fromisoformat(date_to))
            except ValueError:
                pass
        if domain_search:
            traffic_filters.append(TrafficLog.destination_domain.contains(escape_like(domain_search)))
        if search:
            _s = escape_like(search)
            traffic_filters.append(or_(
                TrafficLog.destination_domain.contains(_s),
                Device.hostname.contains(_s),
                Device.mac_address.contains(_s),
                Device.ip_address.contains(_s),
            ))

        if traffic_filters:
            traffic_query = traffic_query.where(and_(*traffic_filters))
            traffic_count_query = traffic_count_query.where(and_(*traffic_filters))

        traffic_total = await db.scalar(traffic_count_query) or 0

        traffic_query = traffic_query.order_by(desc(TrafficLog.timestamp))
        traffic_query = traffic_query.offset((page - 1) * per_page).limit(per_page * 2)
        traffic_result = await db.execute(traffic_query)
        traffic_rows = traffic_result.all()

        for row in traffic_rows:
            items.append(SystemLogEntry(
                id=row.id + 10_000_000,
                timestamp=row.timestamp,
                client_ip=row.ip_address,
                dest_ip=None,
                mac_address=row.mac_address,
                hostname=row.hostname,
                domain=row.destination_domain or "--",
                query_type=row.protocol or "TCP",
                action="allow",
                category="traffic",
                severity="info",
                answer_ip=None,
                block_reason=None,
                upstream_response_ms=None,
                bytes_total=(row.bytes_sent or 0) + (row.bytes_received or 0),
                source_type="traffic",
            ))

    # ============================================================
    # AI INSIGHTS (DDoS Olaylari + Güvenlik + AI Analiz)
    # ============================================================
    if not skip_insights:
        insight_query = select(AiInsight).where(AiInsight.is_dismissed == False)  # noqa: E712
        insight_count_query = select(func.count(AiInsight.id)).where(
            AiInsight.is_dismissed == False  # noqa: E712
        )

        insight_filters = []
        if date_from:
            try:
                insight_filters.append(AiInsight.timestamp >= datetime.fromisoformat(date_from))
            except ValueError:
                pass
        if date_to:
            try:
                insight_filters.append(AiInsight.timestamp <= datetime.fromisoformat(date_to))
            except ValueError:
                pass
        if search:
            insight_filters.append(AiInsight.message.contains(escape_like(search)))
        if domain_search:
            insight_filters.append(AiInsight.message.contains(escape_like(domain_search)))

        # Severity filtresi
        if severity == "critical":
            insight_filters.append(AiInsight.severity == Severity.CRITICAL)
        elif severity == "warning":
            insight_filters.append(AiInsight.severity == Severity.WARNING)

        # Kategori filtresi
        if category == "ddos":
            insight_filters.append(or_(
                AiInsight.message.contains("DDoS"),
                AiInsight.message.contains("[DDoS"),
            ))
        elif category == "security":
            insight_filters.append(AiInsight.category == "security")
        elif category == "ai":
            insight_filters.append(or_(
                AiInsight.category != "security",
                AiInsight.category.is_(None),
            ))

        # Action filtresi — "block" ise sadece DDoS insight'lari goster
        if action == "block":
            insight_filters.append(or_(
                AiInsight.message.contains("DDoS"),
                AiInsight.message.contains("[DDoS"),
            ))

        if insight_filters:
            insight_query = insight_query.where(and_(*insight_filters))
            insight_count_query = insight_count_query.where(and_(*insight_filters))

        insight_total = await db.scalar(insight_count_query) or 0

        insight_query = insight_query.order_by(desc(AiInsight.timestamp))
        insight_query = insight_query.offset((page - 1) * per_page).limit(per_page * 2)
        insight_result = await db.execute(insight_query)
        insight_rows = insight_result.scalars().all()

        for row in insight_rows:
            msg = row.message or ""
            is_ddos = any(k in msg for k in ("DDoS", "ddos", "[DDoS"))

            # Kategori: DDoS olaylari → "ddos", diger güvenlik → "security", geri kalan → "ai"
            cat = "ddos" if is_ddos else ("security" if row.category == "security" else "ai")

            sev = row.severity.value if isinstance(row.severity, Severity) else str(row.severity or "info")

            # Domain alanina okunabilir baslik
            if is_ddos:
                domain_label = "DDoS Koruma"
            elif "[LLM Analiz]" in msg:
                domain_label = "LLM Analiz"
            else:
                domain_label = "AI Insight"

            # DDoS mesajlarindan saldırgan bilgilerini parse et
            # Format: ... | Kaynak: 192.168.1.9 | MAC: aa:bb:cc:dd:ee:ff | Host: hostname
            attacker_ip = None
            attacker_mac = None
            attacker_host = None
            if is_ddos:
                ip_match = re.search(r'Kaynak:\s*([\d.]+)', msg)
                if ip_match:
                    attacker_ip = ip_match.group(1)
                mac_match = re.search(r'MAC:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', msg)
                if mac_match:
                    attacker_mac = mac_match.group(1)
                host_match = re.search(r'Host:\s*(\S+)', msg)
                if host_match and host_match.group(1) != '-':
                    attacker_host = host_match.group(1)

            items.append(SystemLogEntry(
                id=row.id + 20_000_000,
                timestamp=row.timestamp,
                client_ip=attacker_ip,
                dest_ip=None,
                mac_address=attacker_mac,
                hostname=attacker_host,
                domain=domain_label,
                query_type="DDoS" if is_ddos else "AI",
                action="block" if is_ddos else "query",
                category=cat,
                severity=sev,
                answer_ip=None,
                block_reason=msg,
                upstream_response_ms=None,
                source_type="insight",
            ))

    # Birlestir, timestamp'e göre sirala, sayfala
    items.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
    paginated = items[:per_page]

    total = dns_total + traffic_total + insight_total
    total_pages = max(1, math.ceil(total / per_page))

    return SystemLogListResponse(
        items=paginated,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/summary", response_model=SystemLogSummary)
async def system_log_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """30 gunluk özet istatistikler."""
    now = datetime.now()
    month_ago = now - timedelta(days=30)

    # DNS sorgu toplami (30g)
    dns_queries_30d = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(
            DnsQueryLog.timestamp >= month_ago
        )
    ) or 0

    # Engellenen (30g)
    blocked_30d = await db.scalar(
        select(func.count(DnsQueryLog.id)).where(
            and_(
                DnsQueryLog.timestamp >= month_ago,
                DnsQueryLog.blocked == True,  # noqa: E712
            )
        )
    ) or 0

    # AI insights (30g)
    ai_insights_30d = await db.scalar(
        select(func.count(AiInsight.id)).where(
            AiInsight.timestamp >= month_ago
        )
    ) or 0

    # Kritik (30g)
    critical_30d = await db.scalar(
        select(func.count(AiInsight.id)).where(
            and_(
                AiInsight.timestamp >= month_ago,
                AiInsight.severity == Severity.CRITICAL,
            )
        )
    ) or 0

    # Trafik loglari (30g)
    traffic_logs_30d = await db.scalar(
        select(func.count(TrafficLog.id)).where(
            TrafficLog.timestamp >= month_ago
        )
    ) or 0

    total_logs_30d = dns_queries_30d + ai_insights_30d + traffic_logs_30d

    return SystemLogSummary(
        total_logs_30d=total_logs_30d,
        dns_queries_30d=dns_queries_30d,
        blocked_30d=blocked_30d,
        ai_insights_30d=ai_insights_30d,
        critical_30d=critical_30d,
        traffic_logs_30d=traffic_logs_30d,
    )


# ==================== 5651 Kanun Uyumu: Export Endpoint'leri ====================

MAX_EXPORT_ROWS = 100_000
CSV_COLUMNS = [
    "timestamp", "client_ip", "mac_address", "hostname", "domain", "query_type",
    "blocked", "block_reason", "answer_ip", "destination_port", "wan_ip",
]


def _parse_date_param(value: str, is_end: bool = False) -> datetime:
    """Tarih parametresini parse et. Sadece tarih verilirse gun başına/sonuna cevir."""
    # Sadece tarih formati (YYYY-MM-DD, 10 karakter, T icermez)
    if len(value) == 10 and "T" not in value:
        try:
            d = date.fromisoformat(value)
            if is_end:
                return datetime.combine(d, datetime.max.time())
            return datetime.combine(d, datetime.min.time())
        except ValueError:
            pass
    # Tam datetime formati
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, f"Geçersiz tarih formati: {value} (YYYY-MM-DD veya ISO 8601)")


def _build_export_query(date_from: str, date_to: str, source_ip: str = None, domain_search: str = None):
    """Export endpoint'leri için ortak sorgu oluştur."""
    query = (
        select(
            DnsQueryLog.timestamp,
            DnsQueryLog.client_ip,
            DnsQueryLog.mac_address,
            DnsQueryLog.domain,
            DnsQueryLog.query_type,
            DnsQueryLog.blocked,
            DnsQueryLog.block_reason,
            DnsQueryLog.answer_ip,
            DnsQueryLog.destination_port,
            DnsQueryLog.wan_ip,
            Device.hostname,
        )
        .outerjoin(Device, DnsQueryLog.device_id == Device.id)
    )

    filters = []
    dt_from = _parse_date_param(date_from, is_end=False)
    filters.append(DnsQueryLog.timestamp >= dt_from)

    dt_to = _parse_date_param(date_to, is_end=True)
    filters.append(DnsQueryLog.timestamp <= dt_to)

    if source_ip:
        filters.append(DnsQueryLog.client_ip.contains(escape_like(source_ip)))
    if domain_search:
        filters.append(DnsQueryLog.domain.contains(escape_like(domain_search)))

    query = query.where(and_(*filters))
    query = query.order_by(DnsQueryLog.timestamp)
    query = query.limit(MAX_EXPORT_ROWS)
    return query


@router.get("/export/csv")
async def export_logs_csv(
    date_from: str = Query(..., description="Başlangic tarihi (ISO 8601)"),
    date_to: str = Query(..., description="Bitiş tarihi (ISO 8601)"),
    source_ip: Optional[str] = None,
    domain_search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """5651 Kanun Uyumu: DNS loglarını CSV formatinda indir."""
    query = _build_export_query(date_from, date_to, source_ip, domain_search)
    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)

    for row in rows:
        writer.writerow([
            row.timestamp.isoformat() if row.timestamp else "",
            row.client_ip or "",
            row.mac_address or "",
            row.hostname or "",
            row.domain or "",
            row.query_type or "A",
            "BLOCKED" if row.blocked else "ALLOWED",
            row.block_reason or "",
            row.answer_ip or "",
            row.destination_port or 53,
            row.wan_ip or "",
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    filename = f"5651_dns_logs_{date_from}_{date_to}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/json")
async def export_logs_json(
    date_from: str = Query(..., description="Başlangic tarihi (ISO 8601)"),
    date_to: str = Query(..., description="Bitiş tarihi (ISO 8601)"),
    source_ip: Optional[str] = None,
    domain_search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """5651 Kanun Uyumu: DNS loglarını JSONL formatinda indir (SHA-256 hash ile)."""
    import json

    query = _build_export_query(date_from, date_to, source_ip, domain_search)
    result = await db.execute(query)
    rows = result.all()

    lines = []
    hasher = hashlib.sha256()

    for row in rows:
        record = {
            "timestamp": row.timestamp.isoformat() if row.timestamp else "",
            "client_ip": row.client_ip or "",
            "mac_address": row.mac_address or "",
            "hostname": row.hostname or "",
            "domain": row.domain or "",
            "query_type": row.query_type or "A",
            "blocked": row.blocked,
            "block_reason": row.block_reason or "",
            "answer_ip": row.answer_ip or "",
            "destination_port": row.destination_port or 53,
            "wan_ip": row.wan_ip or "",
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        lines.append(line)
        hasher.update(line.encode("utf-8"))

    # Son satir: butunluk hash'i
    integrity = {"_integrity": "sha256", "_hash": hasher.hexdigest(), "_record_count": len(lines)}
    lines.append(json.dumps(integrity, ensure_ascii=False) + "\n")

    content = "".join(lines).encode("utf-8")
    filename = f"5651_dns_logs_{date_from}_{date_to}.jsonl"

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ==================== 5651 Kanun Uyumu: Imza Doğrulama Endpoint'leri ====================

@router.get("/signatures")
async def list_log_signatures(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=10, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """5651: Imzalanmis log dosyalari listesi."""
    total = await db.scalar(select(func.count(LogSignature.id))) or 0
    total_pages = max(1, math.ceil(total / per_page))

    result = await db.execute(
        select(LogSignature)
        .order_by(desc(LogSignature.log_date))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    sigs = result.scalars().all()

    items = []
    for sig in sigs:
        # Dosya hala mevcut mu kontrol et
        file_exists = bool(sig.file_path and os.path.exists(sig.file_path))
        items.append({
            "id": sig.id,
            "log_date": sig.log_date.isoformat() if sig.log_date else "",
            "log_type": sig.log_type,
            "record_count": sig.record_count,
            "sha256_hash": sig.sha256_hash,
            "file_size_bytes": sig.file_size_bytes,
            "signed_at": sig.signed_at.isoformat() if sig.signed_at else "",
            "file_exists": file_exists,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/verify/{log_date}")
async def verify_log_signature(
    log_date: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """5651: Belirli bir tarihin imzalanmis logunu dogrula."""
    try:
        target_date = date.fromisoformat(log_date)
    except ValueError:
        raise HTTPException(400, "Geçersiz tarih formati (YYYY-MM-DD bekleniyor)")

    result = await db.execute(
        select(LogSignature).where(LogSignature.log_date == target_date)
    )
    sigs = result.scalars().all()

    if not sigs:
        raise HTTPException(404, f"{log_date} tarihi için imzalanmis log bulunamadı")

    verifications = []
    for sig in sigs:
        verified = False
        hash_match = False
        error = None

        if not sig.file_path or not os.path.exists(sig.file_path):
            error = "Dosya bulunamadı"
        else:
            try:
                h = hashlib.sha256()
                with open(sig.file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                current_hash = h.hexdigest()
                hash_match = (current_hash == sig.sha256_hash)
                verified = hash_match
            except Exception as e:
                error = str(e)

        verifications.append({
            "log_type": sig.log_type,
            "log_date": sig.log_date.isoformat(),
            "record_count": sig.record_count,
            "sha256_hash": sig.sha256_hash,
            "hash_match": hash_match,
            "verified": verified,
            "file_size_bytes": sig.file_size_bytes,
            "signed_at": sig.signed_at.isoformat() if sig.signed_at else "",
            "error": error,
        })

    all_verified = all(v["verified"] for v in verifications)

    return {
        "date": log_date,
        "verified": all_verified,
        "log_types": verifications,
    }


@router.post("/verify-integrity")
async def verify_all_integrity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """5651: Tum imzalanmis loglarin butunluk kontrolü."""
    result = await db.execute(
        select(LogSignature).order_by(LogSignature.log_date)
    )
    all_sigs = result.scalars().all()

    if not all_sigs:
        return {"total": 0, "verified": 0, "failed": 0, "missing": 0, "details": []}

    verified_count = 0
    failed_count = 0
    missing_count = 0
    failed_details = []

    for sig in all_sigs:
        if not sig.file_path or not os.path.exists(sig.file_path):
            missing_count += 1
            failed_details.append({
                "date": sig.log_date.isoformat(),
                "type": sig.log_type,
                "status": "missing",
            })
            continue

        try:
            h = hashlib.sha256()
            with open(sig.file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            if h.hexdigest() == sig.sha256_hash:
                verified_count += 1
            else:
                failed_count += 1
                failed_details.append({
                    "date": sig.log_date.isoformat(),
                    "type": sig.log_type,
                    "status": "hash_mismatch",
                })
        except Exception:
            failed_count += 1
            failed_details.append({
                "date": sig.log_date.isoformat(),
                "type": sig.log_type,
                "status": "read_error",
            })

    return {
        "total": len(all_sigs),
        "verified": verified_count,
        "failed": failed_count,
        "missing": missing_count,
        "integrity_ok": (failed_count == 0 and missing_count == 0),
        "failed_details": failed_details[:50],  # Max 50 detay
    }

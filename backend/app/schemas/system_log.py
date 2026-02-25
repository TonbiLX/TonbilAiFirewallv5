# --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
# Sistem Logları semalari: kapsamli log görüntüleme için.

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SystemLogEntry(BaseModel):
    """Tek bir sistem log kaydi."""
    id: int
    timestamp: Optional[datetime] = None
    client_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    domain: str
    query_type: str = "A"
    action: str = "query"  # query / block / allow
    category: str = "dns"  # dns / ai / security
    severity: str = "info"  # info / warning / critical
    answer_ip: Optional[str] = None
    block_reason: Optional[str] = None
    upstream_response_ms: Optional[int] = None
    bytes_total: Optional[int] = None
    source_type: str = "dns"

    class Config:
        from_attributes = True


class SystemLogListResponse(BaseModel):
    """Sayfalanmis log listesi yaniti."""
    items: List[SystemLogEntry]
    total: int
    page: int
    per_page: int
    total_pages: int


class SystemLogSummary(BaseModel):
    """30 gunluk özet istatistikler."""
    total_logs_30d: int = 0
    dns_queries_30d: int = 0
    blocked_30d: int = 0
    ai_insights_30d: int = 0
    critical_30d: int = 0
    traffic_logs_30d: int = 0

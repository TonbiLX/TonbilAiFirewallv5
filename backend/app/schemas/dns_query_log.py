# --- Ajan: MUHAFIZ (THE GUARDIAN) + ANALIST (THE ANALYST) ---
# DNS Query Log Pydantic semalari: API response validasyonu.

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DnsQueryLogResponse(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    device_id: Optional[int] = None
    client_ip: Optional[str] = None
    domain: str
    query_type: str = "A"
    blocked: bool = False
    block_reason: Optional[str] = None
    upstream_response_ms: Optional[int] = None
    answer_ip: Optional[str] = None
    source_type: Optional[str] = "INTERNAL"   # INTERNAL / EXTERNAL / DOT / DOH
    dnssec_status: Optional[str] = None        # verified / not_signed / failed / error / skipped
    protocol: Optional[str] = "udp"            # udp / dot / doh

    class Config:
        from_attributes = True


class DomainCountItem(BaseModel):
    domain: str
    count: int


class ClientCountItem(BaseModel):
    device_id: Optional[int] = None
    client_ip: Optional[str] = None
    query_count: int


class DnsStatsResponse(BaseModel):
    total_queries_24h: int = 0
    blocked_queries_24h: int = 0
    block_percentage: float = 0.0
    total_blocklist_domains: int = 0
    active_blocklists: int = 0
    top_blocked_domains: List[DomainCountItem] = []
    top_queried_domains: List[DomainCountItem] = []
    top_clients: List[ClientCountItem] = []
    external_queries_24h: int = 0   # Dışarıdan gelen sorgu sayısı

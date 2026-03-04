# --- Ajan: MIMAR (THE ARCHITECT) ---
# ConnectionFlow Pydantic semalari: canli akis, gecmis, istatistik.

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LiveFlowResponse(BaseModel):
    """Tek bir baglanti akisi (canli veya gecmis)."""
    flow_id: str
    device_id: Optional[int] = None
    device_hostname: Optional[str] = None
    device_ip: Optional[str] = None
    src_ip: str
    src_port: Optional[int] = None
    dst_ip: str
    dst_port: Optional[int] = None
    dst_domain: Optional[str] = None
    protocol: str
    state: Optional[str] = None
    direction: Optional[str] = None
    service_name: Optional[str] = None
    app_name: Optional[str] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    bytes_total: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    bps_in: float = 0.0
    bps_out: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    category: Optional[str] = None
    dst_device_id: Optional[int] = None
    dst_device_hostname: Optional[str] = None

    class Config:
        from_attributes = True


class FlowHistoryResponse(BaseModel):
    """Sayfalanmis gecmis akis listesi."""
    items: List[LiveFlowResponse]
    total: int
    limit: int
    offset: int


class DeviceFlowSummary(BaseModel):
    """Cihaz bazli akis ozeti."""
    device_id: int
    device_hostname: Optional[str] = None
    active_flows: int = 0
    total_flows_period: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    top_domains: List[dict] = []
    top_ports: List[dict] = []


class FlowStatsResponse(BaseModel):
    """Genel akis istatistikleri."""
    total_active_flows: int = 0
    total_bytes_in: int = 0
    total_bytes_out: int = 0
    total_devices_with_flows: int = 0
    large_transfer_count: int = 0
    total_internal_flows: int = 0
    last_update: Optional[datetime] = None

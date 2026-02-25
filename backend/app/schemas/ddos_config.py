# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DDoS koruma yapılandirma schemalari.

from typing import Optional
from pydantic import BaseModel


class DdosConfigResponse(BaseModel):
    """DDoS config GET yaniti."""
    syn_flood_enabled: bool = True
    syn_flood_rate: int = 25
    syn_flood_burst: int = 50

    udp_flood_enabled: bool = True
    udp_flood_rate: int = 50
    udp_flood_burst: int = 100

    icmp_flood_enabled: bool = True
    icmp_flood_rate: int = 10
    icmp_flood_burst: int = 20

    conn_limit_enabled: bool = True
    conn_limit_per_ip: int = 100

    invalid_packet_enabled: bool = True

    http_flood_enabled: bool = False
    http_flood_rate: str = "30r/s"
    http_flood_burst: int = 60

    kernel_hardening_enabled: bool = True
    tcp_max_syn_backlog: int = 4096
    tcp_synack_retries: int = 2
    netfilter_conntrack_max: int = 262144

    uvicorn_workers_enabled: bool = False
    uvicorn_workers: int = 2

    class Config:
        from_attributes = True


class DdosConfigUpdate(BaseModel):
    """DDoS config PUT istegi (tum alanlar optional)."""
    syn_flood_enabled: Optional[bool] = None
    syn_flood_rate: Optional[int] = None
    syn_flood_burst: Optional[int] = None

    udp_flood_enabled: Optional[bool] = None
    udp_flood_rate: Optional[int] = None
    udp_flood_burst: Optional[int] = None

    icmp_flood_enabled: Optional[bool] = None
    icmp_flood_rate: Optional[int] = None
    icmp_flood_burst: Optional[int] = None

    conn_limit_enabled: Optional[bool] = None
    conn_limit_per_ip: Optional[int] = None

    invalid_packet_enabled: Optional[bool] = None

    http_flood_enabled: Optional[bool] = None
    http_flood_rate: Optional[str] = None
    http_flood_burst: Optional[int] = None

    kernel_hardening_enabled: Optional[bool] = None
    tcp_max_syn_backlog: Optional[int] = None
    tcp_synack_retries: Optional[int] = None
    netfilter_conntrack_max: Optional[int] = None

    uvicorn_workers_enabled: Optional[bool] = None
    uvicorn_workers: Optional[int] = None


class DdosProtectionStatus(BaseModel):
    """Tek koruma durumu."""
    name: str
    enabled: bool
    active: bool
    description: str

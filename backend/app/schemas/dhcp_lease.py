# --- Ajan: MIMAR (THE ARCHITECT) ---
# DHCP Lease Pydantic semalari: API request/response validasyonu.

import re

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

_MAC_RE = re.compile(r'^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$')


class DhcpLeaseResponse(BaseModel):
    id: int
    mac_address: str
    ip_address: str
    hostname: Optional[str] = None
    lease_start: Optional[datetime] = None
    lease_end: Optional[datetime] = None
    is_static: bool = False
    device_id: Optional[int] = None
    pool_id: Optional[int] = None

    class Config:
        from_attributes = True


class StaticLeaseCreate(BaseModel):
    mac_address: str
    ip_address: str
    hostname: Optional[str] = None

    @field_validator('mac_address')
    @classmethod
    def validate_mac(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError('Gecersiz MAC adresi')
        return v.upper()

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        ipaddress.ip_address(v)
        return v

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.replace('\n', '').replace('\r', '').replace(';', '').strip()[:63]
        return v


class DhcpStatsResponse(BaseModel):
    total_pools: int = 0
    active_pools: int = 0
    total_ips: int = 0
    assigned_ips: int = 0
    available_ips: int = 0
    static_leases: int = 0
    dynamic_leases: int = 0
    dnsmasq_running: bool = False


class DhcpServiceStatusResponse(BaseModel):
    dnsmasq_running: bool = False
    config_dir_exists: bool = False
    lease_file_exists: bool = False
    pool_config_count: int = 0
    active_leases_count: int = 0


class DhcpLiveLeaseResponse(BaseModel):
    mac_address: str
    ip_address: str
    hostname: str = ""
    lease_end: Optional[datetime] = None
    is_expired: bool = False

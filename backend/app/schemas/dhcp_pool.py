# --- Ajan: MIMAR (THE ARCHITECT) ---
# DHCP Pool Pydantic semalari: API request/response validasyonu.
# NOT: Validator'lar sadece Create/Update modellerinde.

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class DhcpPoolCreate(BaseModel):
    name: str
    subnet: str
    netmask: str = "255.255.255.0"
    range_start: str
    range_end: str
    gateway: str
    dns_servers: List[str] = ["192.168.1.2"]
    lease_time_seconds: int = 86400
    enabled: bool = True

    @field_validator('subnet', 'range_start', 'range_end', 'gateway', 'netmask')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f'Geçersiz IP adresi: {v}')
        return v

    @field_validator('dns_servers')
    @classmethod
    def validate_dns_servers(cls, v: List[str]) -> List[str]:
        import ipaddress
        for server in v:
            try:
                ipaddress.ip_address(server)
            except ValueError:
                raise ValueError(f'Geçersiz DNS sunucu IP adresi: {server}')
        return v

    @field_validator('lease_time_seconds')
    @classmethod
    def validate_lease_time(cls, v: int) -> int:
        if v < 60 or v > 604800:
            raise ValueError('Lease süresi 60-604800 saniye aralığında olmali')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Isim bos olamaz')
        if len(v) > 100:
            raise ValueError('Isim 100 karakterden uzun olamaz')
        return v


class DhcpPoolUpdate(BaseModel):
    name: Optional[str] = None
    subnet: Optional[str] = None
    netmask: Optional[str] = None
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: Optional[List[str]] = None
    lease_time_seconds: Optional[int] = None
    enabled: Optional[bool] = None

    @field_validator('subnet', 'range_start', 'range_end', 'gateway', 'netmask')
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f'Geçersiz IP adresi: {v}')
        return v

    @field_validator('lease_time_seconds')
    @classmethod
    def validate_lease_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 60 or v > 604800):
            raise ValueError('Lease süresi 60-604800 saniye aralığında olmali')
        return v


class DhcpPoolResponse(BaseModel):
    id: int
    name: str
    subnet: str
    netmask: str = "255.255.255.0"
    range_start: str
    range_end: str
    gateway: str
    dns_servers: List[str] = ["192.168.1.2"]
    lease_time_seconds: int = 86400
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

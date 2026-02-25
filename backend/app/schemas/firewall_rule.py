# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Firewall kural semalari: port yönetimi ve güvenlik duvarı konfigurasyonu.
# NOT: Validator'lar sadece Create/Update modellerinde.

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

_VALID_DIRECTIONS = {"inbound", "outbound", "forward"}
_VALID_PROTOCOLS = {"tcp", "udp", "both", "icmp", "all"}
_VALID_ACTIONS = {"accept", "drop", "reject"}


class FirewallRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    direction: str = "inbound"
    protocol: str = "tcp"
    port: Optional[int] = None
    port_end: Optional[int] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    action: str = "drop"
    enabled: bool = True
    priority: int = 100
    log_packets: bool = False

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in _VALID_DIRECTIONS:
            raise ValueError(f'Geçersiz direction: {v} (izin verilen: {_VALID_DIRECTIONS})')
        return v

    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        if v not in _VALID_PROTOCOLS:
            raise ValueError(f'Geçersiz protocol: {v} (izin verilen: {_VALID_PROTOCOLS})')
        return v

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in _VALID_ACTIONS:
            raise ValueError(f'Geçersiz action: {v} (izin verilen: {_VALID_ACTIONS})')
        return v

    @field_validator('port', 'port_end')
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 65535):
            raise ValueError('Port 1-65535 aralığında olmali')
        return v

    @field_validator('source_ip', 'dest_ip')
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import ipaddress
            try:
                if '/' in v:
                    ipaddress.ip_network(v, strict=False)
                else:
                    ipaddress.ip_address(v)
            except ValueError:
                raise ValueError('Geçersiz IP adresi veya CIDR')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if v < 0 or v > 10000:
            raise ValueError('Priority 0-10000 aralığında olmali')
        return v


class FirewallRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    direction: Optional[str] = None
    protocol: Optional[str] = None
    port: Optional[int] = None
    port_end: Optional[int] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    action: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    log_packets: Optional[bool] = None

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_DIRECTIONS:
            raise ValueError(f'Geçersiz direction: {v}')
        return v

    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_PROTOCOLS:
            raise ValueError(f'Geçersiz protocol: {v}')
        return v

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_ACTIONS:
            raise ValueError(f'Geçersiz action: {v}')
        return v

    @field_validator('port', 'port_end')
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 65535):
            raise ValueError('Port 1-65535 aralığında olmali')
        return v


class FirewallRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    direction: str = "inbound"
    protocol: str = "tcp"
    port: Optional[int] = None
    port_end: Optional[int] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    action: str = "drop"
    enabled: bool = True
    priority: int = 100
    log_packets: bool = False
    hit_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortScanResult(BaseModel):
    port: int
    protocol: str
    state: str
    service: Optional[str] = None


class FirewallStatsResponse(BaseModel):
    total_rules: int = 0
    active_rules: int = 0
    inbound_rules: int = 0
    outbound_rules: int = 0
    blocked_packets_24h: int = 0
    open_ports: list = []

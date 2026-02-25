# --- Ajan: MIMAR (THE ARCHITECT) ---
# Device Pydantic semalari.
# NOT: Validator'lar sadece Create/Update modellerinde.
# Response modeli DB'den gelen veriyi oldugu gibi dondurur.

import re
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

_MAC_RE = re.compile(r'^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$')
# Hostname: alfanumerik, tire, alt çizgi, nokta (gercek ag cihazlari için)
_HOSTNAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_.]{0,62}$')


class DeviceCreate(BaseModel):
    mac_address: str
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    manufacturer: Optional[str] = None
    profile_id: Optional[int] = None

    @field_validator('mac_address')
    @classmethod
    def validate_mac(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError('Geçersiz MAC adresi formatı (beklenen: XX:XX:XX:XX:XX:XX)')
        return v.upper()

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError('Geçersiz IP adresi')
        return v

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()[:63]
            if v and not _HOSTNAME_RE.match(v):
                raise ValueError('Geçersiz hostname')
        return v


class DeviceUpdate(BaseModel):
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    manufacturer: Optional[str] = None
    profile_id: Optional[int] = None
    # is_blocked burada yok — block/unblock icin /block ve /unblock endpointleri kullanilmali
    # Dogrudan is_blocked degistirmek nftables kurallariyla tutarsizlik olusturur

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError('Geçersiz IP adresi')
        return v

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()[:63]
            if v and not _HOSTNAME_RE.match(v):
                raise ValueError('Geçersiz hostname')
        return v


class BandwidthLimitUpdate(BaseModel):
    limit_mbps: Optional[int] = None  # None veya 0 = limitsiz, >0 = Mbps sinir

    @field_validator('limit_mbps')
    @classmethod
    def validate_limit(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 10000):
            raise ValueError('Bant genisligi siniri 0-10000 Mbps arasi olmali')
        return v


class DeviceResponse(BaseModel):
    id: int
    mac_address: str
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    manufacturer: Optional[str] = None
    profile_id: Optional[int] = None
    is_blocked: bool = False
    is_online: bool = True
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_online_seconds: int = 0
    last_online_start: Optional[datetime] = None
    bandwidth_limit_mbps: Optional[int] = None

    class Config:
        from_attributes = True

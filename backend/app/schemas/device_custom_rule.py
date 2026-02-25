# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Cihaz özel kural Pydantic semalari.

import re
from pydantic import BaseModel, field_validator
from datetime import datetime

_DOMAIN_RE = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*'
    r'[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
)


class DeviceCustomRuleCreate(BaseModel):
    """Kural oluşturma istegi — device_id path parametresinden gelir."""
    domain: str
    rule_type: str  # "block" | "allow"
    reason: str | None = None

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError('Domain bos olamaz')
        if len(v) > 253:
            raise ValueError('Domain 253 karakterden uzun olamaz')
        if not _DOMAIN_RE.match(v):
            raise ValueError('Geçersiz domain formatı')
        return v

    @field_validator('rule_type')
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in {"block", "allow"}:
            raise ValueError('rule_type "block" veya "allow" olmali')
        return v


class DeviceCustomRuleUpdate(BaseModel):
    """Kural güncelleme istegi — domain, rule_type, reason değiştirilebilir."""
    domain: str | None = None
    rule_type: str | None = None  # "block" | "allow"
    reason: str | None = None

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip().lower()
            if not v:
                raise ValueError('Domain bos olamaz')
            if len(v) > 253:
                raise ValueError('Domain 253 karakterden uzun olamaz')
            if not _DOMAIN_RE.match(v):
                raise ValueError('Geçersiz domain formatı')
        return v

    @field_validator('rule_type')
    @classmethod
    def validate_rule_type(cls, v: str | None) -> str | None:
        if v is not None and v not in {"block", "allow"}:
            raise ValueError('rule_type "block" veya "allow" olmali')
        return v


class DeviceCustomRuleSummary(BaseModel):
    """Tum kurallari listelerken kullanilir (Device bilgisiyle zenginlestirilmis)."""
    id: int
    device_id: int
    device_hostname: str | None = None
    device_ip: str | None = None
    domain: str
    rule_type: str
    reason: str | None = None
    added_by: str = "user"
    created_at: datetime | None = None

    class Config:
        from_attributes = True

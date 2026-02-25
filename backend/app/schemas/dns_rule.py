# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DNS Rule Pydantic semalari: API request/response validasyonu.
# NOT: Validator'lar sadece Create modelinde.

import re
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

_DOMAIN_RE = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*'
    r'[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
)
_VALID_RULE_TYPES = {"block", "allow", "whitelist", "blacklist"}


class DnsRuleCreate(BaseModel):
    domain: str
    rule_type: str
    reason: Optional[str] = None
    profile_id: Optional[int] = None

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
        if v not in _VALID_RULE_TYPES:
            raise ValueError(f'Geçersiz rule_type: {v} (izin verilen: {_VALID_RULE_TYPES})')
        return v


class DnsRuleResponse(BaseModel):
    id: int
    domain: str
    rule_type: str
    reason: Optional[str] = None
    profile_id: Optional[int] = None
    added_by: str = "user"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

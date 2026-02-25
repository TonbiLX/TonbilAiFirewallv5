# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# TLS/Şifreleme yapılandirma semalari.

from pydantic import BaseModel
from datetime import datetime


class TlsConfigUpdate(BaseModel):
    domain: str | None = None
    certificate_chain: str | None = None
    private_key: str | None = None
    lets_encrypt_enabled: bool | None = None
    lets_encrypt_email: str | None = None
    doh_enabled: bool | None = None
    dot_enabled: bool | None = None
    https_enabled: bool | None = None
    https_port: int | None = None
    dot_port: int | None = None
    enabled: bool | None = None


class TlsConfigResponse(BaseModel):
    id: int
    domain: str | None
    cert_path: str | None
    key_path: str | None
    certificate_chain: str | None
    private_key: str | None
    cert_subject: str | None
    cert_issuer: str | None
    cert_not_before: datetime | None
    cert_not_after: datetime | None
    cert_valid: bool
    lets_encrypt_enabled: bool
    lets_encrypt_email: str | None
    doh_enabled: bool
    dot_enabled: bool
    https_enabled: bool
    https_port: int
    dot_port: int
    enabled: bool
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class TlsValidateRequest(BaseModel):
    certificate_chain: str
    private_key: str
    domain: str | None = None


class TlsValidateResponse(BaseModel):
    valid: bool
    subject: str | None = None
    issuer: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    domain_match: bool | None = None
    error: str | None = None

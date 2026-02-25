# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# TLS/Şifreleme yapılandirmasi: DoH, DoT, Let's Encrypt sertifika yönetimi.
# Android Özel DNS desteği için DNS-over-TLS (DoT) ve DNS-over-HTTPS (DoH).

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.db.base import Base


class TlsConfig(Base):
    """TLS sertifika ve şifreleme yapılandirmasi."""
    __tablename__ = "tls_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=True)  # örn. guard.tonbilx.com
    cert_path = Column(String(500), nullable=True)
    key_path = Column(String(500), nullable=True)
    certificate_chain = Column(Text, nullable=True)  # PEM sertifika icerigi
    private_key = Column(Text, nullable=True)  # PEM özel anahtar icerigi
    cert_subject = Column(String(500), nullable=True)  # CN bilgisi
    cert_issuer = Column(String(500), nullable=True)  # Veren kurum
    cert_not_before = Column(DateTime, nullable=True)
    cert_not_after = Column(DateTime, nullable=True)  # Gecerlilik sonu
    cert_valid = Column(Boolean, default=False)  # Sertifika gecerli mi
    lets_encrypt_enabled = Column(Boolean, default=False)
    lets_encrypt_email = Column(String(255), nullable=True)
    doh_enabled = Column(Boolean, default=False)  # DNS-over-HTTPS
    dot_enabled = Column(Boolean, default=False)  # DNS-over-TLS
    https_enabled = Column(Boolean, default=False)  # Yönetim paneli HTTPS
    https_port = Column(Integer, default=443)
    dot_port = Column(Integer, default=853)
    enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

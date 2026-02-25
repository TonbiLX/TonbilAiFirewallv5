# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# 5651 Kanun Uyumu: Gunluk log imza kayitlari.
# Her gun imzalanan log dosyalarinin hash ve meta bilgileri.

from sqlalchemy import Column, Integer, String, Date, DateTime, BigInteger
from sqlalchemy.sql import func

from app.db.base import Base


class LogSignature(Base):
    __tablename__ = "log_signatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_date = Column(Date, index=True, nullable=False)         # Hangi gunun logu
    log_type = Column(String(20), nullable=False)               # "dns", "dhcp", "connection"
    file_path = Column(String(500), nullable=True)              # Imzali dosya yolu
    record_count = Column(Integer, default=0)                   # Kayit sayısı
    sha256_hash = Column(String(64), nullable=False)            # SHA-256 özet
    hmac_signature = Column(String(64), nullable=True)          # HMAC-SHA256 imza
    file_size_bytes = Column(BigInteger, default=0)             # Dosya boyutu (byte)
    signed_at = Column(DateTime, server_default=func.now())     # Imzalanma zamani

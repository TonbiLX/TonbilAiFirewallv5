# --- Ajan: DEDEKTIF (THE DETECTIVE) ---
# AbuseIPDB kara liste kayitlari — kalici SQL deposu.
# Redis'te 48 saatlik TTL var; bu model en son fetch sonuclarini kalici saklar.

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func

from app.db.base import Base


class IpBlacklistEntry(Base):
    __tablename__ = "ip_blacklist_entries"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    ip_address       = Column(String(45), nullable=False, unique=True, index=True)
    abuse_score      = Column(Integer, default=0)
    country          = Column(String(10),  nullable=True)
    last_reported_at = Column(String(50),  nullable=True)  # AbuseIPDB ISO format string
    fetched_at       = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_ibe_score",   "abuse_score"),
        Index("idx_ibe_fetched", "fetched_at"),
    )

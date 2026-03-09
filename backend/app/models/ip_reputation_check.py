# --- Ajan: DEDEKTIF (THE DETECTIVE) ---
# IP Reputation kontrol kayitlari — kalici SQL deposu.
# Redis cache 24 saatte dolabilir; bu model verileri kalici saklar.

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func

from app.db.base import Base


class IpReputationCheck(Base):
    __tablename__ = "ip_reputation_checks"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    ip_address    = Column(String(45), nullable=False, unique=True, index=True)
    abuse_score   = Column(Integer, default=0)
    total_reports = Column(Integer, default=0)
    country       = Column(String(100), nullable=True)
    country_code  = Column(String(10),  nullable=True)
    city          = Column(String(100), nullable=True)
    isp           = Column(String(200), nullable=True)
    org           = Column(String(200), nullable=True)
    checked_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_irc_score",      "abuse_score"),
        Index("idx_irc_checked_at", "checked_at"),
    )

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Engellenen IP modeli: kalici veritabani tabanli IP engelleme.
# Redis'teki gecici engellere ek olarak, manuel/kalici engelleri saklar.

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class BlockedIp(Base):
    __tablename__ = "blocked_ips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, unique=True, index=True)
    reason = Column(String(500), nullable=True)
    blocked_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)       # NULL = kalici engel
    is_manual = Column(Boolean, default=True)           # True=manuel, False=auto
    source = Column(String(100), default="manual")      # "manual", "threat_analyzer", "api"

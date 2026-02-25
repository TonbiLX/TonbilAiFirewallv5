# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Engelleme servisi modeli: AdGuard Home tarzi onceden tanimli
# servis tanimlari (YouTube, Netflix, WhatsApp vb.).

from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class BlockedService(Base):
    """Onceden tanimli engelleme servisi (AdGuard HostlistsRegistry'den)."""
    __tablename__ = "blocked_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    group_name = Column(String(50), nullable=False, index=True)
    icon_svg = Column(Text, nullable=True)
    rules = Column(JSON, nullable=False)
    domain_count = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Güvenilir IP modeli: tehdit analizcisi tarafindan otomatik
# engellemeye tabi tutulmayacak IP adresleri.

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class TrustedIp(Base):
    __tablename__ = "trusted_ips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

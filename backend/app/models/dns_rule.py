# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Kullanıcı tanimli DNS kurallari: bireysel domain engelleme/izin verme.
# profile_id NULL ise kural global (tum cihazlar), doluysa profil bazli.

import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DnsRuleType(str, enum.Enum):
    BLOCK = "block"
    ALLOW = "allow"


class DnsRule(Base):
    __tablename__ = "dns_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, index=True)
    rule_type = Column(SAEnum(DnsRuleType), nullable=False)
    reason = Column(String(500), nullable=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    added_by = Column(String(100), default="user")
    created_at = Column(DateTime, server_default=func.now())

    profile = relationship("Profile")

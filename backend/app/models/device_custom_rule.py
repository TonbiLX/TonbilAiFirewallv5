# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Cihaz bazinda özel DNS kurallari: belirli bir cihaz için
# domain/IP engelleme veya izin verme.

import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DeviceCustomRuleType(str, enum.Enum):
    BLOCK = "block"
    ALLOW = "allow"


class DeviceCustomRule(Base):
    """Cihaz bazinda özel DNS engel/izin kuralı."""
    __tablename__ = "device_custom_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain = Column(String(255), nullable=False, index=True)
    rule_type = Column(SAEnum(DeviceCustomRuleType), nullable=False)
    reason = Column(String(500), nullable=True)
    added_by = Column(String(100), default="user")  # "user", "ai_chat"
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("device_id", "domain", name="uq_device_domain_rule"),
    )

    device = relationship("Device")

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Cihaz bazinda servis engelleme iliskisi.
# Her cihaz için hangi servislerin engelli oldugunu tutar.

from sqlalchemy import (
    Column, Integer, Boolean, JSON, DateTime,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DeviceBlockedService(Base):
    """Cihaz bazinda servis engelleme yapılandirmasi."""
    __tablename__ = "device_blocked_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("blocked_services.id", ondelete="CASCADE"),
                        nullable=False)
    blocked = Column(Boolean, default=True)
    schedule = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("device_id", "service_id", name="uq_device_service"),
    )

    device = relationship("Device")
    service = relationship("BlockedService")

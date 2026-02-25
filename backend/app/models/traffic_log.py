# --- Ajan: MIMAR (THE ARCHITECT) ---
# Trafik log modeli: cihaz bazli ag aktivite kayitlari.

from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TrafficLog(Base):
    __tablename__ = "traffic_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    destination_domain = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)  # "social", "streaming", "gambling", "education"
    bytes_sent = Column(BigInteger, default=0)
    bytes_received = Column(BigInteger, default=0)
    protocol = Column(String(20), nullable=True)   # "TCP", "UDP", "DNS"

    # Iliskiler
    device = relationship("Device", back_populates="traffic_logs")

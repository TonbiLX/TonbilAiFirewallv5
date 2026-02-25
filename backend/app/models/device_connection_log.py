# --- Ajan: MIMAR (THE ARCHITECT) ---
# Cihaz bağlantı gecmisi: connect/disconnect olaylari.

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.base import Base


class DeviceConnectionLog(Base):
    """Cihaz bağlantı/ayrilma olay logu."""
    __tablename__ = "device_connection_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # "connect" veya "disconnect"
    ip_address = Column(String(45), nullable=True)
    session_duration_seconds = Column(Integer, nullable=True)  # Sadece disconnect için
    timestamp = Column(DateTime, server_default=func.now())

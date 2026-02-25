# --- Ajan: ANALIST (THE ANALYST) ---
# Saatlik/gunluk agrega trafik verisi modeli.
# bandwidth_monitor tarafindan periyodik olarak doldurulur.

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DeviceTrafficSnapshot(Base):
    __tablename__ = "device_traffic_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    period = Column(String(10), nullable=False, default="hourly")  # "hourly" / "daily"
    upload_bytes = Column(BigInteger, default=0)
    download_bytes = Column(BigInteger, default=0)
    upload_packets = Column(BigInteger, default=0)
    download_packets = Column(BigInteger, default=0)
    peak_upload_bps = Column(BigInteger, default=0)
    peak_download_bps = Column(BigInteger, default=0)
    connection_count = Column(Integer, default=0)

    # Iliskiler
    device = relationship("Device", backref="traffic_snapshots")

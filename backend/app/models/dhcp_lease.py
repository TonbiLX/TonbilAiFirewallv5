# --- Ajan: MIMAR (THE ARCHITECT) ---
# DHCP kiralama kayitlari: aktif IP atamalari ve statik reservasyonlar.
# is_static=True olan kayitlar MAC-IP eslesmesi olarak kalici korunur.

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DhcpLease(Base):
    __tablename__ = "dhcp_leases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mac_address = Column(String(17), nullable=False, index=True)
    ip_address = Column(String(15), nullable=False, unique=True, index=True)
    hostname = Column(String(255), nullable=True)
    lease_start = Column(DateTime, server_default=func.now())
    lease_end = Column(DateTime, nullable=True)
    is_static = Column(Boolean, default=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    pool_id = Column(Integer, ForeignKey("dhcp_pools.id"), nullable=True)

    device = relationship("Device")
    pool = relationship("DhcpPool", back_populates="leases")

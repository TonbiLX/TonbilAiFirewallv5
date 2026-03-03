# --- Ajan: MIMAR (THE ARCHITECT) ---
# DHCP IP havuzu konfigurasyonu: subnet, IP aralığı, gateway, DNS, lease süresi.
# Birden fazla havuz desteği (Ana AG, Misafir AG gibi).

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DhcpPool(Base):
    __tablename__ = "dhcp_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    subnet = Column(String(18), nullable=False)          # "192.168.1.0"
    netmask = Column(String(15), nullable=False)          # "255.255.255.0"
    range_start = Column(String(15), nullable=False)      # "192.168.1.100"
    range_end = Column(String(15), nullable=False)        # "192.168.1.200"
    gateway = Column(String(15), nullable=False)          # "192.168.1.2"
    dns_servers = Column(JSON, default=["192.168.1.2"])   # Router kendisi DNS
    lease_time_seconds = Column(Integer, default=86400)   # 24 saat
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    leases = relationship("DhcpLease", back_populates="pool")

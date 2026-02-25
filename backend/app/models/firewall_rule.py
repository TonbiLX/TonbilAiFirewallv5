# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Firewall kural modeli: port acma/kapatma, NAT, forwarding kurallari.
# nftables tabanli güvenlik duvarı yönetimi.

import enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.sql import func

from app.db.base import Base


class FirewallAction(str, enum.Enum):
    ACCEPT = "accept"
    DROP = "drop"
    REJECT = "reject"


class FirewallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    FORWARD = "forward"


class FirewallProtocol(str, enum.Enum):
    TCP = "tcp"
    UDP = "udp"
    BOTH = "both"
    ICMP = "icmp"
    ALL = "all"


class FirewallRule(Base):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    direction = Column(SAEnum(FirewallDirection), nullable=False, default=FirewallDirection.INBOUND)
    protocol = Column(SAEnum(FirewallProtocol), nullable=False, default=FirewallProtocol.TCP)
    port = Column(Integer, nullable=True)           # Tek port (NULL=tum portlar)
    port_end = Column(Integer, nullable=True)        # Port aralığı bitiş (opsiyonel)
    source_ip = Column(String(45), nullable=True)    # Kaynak IP (NULL=hepsi)
    dest_ip = Column(String(45), nullable=True)      # Hedef IP (NULL=hepsi)
    action = Column(SAEnum(FirewallAction), nullable=False, default=FirewallAction.DROP)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)          # Dusuk = daha once uygulanir
    log_packets = Column(Boolean, default=False)     # Paketleri logla
    hit_count = Column(Integer, default=0)           # Kac paket bu kurala denk geldi
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

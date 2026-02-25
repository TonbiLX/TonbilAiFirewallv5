# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# VPN İstemci modeli: Dış VPN sunucularina baglanma (Surfshark, NordVPN, vb.)
# Ev internetini ülke bazli VPN tuneli üzerinden yonlendirme.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.db.base import Base


class VpnClientServer(Base):
    """Harici VPN sunucu yapılandirmasi - ülke bazli trafik yonlendirme."""
    __tablename__ = "vpn_client_servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    country = Column(String(50), nullable=False)
    country_code = Column(String(5), nullable=False)  # US, DE, JP, TR, vb.
    endpoint = Column(String(255), nullable=False)  # sunucu:port
    public_key = Column(String(64), nullable=False)
    private_key = Column(String(64), nullable=True)
    preshared_key = Column(String(64), nullable=True)
    interface_address = Column(String(50), nullable=True)  # VPN içindeki istemci adresi
    allowed_ips = Column(String(255), default="0.0.0.0/0, ::/0")
    dns_servers = Column(String(255), nullable=True)
    mtu = Column(Integer, default=1420)
    persistent_keepalive = Column(Integer, default=25)
    is_active = Column(Boolean, default=False)  # Ayni anda sadece biri aktif
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

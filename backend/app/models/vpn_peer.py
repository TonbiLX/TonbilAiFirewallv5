# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WireGuard VPN peer modeli: VPN bağlantı noktaları ve istemci konfigurasyonlari.
# Hem uzaktan eve baglanma hem de tum ev trafiğini VPN üzerinden yonlendirme desteği.

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func

from app.db.base import Base


class VpnPeer(Base):
    __tablename__ = "vpn_peers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)        # Peer adi (orn: "Baba-Telefon")
    public_key = Column(String(44), nullable=True)     # WireGuard public key
    private_key = Column(Text, nullable=True)          # Şifrelenmis private key (config için)
    preshared_key = Column(String(44), nullable=True)  # Opsiyonel PSK
    allowed_ips = Column(String(255), nullable=False)  # Izin verilen IP aralığı (orn: "10.0.0.2/32")
    endpoint = Column(String(255), nullable=True)      # Peer endpoint (dinamik bağlantı için bos)
    dns_servers = Column(String(255), nullable=True)   # DNS sunuculari (orn: "10.0.0.1")
    persistent_keepalive = Column(Integer, default=25) # Keepalive aralığı (NAT için)
    enabled = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)      # Su an bagli mi
    last_handshake = Column(DateTime, nullable=True)   # Son el sikisma zamani
    transfer_rx = Column(Integer, default=0)           # Alinan byte
    transfer_tx = Column(Integer, default=0)           # Gönderilen byte
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class VpnConfig(Base):
    __tablename__ = "vpn_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interface_name = Column(String(20), default="wg0")
    listen_port = Column(Integer, default=51820)
    server_private_key = Column(Text, nullable=True)
    server_public_key = Column(String(44), nullable=True)
    server_address = Column(String(45), default="10.0.0.1/24")  # VPN subnet
    dns_server = Column(String(45), default="10.0.0.1")
    mtu = Column(Integer, default=1420)
    post_up = Column(Text, nullable=True)    # Interface aktif sonrası komut
    post_down = Column(Text, nullable=True)  # Interface kapanma sonrası komut
    enabled = Column(Boolean, default=False)
    route_all_traffic = Column(Boolean, default=False)  # Tum trafiği VPN üzerinden yonlendir
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

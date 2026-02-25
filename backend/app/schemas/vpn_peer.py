# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WireGuard VPN semalari: dosya tabanli okuma için.

from pydantic import BaseModel
from typing import Optional


class VpnPeerResponse(BaseModel):
    """Peer bilgileri (dosya sisteminden okunan + canlı veri)."""
    name: str
    public_key: Optional[str] = None
    allowed_ips: str = ""
    dns_servers: Optional[str] = None
    endpoint: Optional[str] = None
    enabled: bool = True
    has_qr: bool = False
    is_connected: bool = False
    last_handshake: Optional[str] = None
    transfer_rx: int = 0
    transfer_tx: int = 0


class VpnPeerConfigResponse(BaseModel):
    """Peer için indirilebilir WireGuard konfigurasyonu."""
    peer_name: str
    config_text: str
    qr_data: Optional[str] = None


class VpnConfigResponse(BaseModel):
    """WireGuard sunucu konfigurasyonu."""
    interface_name: str = "wg0"
    listen_port: int = 51820
    server_public_key: Optional[str] = None
    server_address: str = "10.13.13.1/24"
    dns_server: str = "10.13.13.1"
    mtu: int = 1420
    enabled: bool = False


class VpnStatsResponse(BaseModel):
    """VPN istatistikleri."""
    server_enabled: bool = False
    server_public_key: Optional[str] = None
    listen_port: int = 51820
    total_peers: int = 0
    connected_peers: int = 0
    total_transfer_rx: int = 0
    total_transfer_tx: int = 0

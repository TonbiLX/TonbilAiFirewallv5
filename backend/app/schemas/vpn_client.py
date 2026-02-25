# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Dış VPN istemci semalari.

from pydantic import BaseModel
from datetime import datetime


class VpnClientServerCreate(BaseModel):
    name: str
    country: str
    country_code: str
    endpoint: str
    public_key: str
    private_key: str | None = None
    preshared_key: str | None = None
    interface_address: str | None = None
    allowed_ips: str = "0.0.0.0/0, ::/0"
    dns_servers: str | None = None
    mtu: int = 1420
    persistent_keepalive: int = 25


class VpnClientServerUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    country_code: str | None = None
    endpoint: str | None = None
    public_key: str | None = None
    private_key: str | None = None
    preshared_key: str | None = None
    interface_address: str | None = None
    allowed_ips: str | None = None
    dns_servers: str | None = None
    mtu: int | None = None
    persistent_keepalive: int | None = None
    enabled: bool | None = None


class VpnClientServerResponse(BaseModel):
    id: int
    name: str
    country: str
    country_code: str
    endpoint: str
    public_key: str
    interface_address: str | None
    allowed_ips: str
    dns_servers: str | None
    mtu: int
    persistent_keepalive: int
    is_active: bool
    enabled: bool
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class VpnClientImport(BaseModel):
    """WireGuard .conf dosyasindan import."""
    name: str
    country: str = "Bilinmiyor"
    country_code: str = "XX"
    config_text: str  # Ham WireGuard config metni


class VpnClientStatsResponse(BaseModel):
    total_servers: int
    active_server: str | None
    active_country: str | None
    client_connected: bool = False


class VpnClientStatusResponse(BaseModel):
    connected: bool = False
    active_server: str | None = None
    active_endpoint: str | None = None
    active_country: str | None = None
    active_country_code: str | None = None
    transfer_rx: int = 0
    transfer_tx: int = 0
    session_total_rx: int = 0
    session_total_tx: int = 0
    speed_rx_bps: int = 0
    speed_tx_bps: int = 0
    last_handshake: str | None = None
    uptime_seconds: int = 0

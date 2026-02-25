# --- Ajan: MIMAR (THE ARCHITECT) ---
# Soyut Temel Sinif: Tum ag suruculeri için HAL sozlesmesi.
# Bu, mimarinin temel tasi - her metod hem MockNetworkDriver (dev)
# hem de LinuxNetworkDriver (prod, Faz 3) tarafindan uygulanmalidir.

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseNetworkDriver(ABC):
    """Donanım Soyutlama Katmani (HAL) - ag işlemleri için.

    Faz 1: MockNetworkDriver (simulasyon)
    Faz 3: LinuxNetworkDriver (Raspberry Pi 5 produksiyon)
    """

    # ===== GUVENLIK DUVARI =====

    @abstractmethod
    async def apply_firewall_rule(self, rule: str) -> bool:
        """Bir nftables güvenlik duvarı kuralı uygula."""
        ...

    @abstractmethod
    async def remove_firewall_rule(self, rule: str) -> bool:
        """Bir nftables güvenlik duvarı kuralıni kaldir."""
        ...

    # ===== CIHAZ YONETIMI =====

    @abstractmethod
    async def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Su an bagli cihazlari MAC, IP, hostname ile dondur."""
        ...

    @abstractmethod
    async def get_interface_stats(self, interface: str) -> Dict[str, Any]:
        """Bir arayuz için TX/RX byte, paket, hata istatistiklerini dondur."""
        ...

    @abstractmethod
    async def get_bandwidth_usage(self) -> Dict[str, float]:
        """WAN ve LAN için anlik bant genisligi (Mbps) dondur."""
        ...

    @abstractmethod
    async def block_device(self, mac_address: str) -> bool:
        """MAC adresine göre bir cihazi engelle."""
        ...

    @abstractmethod
    async def unblock_device(self, mac_address: str) -> bool:
        """MAC adresine göre bir cihazin engelini kaldir."""
        ...

    @abstractmethod
    async def set_bandwidth_limit(self, mac_address: str, limit_mbps: int) -> bool:
        """Belirli bir cihaz için bant genisligi siniri koy."""
        ...

    # ===== DNS ENGELLEME (Faz 2) =====

    @abstractmethod
    async def get_dns_queries(self) -> List[Dict[str, Any]]:
        """Son DNS sorgu loglarını dondur."""
        ...

    @abstractmethod
    async def resolve_dns(self, domain: str, query_type: str = "A") -> Dict[str, Any]:
        """Bir domain için DNS cozumlemesi yap (engelleme kontrolü dahil)."""
        ...

    @abstractmethod
    async def load_blocked_domains(self, domains: set) -> bool:
        """Engellenen domain setini yukle (Redis veya dnsmasq)."""
        ...

    @abstractmethod
    async def add_blocked_domain(self, domain: str) -> bool:
        """Tek bir domaini engelleme listesine ekle."""
        ...

    @abstractmethod
    async def remove_blocked_domain(self, domain: str) -> bool:
        """Tek bir domaini engelleme listesinden cikar."""
        ...

    @abstractmethod
    async def is_domain_blocked(self, domain: str) -> bool:
        """Bir domainin engellenip engellenmedigini kontrol et."""
        ...

    @abstractmethod
    async def get_dns_stats(self) -> Dict[str, Any]:
        """DNS engelleme istatistiklerini dondur."""
        ...

    # ===== DHCP SUNUCU (Faz 2) =====

    @abstractmethod
    async def configure_dhcp_pool(self, pool_config: Dict[str, Any]) -> bool:
        """DHCP IP havuzu tanimla veya güncelle."""
        ...

    @abstractmethod
    async def remove_dhcp_pool(self, pool_id: str) -> bool:
        """DHCP havuzunu kaldir."""
        ...

    @abstractmethod
    async def get_dhcp_leases(self) -> List[Dict[str, Any]]:
        """Aktif DHCP kiralamalarini listele."""
        ...

    @abstractmethod
    async def add_static_lease(self, mac: str, ip: str, hostname: str = "") -> bool:
        """Statik IP ataması (MAC-IP reservasyonu) oluştur."""
        ...

    @abstractmethod
    async def remove_static_lease(self, mac: str) -> bool:
        """Statik IP atamasıni kaldir."""
        ...

    @abstractmethod
    async def get_dhcp_stats(self) -> Dict[str, Any]:
        """DHCP istatistiklerini dondur."""
        ...

    # ===== GUVENLIK DUVARI - PORT YONETIMI (Faz 2.5) =====

    @abstractmethod
    async def add_port_rule(self, rule_config: Dict[str, Any]) -> bool:
        """Port kuralı ekle (ac/kapat/yonlendir)."""
        ...

    @abstractmethod
    async def remove_port_rule(self, rule_id: str) -> bool:
        """Port kuralıni kaldir."""
        ...

    @abstractmethod
    async def scan_ports(self, target_ip: str, port_range: str = "1-1024") -> List[Dict[str, Any]]:
        """Port taramasi yap."""
        ...

    @abstractmethod
    async def get_firewall_stats(self) -> Dict[str, Any]:
        """Güvenlik duvarı istatistiklerini dondur."""
        ...

    # ===== VPN - WIREGUARD (Faz 2.5) =====

    @abstractmethod
    async def vpn_generate_keypair(self) -> Dict[str, str]:
        """WireGuard anahtar cifti oluştur."""
        ...

    @abstractmethod
    async def vpn_get_status(self) -> Dict[str, Any]:
        """VPN sunucu durumunu dondur."""
        ...

    @abstractmethod
    async def vpn_start(self) -> bool:
        """VPN sunucusunu başlat."""
        ...

    @abstractmethod
    async def vpn_stop(self) -> bool:
        """VPN sunucusunu durdur."""
        ...

    @abstractmethod
    async def vpn_add_peer(self, peer_config: Dict[str, Any]) -> Dict[str, str]:
        """VPN peer ekle, konfigurasyonunu dondur."""
        ...

    @abstractmethod
    async def vpn_remove_peer(self, public_key: str) -> bool:
        """VPN peer kaldir."""
        ...

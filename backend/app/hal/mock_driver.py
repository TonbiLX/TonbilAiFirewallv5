# --- Ajan: MIMAR (THE ARCHITECT) ---
# Gelistirme için Mock ag surucusu.
# Tum komutlar dev_execution.log'a kaydedilir.
# Cihaz, trafik, bant genisligi, DNS engelleme ve DHCP verisi simule edilir.

import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import redis.asyncio as aioredis

from app.hal.base_driver import BaseNetworkDriver

logger = logging.getLogger("tonbilai.mock_driver")

# Onceden tanimli simule cihazlar
MOCK_DEVICES = [
    {"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.101", "hostname": "Ahmet-iPhone",    "manufacturer": "Apple"},
    {"mac": "AA:BB:CC:DD:EE:02", "ip": "192.168.1.102", "hostname": "Elif-Tablet",      "manufacturer": "Samsung"},
    {"mac": "AA:BB:CC:DD:EE:03", "ip": "192.168.1.103", "hostname": "SmartTV-Salon",     "manufacturer": "LG"},
    {"mac": "AA:BB:CC:DD:EE:04", "ip": "192.168.1.104", "hostname": "Baba-Laptop",       "manufacturer": "Lenovo"},
    {"mac": "AA:BB:CC:DD:EE:05", "ip": "192.168.1.105", "hostname": "IoT-AkilliBulb-01", "manufacturer": "Philips"},
    {"mac": "AA:BB:CC:DD:EE:06", "ip": "192.168.1.106", "hostname": "Misafir-Telefon",   "manufacturer": "Xiaomi"},
    {"mac": "AA:BB:CC:DD:EE:07", "ip": "192.168.1.107", "hostname": "Anne-PC",           "manufacturer": "Dell"},
    {"mac": "AA:BB:CC:DD:EE:08", "ip": "192.168.1.108", "hostname": "Çocuk-Tablet",      "manufacturer": "Amazon"},
]

LOG_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "dev_execution.log"


class MockNetworkDriver(BaseNetworkDriver):
    """Gercek donanım olmadan ag işlemlerini simule eder."""

    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client
        self._blocked_macs: set = set()
        self._bandwidth_limits: dict = {}
        # DNS engelleme state
        self._blocked_domains: set = set()
        self._dns_query_count: int = 0
        self._dns_blocked_count: int = 0
        # DHCP state
        self._dhcp_pools: dict = {}
        self._dhcp_leases: dict = {}  # mac -> lease_info
        self._static_leases: dict = {}  # mac -> {ip, hostname}

    def _log_command(self, command: str):
        """Calistirilacak sistem komutlarini dev_execution.log'a kaydet."""
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] MOCK_EXEC: {command}\n"
        with open(LOG_FILE, "a") as f:
            f.write(entry)
        logger.info(f"MockDriver logged: {command}")

    # ===== GUVENLIK DUVARI =====

    async def apply_firewall_rule(self, rule: str) -> bool:
        self._log_command(f"nft add rule {rule}")
        return True

    async def remove_firewall_rule(self, rule: str) -> bool:
        self._log_command(f"nft delete rule {rule}")
        return True

    # ===== CIHAZ YONETIMI =====

    async def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Redis mock registrysinden cihazlari dondur."""
        devices = []
        for dev in MOCK_DEVICES:
            if dev["mac"] not in self._blocked_macs:
                is_online = random.random() > 0.15  # %85 olasilikla çevrimiçi
                devices.append({**dev, "is_online": is_online})

        # Redis'e kaydet (diger servisler için)
        for dev in devices:
            key = f"device:{dev['mac']}"
            await self._redis.hset(key, mapping={
                "ip": dev["ip"],
                "hostname": dev["hostname"],
                "manufacturer": dev["manufacturer"],
                "is_online": str(dev.get("is_online", True)),
                "last_seen": datetime.now().isoformat(),
            })
            await self._redis.expire(key, 300)  # 5 dk TTL
        return devices

    async def get_interface_stats(self, interface: str) -> Dict[str, Any]:
        return {
            "interface": interface,
            "rx_bytes": random.randint(100_000_000, 5_000_000_000),
            "tx_bytes": random.randint(50_000_000, 2_000_000_000),
            "rx_packets": random.randint(100_000, 5_000_000),
            "tx_packets": random.randint(50_000, 2_000_000),
            "rx_errors": random.randint(0, 10),
            "tx_errors": random.randint(0, 5),
        }

    async def get_bandwidth_usage(self) -> Dict[str, float]:
        return {
            "wan_download_mbps": round(random.uniform(20.0, 95.0), 2),
            "wan_upload_mbps": round(random.uniform(5.0, 25.0), 2),
            "lan_throughput_mbps": round(random.uniform(50.0, 800.0), 2),
            "timestamp": datetime.now().isoformat(),
        }

    async def block_device(self, mac_address: str) -> bool:
        self._blocked_macs.add(mac_address)
        self._log_command(
            f"nft add rule inet filter forward ether saddr {mac_address} drop"
        )
        return True

    async def unblock_device(self, mac_address: str) -> bool:
        self._blocked_macs.discard(mac_address)
        self._log_command(
            f"nft delete rule inet filter forward ether saddr {mac_address} drop"
        )
        return True

    async def set_bandwidth_limit(self, mac_address: str, limit_mbps: int) -> bool:
        self._bandwidth_limits[mac_address] = limit_mbps
        self._log_command(
            f"tc qdisc add dev lan0 root handle 1: htb; "
            f"tc class add dev lan0 parent 1: classid 1:{mac_address[-2:]} htb rate {limit_mbps}mbit"
        )
        return True

    # ===== DNS ENGELLEME =====

    async def get_dns_queries(self) -> List[Dict[str, Any]]:
        """DNS sorgu loglari oluştur (engelleme simule ederek)."""
        domains = [
            ("youtube.com", "streaming"), ("google.com", "search"),
            ("instagram.com", "social"), ("tiktok.com", "social"),
            ("netflix.com", "streaming"), ("gaming-site.com", "gaming"),
            ("school-portal.edu.tr", "education"), ("kumar-sitesi.bet", "gambling"),
            ("news.com.tr", "news"), ("stackoverflow.com", "development"),
            ("ads.doubleclick.net", "advertising"), ("tracker.analytics.com", "tracking"),
            ("malware-c2.evil", "malicious"), ("ad.banner-network.com", "advertising"),
        ]
        queries = []
        for _ in range(random.randint(5, 15)):
            domain, category = random.choice(domains)
            device = random.choice(MOCK_DEVICES)
            resolution = await self.resolve_dns(domain)
            queries.append({
                "timestamp": datetime.now().isoformat(),
                "device_mac": device["mac"],
                "client_ip": device["ip"],
                "domain": domain,
                "category": category,
                "query_type": random.choice(["A", "AAAA", "CNAME"]),
                "blocked": resolution["blocked"],
                "block_reason": resolution.get("block_reason"),
                "answer_ip": resolution["answer"],
                "response_ms": resolution["response_ms"],
            })
        return queries

    async def resolve_dns(self, domain: str, query_type: str = "A") -> Dict[str, Any]:
        """DNS cozumlemesi simule et, engelleme kontrolü ile."""
        self._dns_query_count += 1
        is_blocked = await self.is_domain_blocked(domain)

        if is_blocked:
            self._dns_blocked_count += 1
            self._log_command(f"dnsmasq: BLOCKED {domain} -> 0.0.0.0")
            return {
                "domain": domain,
                "query_type": query_type,
                "blocked": True,
                "answer": "0.0.0.0",
                "response_ms": 1,
                "block_reason": "blocklist",
            }

        fake_ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        response_ms = random.randint(5, 150)
        self._log_command(f"dnsmasq: RESOLVE {domain} ({query_type}) -> {fake_ip} [{response_ms}ms]")
        return {
            "domain": domain,
            "query_type": query_type,
            "blocked": False,
            "answer": fake_ip,
            "response_ms": response_ms,
            "block_reason": None,
        }

    async def load_blocked_domains(self, domains: set) -> bool:
        """Redis SET'e tum engelli domainleri yukle."""
        self._blocked_domains = domains
        if domains:
            await self._redis.delete("dns:blocked_domains")
            pipe = self._redis.pipeline()
            for domain in domains:
                pipe.sadd("dns:blocked_domains", domain)
            await pipe.execute()
        self._log_command(f"dnsmasq: Loaded {len(domains)} blocked domains into sinkhole")
        return True

    async def add_blocked_domain(self, domain: str) -> bool:
        self._blocked_domains.add(domain)
        await self._redis.sadd("dns:blocked_domains", domain)
        self._log_command(f"dnsmasq: Added block for {domain}")
        return True

    async def remove_blocked_domain(self, domain: str) -> bool:
        self._blocked_domains.discard(domain)
        await self._redis.srem("dns:blocked_domains", domain)
        self._log_command(f"dnsmasq: Removed block for {domain}")
        return True

    async def is_domain_blocked(self, domain: str) -> bool:
        """Domain engel kontrolü: tam esleme + ust domain yuruyusu."""
        if await self._redis.sismember("dns:blocked_domains", domain):
            return True
        # Ust domain kontrolü (ads.example.com -> example.com)
        parts = domain.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if await self._redis.sismember("dns:blocked_domains", parent):
                return True
        return domain in self._blocked_domains

    async def get_dns_stats(self) -> Dict[str, Any]:
        blocked_count = await self._redis.scard("dns:blocked_domains")
        return {
            "total_blocked_domains": blocked_count or len(self._blocked_domains),
            "dns_queries_total": self._dns_query_count,
            "dns_queries_blocked": self._dns_blocked_count,
            "block_percentage": round(
                (self._dns_blocked_count / max(self._dns_query_count, 1)) * 100, 1
            ),
        }

    # ===== DHCP SUNUCU =====

    async def configure_dhcp_pool(self, pool_config: Dict[str, Any]) -> bool:
        """DHCP havuzu tanimla veya güncelle."""
        pool_id = str(pool_config.get("id", pool_config.get("name", "default")))
        self._dhcp_pools[pool_id] = pool_config
        self._log_command(
            f"dnsmasq --dhcp-range={pool_config['range_start']},"
            f"{pool_config['range_end']},"
            f"{pool_config.get('netmask', '255.255.255.0')},"
            f"{pool_config.get('lease_time_seconds', 86400)}s"
        )
        # Redis'e kaydet
        await self._redis.hset(f"dhcp:pool:{pool_id}", mapping={
            "name": pool_config.get("name", ""),
            "range_start": pool_config["range_start"],
            "range_end": pool_config["range_end"],
            "gateway": pool_config.get("gateway", "192.168.1.1"),
            "enabled": str(pool_config.get("enabled", True)),
        })
        return True

    async def remove_dhcp_pool(self, pool_id: str) -> bool:
        self._dhcp_pools.pop(pool_id, None)
        await self._redis.delete(f"dhcp:pool:{pool_id}")
        self._log_command(f"dnsmasq: Removed DHCP pool {pool_id}")
        return True

    async def get_dhcp_leases(self) -> List[Dict[str, Any]]:
        """Aktif DHCP kiralamalarini dondur (mock)."""
        leases = []
        now = datetime.now()
        for dev in MOCK_DEVICES:
            mac = dev["mac"]
            is_static = mac in self._static_leases
            lease_start = now - timedelta(hours=random.randint(1, 23))
            lease_end = lease_start + timedelta(seconds=86400 if not is_static else 0)
            remaining = max(0, int((lease_end - now).total_seconds())) if not is_static else None

            ip = self._static_leases[mac]["ip"] if is_static else dev["ip"]

            leases.append({
                "mac_address": mac,
                "ip_address": ip,
                "hostname": dev["hostname"],
                "lease_start": lease_start.isoformat(),
                "lease_end": lease_end.isoformat() if not is_static else None,
                "remaining_seconds": remaining,
                "is_static": is_static,
            })

            # Redis'e kaydet
            await self._redis.hset(f"dhcp:lease:{mac}", mapping={
                "ip": ip,
                "hostname": dev["hostname"],
                "lease_start": lease_start.isoformat(),
                "is_static": str(is_static),
            })
            await self._redis.expire(f"dhcp:lease:{mac}", 300)

        return leases

    async def add_static_lease(self, mac: str, ip: str, hostname: str = "") -> bool:
        self._static_leases[mac] = {"ip": ip, "hostname": hostname}
        self._log_command(f"dnsmasq: dhcp-host={mac},{ip},{hostname}")
        await self._redis.hset(f"dhcp:static:{mac}", mapping={
            "ip": ip,
            "hostname": hostname,
        })
        return True

    async def remove_static_lease(self, mac: str) -> bool:
        self._static_leases.pop(mac, None)
        await self._redis.delete(f"dhcp:static:{mac}")
        self._log_command(f"dnsmasq: Removed static lease for {mac}")
        return True

    async def get_dhcp_stats(self) -> Dict[str, Any]:
        """DHCP istatistikleri."""
        total_ips = 0
        for pool in self._dhcp_pools.values():
            start_parts = pool["range_start"].split(".")
            end_parts = pool["range_end"].split(".")
            total_ips += int(end_parts[3]) - int(start_parts[3]) + 1

        assigned = len(MOCK_DEVICES)
        static_count = len(self._static_leases)

        return {
            "total_pools": len(self._dhcp_pools),
            "active_pools": sum(1 for p in self._dhcp_pools.values() if p.get("enabled", True)),
            "total_ips": total_ips if total_ips > 0 else 101,
            "assigned_ips": assigned,
            "available_ips": max(0, (total_ips if total_ips > 0 else 101) - assigned),
            "static_leases": static_count,
            "dynamic_leases": assigned - static_count,
        }

    # ===== GUVENLIK DUVARI - PORT YONETIMI (Faz 2.5) =====

    async def add_port_rule(self, rule_config: Dict[str, Any]) -> bool:
        port = rule_config.get("port", "any")
        protocol = rule_config.get("protocol", "tcp")
        action = rule_config.get("action", "drop")
        direction = rule_config.get("direction", "inbound")
        self._log_command(
            f"nft add rule inet filter {direction} {protocol} dport {port} {action}"
        )
        return True

    async def remove_port_rule(self, rule_id: str) -> bool:
        self._log_command(f"nft delete rule inet filter handle {rule_id}")
        return True

    async def scan_ports(self, target_ip: str, port_range: str = "1-1024") -> List[Dict[str, Any]]:
        """Mock port taramasi - yaygin portlari simule et."""
        common_ports = {
            22: ("open", "ssh"), 53: ("open", "dns"), 80: ("open", "http"),
            443: ("open", "https"), 8000: ("open", "http-alt"), 8080: ("closed", "http-proxy"),
            3306: ("filtered", "mysql"), 5173: ("open", "vite-dev"),
            6379: ("filtered", "redis"), 51820: ("closed", "wireguard"),
        }
        results = []
        start, end = port_range.split("-")
        for port in range(int(start), min(int(end) + 1, int(start) + 100)):
            if port in common_ports:
                state, service = common_ports[port]
                results.append({
                    "port": port, "protocol": "tcp",
                    "state": state, "service": service,
                })
        self._log_command(f"nmap -sS {target_ip} -p {port_range}")
        return results

    async def get_firewall_stats(self) -> Dict[str, Any]:
        return {
            "total_rules": random.randint(8, 15),
            "active_rules": random.randint(6, 12),
            "inbound_rules": random.randint(3, 8),
            "outbound_rules": random.randint(2, 5),
            "blocked_packets_24h": random.randint(500, 5000),
            "open_ports": [22, 53, 80, 443, 8000, 5173],
        }

    # ===== VPN - WIREGUARD (Faz 2.5) =====

    async def vpn_generate_keypair(self) -> Dict[str, str]:
        """Mock WireGuard anahtar cifti oluştur."""
        import base64
        import os
        private = base64.b64encode(os.urandom(32)).decode()
        public = base64.b64encode(os.urandom(32)).decode()
        self._log_command("wg genkey | tee /etc/wireguard/private.key | wg pubkey > /etc/wireguard/public.key")
        return {"private_key": private, "public_key": public}

    async def vpn_get_status(self) -> Dict[str, Any]:
        return {
            "interface": "wg0",
            "listening_port": 51820,
            "public_key": "mock_server_public_key_base64==",
            "peers": [],
            "active": False,
        }

    async def vpn_start(self) -> bool:
        self._log_command("wg-quick up wg0")
        return True

    async def vpn_stop(self) -> bool:
        self._log_command("wg-quick down wg0")
        return True

    async def vpn_add_peer(self, peer_config: Dict[str, Any]) -> Dict[str, str]:
        keys = await self.vpn_generate_keypair()
        name = peer_config.get("name", "peer")
        allowed_ips = peer_config.get("allowed_ips", "10.0.0.2/32")
        self._log_command(
            f"wg set wg0 peer {keys['public_key']} allowed-ips {allowed_ips}"
        )
        config = (
            f"[Interface]\n"
            f"PrivateKey = {keys['private_key']}\n"
            f"Address = {allowed_ips}\n"
            f"DNS = 10.0.0.1\n\n"
            f"[Peer]\n"
            f"PublicKey = mock_server_public_key_base64==\n"
            f"Endpoint = YOUR_SERVER_IP:51820\n"
            f"AllowedIPs = 0.0.0.0/0\n"
            f"PersistentKeepalive = 25\n"
        )
        return {
            "public_key": keys["public_key"],
            "private_key": keys["private_key"],
            "config": config,
        }

    async def vpn_remove_peer(self, public_key: str) -> bool:
        self._log_command(f"wg set wg0 peer {public_key} remove")
        return True

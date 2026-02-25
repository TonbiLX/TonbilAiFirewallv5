# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Linux ag surucusu: MockNetworkDriver'i genisletir.
# DHCP: gercek dnsmasq entegrasyonu
# Firewall: gercek nftables kurallari
# Cihaz engelleme: nftables MAC seti
# Bant genişliği: tc HTB siniflandirma
# VPN: gercek WireGuard komutlari

import asyncio
import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

import redis.asyncio as aioredis

from app.hal.mock_driver import MockNetworkDriver
from app.hal import linux_dhcp_driver as dhcp
from app.hal import linux_nftables as nft
from app.hal import linux_tc as tc

logger = logging.getLogger("tonbilai.linux_driver")


class LinuxNetworkDriver(MockNetworkDriver):
    """Gercek Linux ag surucusu.
    DHCP: dnsmasq entegrasyonu (config yazma + lease okuma)
    Firewall: gercek nftables kural yönetimi
    Cihaz Engelleme: nftables MAC seti
    Bant Genisligi: tc HTB siniflandirma
    VPN: gercek WireGuard komutlari
    """

    def __init__(self, redis_client: aioredis.Redis):
        super().__init__(redis_client)
        self._static_leases_db: List[Dict[str, Any]] = []
        self._bandwidth_limits: dict = {}  # mac -> limit_mbps
        logger.info("LinuxNetworkDriver başlatildi (DHCP+Firewall+VPN: gercek)")

    # ===== BASLANGIC SENKRONIZASYONU =====

    async def initialize(self):
        """Sistem baslangiçinda nftables tablolarini ve kurallari hazirla."""
        try:
            await nft.ensure_tonbilai_table()
            logger.info("nftables tonbilai tablosu hazir")
        except Exception as e:
            logger.error(f"nftables başlangıç hatasi: {e}")

    # ===== GUVENLIK DUVARI - GERCEK NFTABLES =====

    async def apply_firewall_rule(self, rule: str) -> bool:
        """nftables firewall kuralı uygula."""
        try:
            await nft.run_nft(f"add rule inet tonbilai input {rule}".split())
            return True
        except Exception as e:
            logger.error(f"Firewall kuralı uygulanamadi: {e}")
            return False

    async def remove_firewall_rule(self, rule: str) -> bool:
        """nftables firewall kuralıni kaldir."""
        try:
            await nft.run_nft(f"delete rule inet tonbilai input {rule}".split(), check=False)
            return True
        except Exception as e:
            logger.error(f"Firewall kuralı kaldirilamadi: {e}")
            return False

    async def add_port_rule(self, rule_config: Dict[str, Any]) -> bool:
        """Port kuralı ekle (nftables)."""
        try:
            rule_expr = nft.build_nft_rule_expr(rule_config)
            direction = rule_config.get("direction", "inbound")
            chain = "input" if direction == "inbound" else ("forward" if direction == "forward" else "output")
            rule_id = rule_config.get("id", 0)
            comment = f"fw_rule_{rule_id}"

            cmd = f"add rule inet tonbilai {chain} {rule_expr} comment \"{comment}\""
            await nft.run_nft(cmd.split())
            logger.info(f"Port kuralı eklendi: [{chain}] {rule_expr}")
            return True
        except Exception as e:
            logger.error(f"Port kuralı eklenemedi: {e}")
            return False

    async def remove_port_rule(self, rule_id: str) -> bool:
        """Port kuralıni handle/comment ile kaldir."""
        try:
            comment = f"fw_rule_{rule_id}"
            for chain in ("input", "forward", "output"):
                out = await nft.run_nft(["-a", "list", "chain", "inet", "tonbilai", chain], check=False)
                for line in out.splitlines():
                    if comment in line:
                        match = re.search(r"# handle (\d+)", line)
                        if match:
                            handle = int(match.group(1))
                            await nft.run_nft(
                                ["delete", "rule", "inet", "tonbilai", chain, "handle", str(handle)],
                                check=False,
                            )
                            logger.info(f"Port kuralı silindi: {chain} handle {handle}")
            return True
        except Exception as e:
            logger.error(f"Port kuralı kaldirilamadi: {e}")
            return False

    async def scan_ports(self, target_ip: str, port_range: str = "1-1024") -> List[Dict[str, Any]]:
        """Gercek port taramasi."""
        return await nft.scan_ports_real(target_ip, port_range)

    async def get_firewall_stats(self) -> Dict[str, Any]:
        """Gercek firewall istatistikleri."""
        return await nft.get_firewall_stats()

    # ===== CIHAZ ENGELLEME - GERCEK NFTABLES MAC SETI =====

    async def block_device(self, mac_address: str) -> bool:
        """MAC adresini nftables engelleme setine ekle."""
        try:
            # MAC doğrulama
            if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac_address):
                logger.error(f"Geçersiz MAC adresi: {mac_address}")
                return False

            await nft.add_blocked_mac(mac_address)
            self._blocked_macs.add(mac_address)
            return True
        except Exception as e:
            logger.error(f"Cihaz engellenemedi ({mac_address}): {e}")
            return False

    async def unblock_device(self, mac_address: str) -> bool:
        """MAC adresini nftables engelleme setinden cikar."""
        try:
            await nft.remove_blocked_mac(mac_address)
            self._blocked_macs.discard(mac_address)
            return True
        except Exception as e:
            logger.error(f"Cihaz engeli kaldirilamadi ({mac_address}): {e}")
            return False

    # ===== BANT GENISLIGI SINIRLANDIRMA - GERCEK TC =====

    async def set_bandwidth_limit(self, mac_address: str, limit_mbps: int) -> bool:
        """Cihaz için gercek bant genisligi siniri (tc HTB)."""
        try:
            if limit_mbps <= 0:
                # Siniri kaldir
                await tc.remove_device_limit(mac_address)
                self._bandwidth_limits.pop(mac_address, None)
                logger.info(f"Bant genişliği siniri kaldırıldı: {mac_address}")
            else:
                await tc.add_device_limit(mac_address, limit_mbps)
                self._bandwidth_limits[mac_address] = limit_mbps
                logger.info(f"Bant genişliği siniri: {mac_address} -> {limit_mbps}Mbps")
            return True
        except Exception as e:
            logger.error(f"Bant genişliği siniri ayarlanamadi ({mac_address}): {e}")
            return False

    # ===== CIHAZ YONETIMI - GERCEK VERILER =====

    async def get_connected_devices(self) -> List[Dict[str, Any]]:
        """ARP tablosundan bagli cihazlari al."""
        devices = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "ip", "neigh", "show",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode()

            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and "lladdr" in parts:
                    ip = parts[0]
                    mac_idx = parts.index("lladdr") + 1
                    mac = parts[mac_idx] if mac_idx < len(parts) else ""
                    state = parts[-1] if parts else ""

                    if mac and ip.startswith("192.168."):
                        is_online = state in ("REACHABLE", "STALE", "DELAY")
                        devices.append({
                            "mac": mac.upper(),
                            "ip": ip,
                            "hostname": "",
                            "manufacturer": "",
                            "is_online": is_online,
                        })

            # Redis'e kaydet
            for dev in devices:
                key = f"device:{dev['mac']}"
                await self._redis.hset(key, mapping={
                    "ip": dev["ip"],
                    "hostname": dev["hostname"],
                    "manufacturer": dev["manufacturer"],
                    "is_online": str(dev["is_online"]),
                    "last_seen": datetime.now().isoformat(),
                })
                await self._redis.expire(key, 300)

        except Exception as e:
            logger.error(f"Cihaz listesi hatasi: {e}")

        return devices

    async def get_interface_stats(self, interface: str) -> Dict[str, Any]:
        """Gercek arayuz istatistikleri (/sys/class/net)."""
        stats = {
            "interface": interface,
            "rx_bytes": 0, "tx_bytes": 0,
            "rx_packets": 0, "tx_packets": 0,
            "rx_errors": 0, "tx_errors": 0,
        }

        base = Path(f"/sys/class/net/{interface}/statistics")
        if not base.exists():
            return stats

        for key in ("rx_bytes", "tx_bytes", "rx_packets", "tx_packets", "rx_errors", "tx_errors"):
            path = base / key
            try:
                stats[key] = int(path.read_text().strip())
            except (FileNotFoundError, ValueError):
                pass

        return stats

    async def get_bandwidth_usage(self) -> Dict[str, float]:
        """Gercek bant genisligi (br0 istatistiklerinden)."""
        stats = await self.get_interface_stats("br0")
        return {
            "wan_download_mbps": round(stats["rx_bytes"] / 1_000_000 * 8, 2),
            "wan_upload_mbps": round(stats["tx_bytes"] / 1_000_000 * 8, 2),
            "lan_throughput_mbps": round((stats["rx_bytes"] + stats["tx_bytes"]) / 1_000_000 * 8, 2),
            "timestamp": datetime.now().isoformat(),
        }

    # ===== VPN - GERCEK WIREGUARD =====

    async def vpn_generate_keypair(self) -> Dict[str, str]:
        """Gercek WireGuard anahtar cifti oluştur."""
        try:
            private_key = await self._run_cmd(["wg", "genkey"])
            proc = await asyncio.create_subprocess_exec(
                "wg", "pubkey",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate(input=private_key.encode())
            public_key = stdout.decode().strip()
            return {"private_key": private_key, "public_key": public_key}
        except Exception as e:
            logger.error(f"WireGuard anahtar oluşturma hatasi: {e}")
            return await super().vpn_generate_keypair()

    async def vpn_get_status(self) -> Dict[str, Any]:
        """Gercek WireGuard sunucu durumu."""
        result = {
            "interface": "wg0",
            "listening_port": 51820,
            "public_key": None,
            "peers": [],
            "active": False,
        }
        try:
            out = await self._run_cmd(["sudo", "wg", "show", "wg0"], check=False)
            if out and "Unable to access" not in out:
                result["active"] = True
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("public key:"):
                        result["public_key"] = line.split(":", 1)[1].strip()
                    elif line.startswith("listening port:"):
                        result["listening_port"] = int(line.split(":", 1)[1].strip())
        except Exception as e:
            logger.error(f"WireGuard durum hatasi: {e}")
        return result

    async def vpn_start(self) -> bool:
        """WireGuard sunucusunu başlat."""
        try:
            await self._run_cmd(["sudo", "wg-quick", "up", "wg0"])
            return True
        except Exception as e:
            logger.error(f"WireGuard başlatilamadi: {e}")
            return False

    async def vpn_stop(self) -> bool:
        """WireGuard sunucusunu durdur."""
        try:
            await self._run_cmd(["sudo", "wg-quick", "down", "wg0"], check=False)
            return True
        except Exception as e:
            logger.error(f"WireGuard durdurulamadi: {e}")
            return False

    async def vpn_add_peer(self, peer_config: Dict[str, Any]) -> Dict[str, str]:
        """Gercek WireGuard peer ekle."""
        try:
            keys = await self.vpn_generate_keypair()
            allowed_ips = peer_config.get("allowed_ips", "10.13.13.2/32")

            # Canlı WireGuard'a ekle
            await self._run_cmd([
                "sudo", "wg", "set", "wg0",
                "peer", keys["public_key"],
                "allowed-ips", allowed_ips,
            ], check=False)

            name = peer_config.get("name", "peer")
            config = (
                f"[Interface]\n"
                f"PrivateKey = {keys['private_key']}\n"
                f"Address = {allowed_ips}\n"
                f"DNS = 192.168.1.2\n\n"
                f"[Peer]\n"
                f"PublicKey = {keys.get('server_public_key', '')}\n"
                f"Endpoint = guard.tonbilx.com:51820\n"
                f"AllowedIPs = 0.0.0.0/0, ::/0\n"
                f"PersistentKeepalive = 25\n"
            )
            return {
                "public_key": keys["public_key"],
                "private_key": keys["private_key"],
                "config": config,
            }
        except Exception as e:
            logger.error(f"Peer eklenemedi: {e}")
            return await super().vpn_add_peer(peer_config)

    async def vpn_remove_peer(self, public_key: str) -> bool:
        """WireGuard peer kaldir."""
        try:
            await self._run_cmd([
                "sudo", "wg", "set", "wg0",
                "peer", public_key, "remove",
            ], check=False)
            return True
        except Exception as e:
            logger.error(f"Peer kaldirilamadi: {e}")
            return False

    # ===== DHCP - dnsmasq entegrasyonu =====

    async def configure_dhcp_pool(self, pool_config: Dict[str, Any]) -> bool:
        """DHCP havuzu için dnsmasq config dosyasi oluştur."""
        pool_id = pool_config.get("id")
        if not pool_id:
            return False

        config_content = dhcp.generate_pool_config(pool_config)
        success = dhcp.write_pool_config(pool_id, config_content)
        if success:
            dhcp.trigger_reload()
        return success

    async def remove_dhcp_pool(self, pool_id: str) -> bool:
        """DHCP havuz config dosyasini sil."""
        try:
            pid = int(pool_id)
        except ValueError:
            return False
        success = dhcp.remove_pool_config(pid)
        if success:
            dhcp.trigger_reload()
        return success

    async def get_dhcp_leases(self) -> List[Dict[str, Any]]:
        """dnsmasq lease dosyasindan aktif kiralamalari oku."""
        raw_leases = dhcp.parse_leases_file()
        leases = []
        for lease in raw_leases:
            if not lease.get("is_expired", True):
                leases.append({
                    "mac": lease["mac_address"],
                    "ip": lease["ip_address"],
                    "hostname": lease["hostname"],
                    "lease_end": lease["lease_end"].isoformat() if lease["lease_end"] else None,
                })
        return leases

    async def add_static_lease(self, mac: str, ip: str, hostname: str = "") -> bool:
        """Statik IP ataması - dnsmasq config'e yaz."""
        found = False
        for lease in self._static_leases_db:
            if lease["mac_address"].upper() == mac.upper():
                lease["ip_address"] = ip
                lease["hostname"] = hostname
                found = True
                break
        if not found:
            self._static_leases_db.append({
                "mac_address": mac.upper(),
                "ip_address": ip,
                "hostname": hostname,
            })

        success = dhcp.write_static_leases_config(self._static_leases_db)
        if success:
            dhcp.trigger_reload()
        return success

    async def remove_static_lease(self, mac: str) -> bool:
        """Statik IP atamasıni kaldir - config'den cikar."""
        self._static_leases_db = [
            l for l in self._static_leases_db
            if l["mac_address"].upper() != mac.upper()
        ]
        success = dhcp.write_static_leases_config(self._static_leases_db)
        if success:
            dhcp.trigger_reload()
        return success

    async def get_dhcp_stats(self) -> Dict[str, Any]:
        """dnsmasq lease dosyasindan istatistik cikar."""
        leases = dhcp.parse_leases_file()
        active = [l for l in leases if not l.get("is_expired", True)]
        return {
            "total_leases": len(active),
            "static_leases": len(self._static_leases_db),
            "dynamic_leases": len(active) - len(self._static_leases_db),
            "dnsmasq_running": dhcp.is_dnsmasq_running(),
        }

    # ===== YARDIMCI =====

    async def _run_cmd(self, cmd: list, check: bool = True) -> str:
        """Sistem komutu calistir."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0 and check:
            raise RuntimeError(f"Command failed: {' '.join(cmd)} -> {err}")
        return out

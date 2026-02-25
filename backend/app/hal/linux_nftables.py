# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# nftables yardimci modulu: Gercek nft komutlari calistirma.
# LinuxNetworkDriver tarafindan kullanilir.

import asyncio
import json
import logging
import re
import socket
from typing import List, Dict, Any, Optional

logger = logging.getLogger("tonbilai.nftables")

NFT_BIN = "/usr/sbin/nft"
TABLE_NAME = "inet tonbilai"
BLOCKED_MACS_SET = "blocked_macs"
BLOCKED_IPS_SET = "blocked_ips"
BRIDGE_TABLE = "bridge accounting"
BRIDGE_CHAIN = "per_device"
BRIDGE_MASQ_TABLE = "bridge masquerade_fix"
BRIDGE_MASQ_CHAIN = "mac_rewrite"


async def run_nft(args: List[str], check: bool = True) -> str:
    """nft komutunu sudo ile calistir."""
    cmd = ["sudo", NFT_BIN] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode().strip()
    err = stderr.decode().strip()

    if proc.returncode != 0 and check:
        logger.error(f"nft komutu başarısız: {' '.join(cmd)} -> {err}")
        raise RuntimeError(f"nft error: {err}")

    if proc.returncode != 0:
        logger.warning(f"nft komutu uyari: {' '.join(cmd)} -> {err}")

    return out


async def ensure_tonbilai_table():
    """TonbilAiOS nftables tablo ve zincirlerini oluştur (yoksa)."""
    # Tablo var mi kontrol et
    out = await run_nft(["-j", "list", "tables"], check=False)

    # Tablo yoksa oluştur
    ruleset = await run_nft(["list", "ruleset"], check=False)
    if "table inet tonbilai" not in ruleset:
        logger.info("inet tonbilai tablosu oluşturuluyor...")

        nft_commands = """
table inet tonbilai {
    set blocked_macs {
        type ether_addr;
    }

    set blocked_ips {
        type ipv4_addr;
        flags timeout;
    }

    chain input {
        type filter hook input priority 0; policy accept;
        ct state established,related accept
        tcp flags & (fin | syn) == fin | syn drop
        tcp flags & (syn | rst) == syn | rst drop
        ip saddr @blocked_ips counter drop
    }

    chain forward {
        type filter hook forward priority 0; policy accept;
        ct state established,related accept
        ether saddr @blocked_macs counter drop
        ip saddr @blocked_ips counter drop
        ip daddr @blocked_ips counter drop
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
"""
        # nft -f ile toplu komut calistir
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=nft_commands.encode())
        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.error(f"Tablo oluşturma hatasi: {err}")
            raise RuntimeError(f"nft table create error: {err}")

        logger.info("inet tonbilai tablosu oluşturuldu (DDoS korumasi dahil)")
    else:
        logger.info("inet tonbilai tablosu zaten mevcut")

    # VPN masquerade için inet nat postrouting zincirini oluştur
    await ensure_nat_postrouting_chain()


async def ensure_nat_postrouting_chain():
    """inet nat postrouting zincirini oluştur (yoksa).

    inet nat tablosu zaten mevcut (DNS prerouting redirect için).
    Sadece postrouting chain eksikse eklenir. VPN masquerade için gerekli.
    """
    out = await run_nft(["list", "table", "inet", "nat"], check=False)
    if "chain postrouting" in out:
        logger.debug("inet nat postrouting zinciri zaten mevcut")
        return

    logger.info("inet nat postrouting zinciri oluşturuluyor...")
    nft_cmd = 'add chain inet nat postrouting { type nat hook postrouting priority 100 ; policy accept ; }'
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, nft_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        # Alternatif: -f ile dene
        proc2 = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc2.communicate(input=nft_cmd.encode())
        if proc2.returncode != 0:
            logger.error(f"postrouting chain oluşturulamadi: {stderr.decode()}")
            return

    logger.info("inet nat postrouting zinciri oluşturuldu")


def _validate_interface_name(interface: str) -> str:
    """Interface adini dogrula — command injection onlemi."""
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]{0,14}$', interface):
        raise ValueError(f"Geçersiz interface adi: {interface}")
    return interface


def _validate_subnet(subnet: str) -> str:
    """Subnet CIDR formatini dogrula — command injection onlemi."""
    import ipaddress
    try:
        ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        raise ValueError(f"Geçersiz subnet: {subnet}")
    return subnet


def _validate_mac(mac: str) -> str:
    """MAC adresi formatini dogrula — command injection onlemi."""
    if not re.match(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$', mac):
        raise ValueError(f"Geçersiz MAC adresi: {mac}")
    return mac.lower()


def _validate_ip(ip: str) -> str:
    """IP adresi veya CIDR formatini dogrula — command injection onlemi."""
    import ipaddress
    try:
        # CIDR veya tek IP
        if "/" in ip:
            ipaddress.ip_network(ip, strict=False)
        else:
            ipaddress.ip_address(ip)
    except ValueError:
        raise ValueError(f"Geçersiz IP adresi: {ip}")
    return ip


async def add_vpn_nft_rules(interface: str, subnet: str, is_client: bool = False):
    """VPN için nftables forward + masquerade kurallarini ekle.

    Her kural comment ile tanimlanir, remove_vpn_nft_rules() ile guvenle silinir.

    is_client=True: VPN client (dis VPN) — masquerade wg-client üzerinden
    is_client=False: VPN server (wg0) — masquerade br0 üzerinden
    """
    interface = _validate_interface_name(interface)
    subnet = _validate_subnet(subnet)

    if is_client:
        # VPN client: trafik wg-client üzerinden cikar, masquerade orada
        masq_rule = f'add rule inet nat postrouting oifname {interface} counter masquerade comment "vpn_{interface}_masq"'
    else:
        # VPN server: VPN peer trafiği br0'dan LAN'a cikar
        masq_rule = f'add rule inet nat postrouting oifname br0 ip saddr {subnet} counter masquerade comment "vpn_{interface}_masq"'

    rules = f"""
add rule inet tonbilai forward iifname {interface} counter accept comment "vpn_{interface}_fwd_in"
add rule inet tonbilai forward oifname {interface} counter accept comment "vpn_{interface}_fwd_out"
{masq_rule}
"""
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=rules.strip().encode())
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.error(f"VPN nft kural ekleme hatasi ({interface}): {err}")
        raise RuntimeError(f"VPN nft rules error: {err}")

    logger.info(f"VPN nftables kurallari eklendi: {interface} ({subnet}, client={is_client})")


async def remove_vpn_nft_rules(interface: str):
    """VPN için eklenmemiş nftables kurallarini comment bazli guvenle sil.

    Sadece vpn_{interface}_* comment'li kurallar silinir.
    Diger firewall kurallarina dokunulmaz.
    """
    interface = _validate_interface_name(interface)
    comment_prefix = f"vpn_{interface}_"

    chain_specs = [
        ("inet", "tonbilai", "forward"),
        ("inet", "nat", "postrouting"),
    ]

    removed = 0
    for family, table, chain in chain_specs:
        out = await run_nft(["-a", "list", "chain", family, table, chain], check=False)
        if not out:
            continue

        for line in out.splitlines():
            if comment_prefix not in line:
                continue
            handle_match = re.search(r"# handle (\d+)", line)
            if handle_match:
                handle = handle_match.group(1)
                await run_nft(
                    ["delete", "rule", family, table, chain, "handle", handle],
                    check=False,
                )
                removed += 1

    if removed:
        logger.info(f"VPN nftables kurallari silindi: {interface} ({removed} kural)")
    else:
        logger.debug(f"VPN nftables kuralı bulunamadı: {interface}")


def build_nft_rule_expr(rule: Dict[str, Any]) -> str:
    """FirewallRule dict'inden nftables kural ifadesi oluştur."""
    parts = []

    protocol = rule.get("protocol", "tcp")
    port = rule.get("port")
    port_end = rule.get("port_end")
    source_ip = rule.get("source_ip")
    dest_ip = rule.get("dest_ip")
    action = rule.get("action", "drop")
    log_packets = rule.get("log_packets", False)

    # Protokol filtresi
    if protocol in ("tcp", "udp"):
        parts.append(f"meta l4proto {protocol}")
    elif protocol == "both":
        parts.append("meta l4proto { tcp, udp }")
    elif protocol == "icmp":
        parts.append("ip protocol icmp")

    # Kaynak IP (doğrulanmış)
    if source_ip:
        source_ip = _validate_ip(source_ip)
        parts.append(f"ip saddr {source_ip}")

    # Hedef IP (doğrulanmış)
    if dest_ip:
        dest_ip = _validate_ip(dest_ip)
        parts.append(f"ip daddr {dest_ip}")

    # Port
    if port and protocol not in ("icmp", "all"):
        if port_end and port_end > port:
            parts.append(f"th dport {port}-{port_end}")
        else:
            parts.append(f"th dport {port}")

    # Loglama
    if log_packets:
        rule_name = rule.get("name", "rule")
        parts.append(f'log prefix "TONBILAI-{rule_name}: "')

    # Counter
    parts.append("counter")

    # Aksiyon
    parts.append(action)

    return " ".join(parts)


async def add_firewall_rule(chain: str, rule_expr: str, comment: str = "") -> Optional[int]:
    """Zincire kural ekle, handle dondur."""
    cmd = f"add rule {TABLE_NAME} {chain} {rule_expr}"
    if comment:
        cmd += f' comment "{comment}"'
    await run_nft(cmd.split())
    # Handle'i bul
    handle = await _get_last_rule_handle(chain)
    return handle


async def remove_firewall_rule_by_handle(chain: str, handle: int):
    """Handle ile kural sil."""
    await run_nft(["delete", "rule", "inet", "tonbilai", chain, "handle", str(handle)])


async def _get_last_rule_handle(chain: str) -> Optional[int]:
    """Zincirdeki son kuralın handle'ini dondur."""
    out = await run_nft(["-a", "list", "chain", "inet", "tonbilai", chain], check=False)
    handles = re.findall(r"# handle (\d+)", out)
    if handles:
        return int(handles[-1])
    return None


async def sync_firewall_rules(rules: List[Dict[str, Any]]):
    """DB'deki aktif kurallari nftables'a senkronize et.

    Mevcut dinamik kurallari temizleyip yeniden oluşturur.
    Sabit kurallar (DDoS korumasi) korunur.
    """
    # Input ve forward zincirlerindeki mevcut kurallari oku
    # Sadece comment'li kurallari temizle (dinamik kurallar)
    for chain in ("input", "forward", "output"):
        out = await run_nft(["-a", "list", "chain", "inet", "tonbilai", chain], check=False)
        for line in out.splitlines():
            if 'comment "fw_rule_' in line:
                match = re.search(r"# handle (\d+)", line)
                if match:
                    handle = int(match.group(1))
                    await run_nft(
                        ["delete", "rule", "inet", "tonbilai", chain, "handle", str(handle)],
                        check=False,
                    )

    # Kuralları öncelik sirasina göre ekle
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 100))
    for rule in sorted_rules:
        if not rule.get("enabled", True):
            continue

        direction = rule.get("direction", "inbound")
        if direction == "inbound":
            chain = "input"
        elif direction == "forward":
            chain = "forward"
        else:
            chain = "output"

        rule_expr = build_nft_rule_expr(rule)
        rule_id = rule.get("id", 0)
        comment = f"fw_rule_{rule_id}"

        try:
            cmd_str = f"add rule inet tonbilai {chain} {rule_expr} comment \"{comment}\""
            await run_nft(cmd_str.split())
            logger.debug(f"Firewall kuralı eklendi: [{chain}] {rule_expr}")
        except Exception as e:
            logger.error(f"Kural eklenemedi (id={rule_id}): {e}")


async def add_blocked_mac(mac: str):
    """MAC adresini engelleme setine ekle."""
    mac = _validate_mac(mac)
    await run_nft(["add", "element", "inet", "tonbilai", BLOCKED_MACS_SET, "{", mac, "}"])
    logger.info(f"MAC engellendi: {mac}")


async def remove_blocked_mac(mac: str):
    """MAC adresini engelleme setinden cikar."""
    mac = _validate_mac(mac)
    await run_nft(["delete", "element", "inet", "tonbilai", BLOCKED_MACS_SET, "{", mac, "}"], check=False)
    logger.info(f"MAC engeli kaldırıldı: {mac}")


async def sync_blocked_macs(macs: List[str]):
    """Engellenmis MAC listesini senkronize et."""
    # Mevcut seti temizle
    await run_nft(["flush", "set", "inet", "tonbilai", BLOCKED_MACS_SET], check=False)

    if not macs:
        return

    # Toplu ekle
    mac_list = ", ".join(m.lower() for m in macs)
    await run_nft(
        ["add", "element", "inet", "tonbilai", BLOCKED_MACS_SET, "{", mac_list, "}"],
        check=False,
    )
    logger.info(f"{len(macs)} MAC adresi engelleme setine eklendi")


async def add_blocked_ip(ip: str, timeout_seconds: int = 3600):
    """IP adresini engelleme setine ekle (sureli)."""
    await run_nft(
        ["add", "element", "inet", "tonbilai", BLOCKED_IPS_SET,
         "{", ip, "timeout", f"{timeout_seconds}s", "}"],
        check=False,
    )
    logger.info(f"IP engellendi: {ip} ({timeout_seconds}s)")


async def remove_blocked_ip(ip: str):
    """IP adresini engelleme setinden cikar."""
    await run_nft(
        ["delete", "element", "inet", "tonbilai", BLOCKED_IPS_SET, "{", ip, "}"],
        check=False,
    )
    logger.info(f"IP engeli kaldırıldı: {ip}")


async def get_firewall_stats() -> Dict[str, Any]:
    """Gercek firewall istatistiklerini dondur."""
    stats = {
        "total_rules": 0,
        "active_rules": 0,
        "inbound_rules": 0,
        "outbound_rules": 0,
        "blocked_packets_24h": 0,
        "open_ports": [],
        "blocked_macs_count": 0,
        "blocked_ips_count": 0,
    }

    try:
        # Kural sayilarini al
        ruleset = await run_nft(["list", "table", "inet", "tonbilai"], check=False)
        stats["total_rules"] = ruleset.count("comment \"fw_rule_")

        # Counter degerlerini topla (drop counter)
        for match in re.finditer(r"counter packets (\d+) bytes \d+ drop", ruleset):
            stats["blocked_packets_24h"] += int(match.group(1))

        # Engellenmis MAC sayısı
        mac_set = await run_nft(["list", "set", "inet", "tonbilai", BLOCKED_MACS_SET], check=False)
        mac_count = mac_set.count(":")  # Her MAC adresinde 5 adet : var
        stats["blocked_macs_count"] = mac_count // 5 if mac_count >= 5 else 0

        # Açık portlari bul
        stats["open_ports"] = await list_open_ports()

    except Exception as e:
        logger.error(f"Firewall stats hatasi: {e}")

    return stats


async def list_open_ports() -> List[int]:
    """Dinleyen portlari listele (ss -tuln)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ss", "-tuln",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        out = stdout.decode()

        ports = set()
        for line in out.splitlines()[1:]:  # Baslik satiri atla
            parts = line.split()
            if len(parts) >= 5:
                # Local Address:Port
                local = parts[4]
                if ":" in local:
                    port_str = local.rsplit(":", 1)[-1]
                    try:
                        port = int(port_str)
                        if port < 49152:  # Ephemeral portlari haric tut
                            ports.add(port)
                    except ValueError:
                        pass

        return sorted(ports)
    except Exception as e:
        logger.error(f"Port listesi hatasi: {e}")
        return []


async def scan_ports_real(target_ip: str, port_range: str = "1-1024") -> List[Dict[str, Any]]:
    """Basit TCP port taramasi."""
    results = []
    try:
        start, end = port_range.split("-")
        start_port = int(start)
        end_port = min(int(end), start_port + 200)  # Maks 200 port

        # Bilinen servis isimleri
        known_services = {
            22: "ssh", 53: "dns", 80: "http", 443: "https",
            853: "dns-over-tls", 3306: "mysql", 5432: "postgres",
            6379: "redis", 8000: "http-alt", 8080: "http-proxy",
            51820: "wireguard",
        }

        for port in range(start_port, end_port + 1):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((target_ip, port))
                sock.close()

                if result == 0:
                    service = known_services.get(port, "unknown")
                    results.append({
                        "port": port,
                        "protocol": "tcp",
                        "state": "open",
                        "service": service,
                    })
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Port tarama hatasi: {e}")

    return results


async def persist_nftables():
    """Mevcut ruleset'i /etc/nftables.conf'a kaydet."""
    try:
        ruleset = await run_nft(["list", "ruleset"])
        # Flush komutuyla basla
        content = "#!/usr/sbin/nft -f\nflush ruleset\n\n" + ruleset + "\n"

        proc = await asyncio.create_subprocess_exec(
            "sudo", "tee", "/etc/nftables.conf",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate(input=content.encode())
        if proc.returncode == 0:
            logger.info("nftables kurallari /etc/nftables.conf'a kaydedildi")
        else:
            logger.error("nftables persist hatasi")
    except Exception as e:
        logger.error(f"nftables persist hatasi: {e}")


# ============================================================================
# Bridge Per-Device Bandwidth Counter Fonksiyonlari
# nftables bridge tablosu ile MAC bazli gercek zamanli byte/paket sayacı
# ============================================================================

async def ensure_bridge_accounting_chain():
    """Bridge per_device accounting zincirini oluştur (yoksa).

    Yapi:
        table bridge accounting {
            chain per_device {
                type filter hook forward priority -2; policy accept;
            }
        }
    """
    ruleset = await run_nft(["list", "ruleset"], check=False)
    if "table bridge accounting" in ruleset:
        logger.debug("Bridge accounting tablosu zaten mevcut")
        return

    logger.info("Bridge accounting tablosu oluşturuluyor...")
    nft_commands = """
table bridge accounting {
    chain per_device {
        type filter hook forward priority -2; policy accept;
    }
}
"""
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=nft_commands.encode())
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.error(f"Bridge accounting tablo oluşturma hatasi: {err}")
        raise RuntimeError(f"bridge accounting create error: {err}")

    logger.info("Bridge accounting tablosu oluşturuldu")


async def add_device_counter(mac: str):
    """Cihaz için upload/download bridge counter kuralı ekle.

    Her MAC için 2 kural:
    - ether saddr MAC counter comment "bw_{mac}_up"   (upload)
    - ether daddr MAC counter comment "bw_{mac}_down"  (download)
    """
    mac_lower = mac.lower()
    comment_up = f"bw_{mac_lower}_up"
    comment_down = f"bw_{mac_lower}_down"

    # Zaten var mi kontrol et
    out = await run_nft(["-a", "list", "chain", "bridge", "accounting", BRIDGE_CHAIN], check=False)
    if comment_up in out:
        logger.debug(f"Counter zaten mevcut: {mac_lower}")
        return

    # Upload counter
    await run_nft([
        "add", "rule", "bridge", "accounting", BRIDGE_CHAIN,
        "ether", "saddr", mac_lower, "counter",
        "comment", f'"{comment_up}"',
    ], check=False)

    # Download counter
    await run_nft([
        "add", "rule", "bridge", "accounting", BRIDGE_CHAIN,
        "ether", "daddr", mac_lower, "counter",
        "comment", f'"{comment_down}"',
    ], check=False)

    logger.debug(f"Bridge counter eklendi: {mac_lower}")


async def remove_device_counter(mac: str):
    """Cihaz için bridge counter kurallarini sil."""
    mac_lower = mac.lower()
    patterns = [f"bw_{mac_lower}_up", f"bw_{mac_lower}_down"]

    out = await run_nft(["-a", "list", "chain", "bridge", "accounting", BRIDGE_CHAIN], check=False)
    for line in out.splitlines():
        for pattern in patterns:
            if pattern in line:
                match = re.search(r"# handle (\d+)", line)
                if match:
                    handle = match.group(1)
                    await run_nft([
                        "delete", "rule", "bridge", "accounting", BRIDGE_CHAIN,
                        "handle", handle,
                    ], check=False)

    logger.debug(f"Bridge counter silindi: {mac_lower}")


async def read_device_counters() -> Dict[str, Dict[str, int]]:
    """Tum per-device counter degerlerini oku.

    Returns:
        {
            "aa:bb:cc:dd:ee:ff": {
                "upload_bytes": 12345, "upload_packets": 100,
                "download_bytes": 67890, "download_packets": 200,
            },
            ...
        }
    """
    result: Dict[str, Dict[str, int]] = {}

    out = await run_nft(["-a", "list", "chain", "bridge", "accounting", BRIDGE_CHAIN], check=False)
    if not out:
        return result

    # Her satiri parse et: "... counter packets X bytes Y ... comment "bw_MAC_dir""
    for line in out.splitlines():
        line = line.strip()
        if "counter" not in line or "comment" not in line:
            continue

        # Comment'ten MAC ve yon cikar
        comment_match = re.search(r'comment\s+"bw_([0-9a-f:]+)_(up|down)"', line)
        if not comment_match:
            continue

        mac = comment_match.group(1)
        direction = comment_match.group(2)

        # Counter degerlerini cikar
        counter_match = re.search(r'counter\s+packets\s+(\d+)\s+bytes\s+(\d+)', line)
        if not counter_match:
            continue

        packets = int(counter_match.group(1))
        bytes_val = int(counter_match.group(2))

        if mac not in result:
            result[mac] = {
                "upload_bytes": 0, "upload_packets": 0,
                "download_bytes": 0, "download_packets": 0,
            }

        if direction == "up":
            result[mac]["upload_bytes"] = bytes_val
            result[mac]["upload_packets"] = packets
        else:
            result[mac]["download_bytes"] = bytes_val
            result[mac]["download_packets"] = packets

    return result


async def sync_device_counters(macs: List[str]):
    """Bilinen cihaz MAC listesi ile bridge counter kurallarini senkronize et.

    Yeni MAC'ler için counter ekle, kaldirilmis olanlari sil.
    """
    await ensure_bridge_accounting_chain()

    # Mevcut counter MAC'lerini oku
    out = await run_nft(["-a", "list", "chain", "bridge", "accounting", BRIDGE_CHAIN], check=False)
    existing_macs = set()
    for match in re.finditer(r'comment\s+"bw_([0-9a-f:]+)_up"', out):
        existing_macs.add(match.group(1))

    target_macs = {m.lower() for m in macs}

    # Yeni MAC'ler için counter ekle
    for mac in target_macs - existing_macs:
        await add_device_counter(mac)

    # Kaldirilmis MAC'lerin counterlarini sil
    for mac in existing_macs - target_macs:
        await remove_device_counter(mac)

    if target_macs != existing_macs:
        added = len(target_macs - existing_macs)
        removed = len(existing_macs - target_macs)
        logger.info(f"Bridge counter sync: +{added} eklendi, -{removed} silindi, toplam {len(target_macs)}")


# ============================================================================
# Conntrack (Aktif Bağlantı) Fonksiyonlari
# ============================================================================

async def get_active_connections() -> List[Dict[str, Any]]:
    """conntrack'ten aktif bağlantılari parse et."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "/usr/sbin/conntrack", "-L", "-o", "extended",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error(f"conntrack okuma hatasi: {e}")
        return []

    connections = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        # Protokol
        proto_match = re.match(r'ipv[46]\s+\d+\s+(\w+)\s+\d+\s+(\d+)\s*(\w*)', line)
        if not proto_match:
            continue

        proto = proto_match.group(1).upper()
        ttl = proto_match.group(2)
        state = proto_match.group(3) or ""

        # Alan cikarma
        fields = dict(re.findall(r'(src|dst|sport|dport|packets|bytes)=(\S+)', line))

        # Ilk set original yondur
        all_matches = re.findall(r'(src|dst|sport|dport|packets|bytes)=(\S+)', line)
        if len(all_matches) < 4:
            continue

        # Orijinal yon: ilk src, dst, sport, dport
        orig = {}
        reply = {}
        seen = set()
        current = orig
        for key, val in all_matches:
            if key in seen:
                current = reply
                seen = set()
            current[key] = val
            seen.add(key)

        conn = {
            "protocol": proto,
            "src_ip": orig.get("src", ""),
            "src_port": int(orig.get("sport", 0)),
            "dst_ip": orig.get("dst", ""),
            "dst_port": int(orig.get("dport", 0)),
            "bytes_sent": int(orig.get("bytes", 0)),
            "bytes_received": int(reply.get("bytes", 0)),
            "packets_sent": int(orig.get("packets", 0)),
            "packets_received": int(reply.get("packets", 0)),
            "state": state,
            "ttl": int(ttl),
        }
        connections.append(conn)

    return connections


async def get_connection_count() -> Dict[str, int]:
    """Aktif ve maksimum bağlantı sayısıni dondur."""
    result = {"active": 0, "max": 65536}

    try:
        # Aktif bağlantı sayısı
        proc = await asyncio.create_subprocess_exec(
            "cat", "/proc/sys/net/netfilter/nf_conntrack_count",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        count_str = stdout.decode().strip()
        if count_str.isdigit():
            result["active"] = int(count_str)

        # Maksimum bağlantı sayısı
        proc = await asyncio.create_subprocess_exec(
            "cat", "/proc/sys/net/netfilter/nf_conntrack_max",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        max_str = stdout.decode().strip()
        if max_str.isdigit():
            result["max"] = int(max_str)

    except Exception as e:
        logger.error(f"Bağlantı sayısı okuma hatasi: {e}")

    return result


async def get_rule_hit_counts() -> Dict[int, Dict[str, int]]:
    """Firewall kurallarinin hit count degerlerini dondur.

    Returns:
        {rule_id: {"packets": X, "bytes": Y}, ...}
    """
    result: Dict[int, Dict[str, int]] = {}

    ruleset = await run_nft(["-a", "list", "table", "inet", "tonbilai"], check=False)
    if not ruleset:
        return result

    for line in ruleset.splitlines():
        # fw_rule_ID comment'li satirlarda counter degerlerini ara
        rule_match = re.search(r'comment\s+"fw_rule_(\d+)"', line)
        if not rule_match:
            continue

        rule_id = int(rule_match.group(1))
        counter_match = re.search(r'counter\s+packets\s+(\d+)\s+bytes\s+(\d+)', line)
        if counter_match:
            result[rule_id] = {
                "packets": int(counter_match.group(1)),
                "bytes": int(counter_match.group(2)),
            }

    return result


# === IP/Subnet Engelleme Senkronizasyonu ===

async def add_blocked_subnet(subnet: str, timeout_seconds: int = 3600):
    """Subnet'i nftables forward+input zincirine kural olarak ekle.
    Set'e CIDR eklenemez, bu yuzden ayri kural olarak eklenir.
    insert kullanilir (ct state established'dan ONCE gelmeli).
    """
    comment = f"blocked_subnet_{subnet.replace('/', '_')}"
    # Forward zinciri
    await run_nft(
        ["insert", "rule", "inet", "tonbilai", "forward",
         "ip", "saddr", subnet, "counter", "drop", "comment", f'"{comment}_fwd"'],
        check=False,
    )
    await run_nft(
        ["insert", "rule", "inet", "tonbilai", "forward",
         "ip", "daddr", subnet, "counter", "drop", "comment", f'"{comment}_dst"'],
        check=False,
    )
    # Input zinciri
    await run_nft(
        ["insert", "rule", "inet", "tonbilai", "input",
         "ip", "saddr", subnet, "counter", "drop", "comment", f'"{comment}_in"'],
        check=False,
    )
    logger.info(f"Subnet engellendi (nftables rule): {subnet} ({timeout_seconds}s)")


async def remove_blocked_subnet(subnet: str):
    """Subnet engel kurallarini nftables'tan sil (comment ile bul)."""
    comment_prefix = f"blocked_subnet_{subnet.replace('/', '_')}"
    try:
        for chain in ("forward", "input"):
            ruleset = await run_nft(
                ["list", "chain", "inet", "tonbilai", chain, "-a"],
                check=False,
            )
            for line in ruleset.splitlines():
                if comment_prefix in line and "handle" in line:
                    handle_match = re.search(r'handle (\d+)', line)
                    if handle_match:
                        handle = handle_match.group(1)
                        await run_nft(
                            ["delete", "rule", "inet", "tonbilai", chain,
                             "handle", handle],
                            check=False,
                        )
        logger.info(f"Subnet engeli kaldırıldı (nftables rule): {subnet}")
    except Exception as e:
        logger.error(f"Subnet engel kaldirma hatasi: {e}")


async def sync_blocked_ips(ip_timeout_pairs: list):
    """Redis'teki engelli IP'leri nftables blocked_ips setine toplu senkronize et.
    ip_timeout_pairs: [(ip, timeout_seconds), ...]
    Mevcut seti flush eder ve yeniden doldurur.
    """
    if not ip_timeout_pairs:
        logger.info("nftables IP sync: engelli IP yok, set temizleniyor")
        await run_nft(
            ["flush", "set", "inet", "tonbilai", BLOCKED_IPS_SET],
            check=False,
        )
        return

    # Once seti temizle
    await run_nft(
        ["flush", "set", "inet", "tonbilai", BLOCKED_IPS_SET],
        check=False,
    )

    # Her IP'yi timeout ile ekle
    added = 0
    for ip, timeout_sec in ip_timeout_pairs:
        # CIDR notasyonu varsa atla (set ipv4_addr desteklemez)
        if "/" in ip:
            continue
        timeout_sec = max(int(timeout_sec), 60)  # minimum 60 saniye
        await run_nft(
            ["add", "element", "inet", "tonbilai", BLOCKED_IPS_SET,
             "{", ip, "timeout", f"{timeout_sec}s", "}"],
            check=False,
        )
        added += 1

    logger.info(f"nftables IP sync tamamlandi: {added} IP eklendi")


# ============================================================================
# Bridge LAN Masquerade — Modem/Router Uyumlulugu
# Bazi modem/router'lar (ZTE ZXHN H267A vb.) kendi DHCP'sinden IP
# almamis cihazlarin internet trafigini iletmez. Bu modül:
# 1. Bridge postrouting'de kaynak MAC'i br0 MAC'e degistirir (WAN portunda)
# 2. inet nat postrouting'de LAN trafigi icin MASQUERADE ekler
# Boylece tum LAN cihazlarinin trafigi Pi'den geliyormus gibi gorunur.
# ============================================================================


async def _get_br0_mac() -> Optional[str]:
    """br0 bridge interface'inin MAC adresini oku."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "cat", "/sys/class/net/br0/address",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        mac = stdout.decode().strip()
        if re.match(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$', mac):
            return mac
    except Exception as e:
        logger.warning(f"br0 MAC adresi okunamadi: {e}")
    return None


async def _get_wan_bridge_port() -> str:
    """br0 bridge'inin WAN (gateway) tarafindaki port adini tespit et.

    Default gateway'in ARP karsiligindaki bridge portunu bulmaya calisir.
    Bulamazsa 'eth0' doner (en yaygin yapilandirma).
    """
    try:
        # Bridge portlarini listele
        proc = await asyncio.create_subprocess_exec(
            "ls", "/sys/class/net/br0/brif/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        ports = stdout.decode().strip().split()

        if len(ports) <= 1:
            return ports[0] if ports else "eth0"

        # Default gateway IP'sini bul
        proc2 = await asyncio.create_subprocess_exec(
            "ip", "route", "show", "default",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout2, _ = await proc2.communicate()
        gw_match = re.search(r'via\s+([\d.]+)', stdout2.decode())
        if not gw_match:
            return "eth0"

        gw_ip = gw_match.group(1)

        # Gateway'in MAC adresini ARP tablosundan bul
        proc3 = await asyncio.create_subprocess_exec(
            "ip", "neigh", "show", gw_ip, "dev", "br0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout3, _ = await proc3.communicate()
        mac_match = re.search(r'lladdr\s+([0-9a-f:]+)', stdout3.decode())
        if not mac_match:
            return "eth0"

        gw_mac = mac_match.group(1)

        # Bu MAC hangi bridge portunda ogrenilmis?
        proc4 = await asyncio.create_subprocess_exec(
            "bridge", "fdb", "show", "br", "br0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout4, _ = await proc4.communicate()
        for line in stdout4.decode().splitlines():
            if gw_mac in line:
                for port in ports:
                    if port in line:
                        logger.info(f"WAN bridge portu tespit edildi: {port} (gateway {gw_ip})")
                        return port

    except Exception as e:
        logger.warning(f"WAN bridge port tespiti basarisiz: {e}")

    return "eth0"


async def ensure_bridge_masquerade():
    """Bridge seviyesinde MAC yeniden yazimi ve IP MASQUERADE kurallari.

    ZTE gibi bazi modem/router'lar, kendi DHCP'sinden IP almamis yeni
    cihazlarin internet trafigini iletmez. Bu fonksiyon:
    1. br_netfilter modülünü yukler ve bridge-nf-call-iptables'i aktif eder
    2. Bridge postrouting'de kaynak MAC'i br0 MAC'e degistirir (WAN portunda)
    3. inet nat postrouting'de LAN trafigi icin MASQUERADE ekler

    Boylece tum LAN cihazlarinin internet trafigi Pi'den geliyormus gibi
    gorunur ve modem/router trafigi sorunsuz iletir.
    """
    br0_mac = await _get_br0_mac()
    if not br0_mac:
        logger.error("br0 MAC adresi alinamadi, bridge masquerade kurulamadi")
        return

    wan_iface = await _get_wan_bridge_port()
    lan_subnet = await _detect_lan_subnet()

    # 1. br_netfilter yuklu oldugundan emin ol
    await _run_system_cmd(["sudo", "modprobe", "br_netfilter"], check=False)
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"], check=False
    )

    ruleset = await run_nft(["list", "ruleset"], check=False)

    # 2. Bridge MAC rewrite tablosu
    if BRIDGE_MASQ_TABLE not in ruleset:
        logger.info(
            f"Bridge masquerade tablosu olusturuluyor "
            f"(WAN={wan_iface}, br0_mac={br0_mac}, subnet={lan_subnet})..."
        )
        nft_commands = f"""
table {BRIDGE_MASQ_TABLE} {{
    chain {BRIDGE_MASQ_CHAIN} {{
        type filter hook postrouting priority 300; policy accept;
        oifname "{wan_iface}" ether saddr != {br0_mac} ether saddr set {br0_mac} comment "bridge_mac_rewrite"
    }}
}}
"""
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=nft_commands.encode())
        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.error(f"Bridge masquerade tablosu olusturulamadi: {err}")
        else:
            logger.info("Bridge MAC rewrite tablosu olusturuldu")
    else:
        logger.info("Bridge masquerade tablosu zaten mevcut")

    # 3. inet nat postrouting MASQUERADE
    if "bridge_lan_masq" not in ruleset:
        await ensure_nat_postrouting_chain()
        masq_rule = (
            f'add rule inet nat postrouting '
            f'ip saddr {lan_subnet} ip daddr != {lan_subnet} '
            f'masquerade comment "bridge_lan_masq"'
        )
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=masq_rule.encode())
        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.error(f"LAN MASQUERADE kurali eklenemedi: {err}")
        else:
            logger.info(f"LAN MASQUERADE kurali eklendi ({lan_subnet})")
    else:
        logger.info("LAN MASQUERADE kurali zaten mevcut")

    # 4. Kurallari persist et
    await persist_nftables()


async def remove_bridge_masquerade():
    """Bridge masquerade kurallarini kaldir.

    Modem/router degisikligi veya sorun giderme icin kullanilabilir.
    """
    # 1. Bridge MAC rewrite tablosunu sil
    await run_nft(["delete", "table", BRIDGE_MASQ_TABLE], check=False)
    logger.info("Bridge masquerade tablosu silindi")

    # 2. MASQUERADE kuralini sil (comment bazli)
    out = await run_nft(["-a", "list", "chain", "inet", "nat", "postrouting"], check=False)
    if out:
        for line in out.splitlines():
            if "bridge_lan_masq" in line and "handle" in line:
                handle_match = re.search(r"handle\s+(\d+)", line)
                if handle_match:
                    handle = handle_match.group(1)
                    await run_nft(
                        ["delete", "rule", "inet", "nat", "postrouting", "handle", handle],
                        check=False,
                    )
                    logger.info("LAN MASQUERADE kurali silindi")

    await persist_nftables()
    logger.info("Bridge masquerade kurallari tamamen kaldirildi")


# ============================================================================
# VPN Client Bridge Trafik Yonlendirme
# Bridge-forwarded internet trafiğini Pi'nin IP stack'ine yonlendirir
# boylece trafik VPN tunelinden cikar.
# ============================================================================

VPN_BRIDGE_TABLE = "vpn_redirect"


async def _run_system_cmd(cmd: list, check: bool = True) -> str:
    """Genel sistem komutu calistir (nft disindaki komutlar için)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode().strip()
    err = stderr.decode().strip()
    if proc.returncode != 0 and check:
        logger.error(f"Komut hatasi: {' '.join(cmd)} -> {err}")
        raise RuntimeError(err)
    return out


async def _detect_lan_subnet() -> str:
    """br0 interface'inden LAN subnet'ini tespit et (orn: 192.168.1.0/24)."""
    try:
        out = await _run_system_cmd(
            ["ip", "-4", "-o", "addr", "show", "br0"], check=False
        )
        # "2: br0  inet 192.168.1.2/24 brd ..." parse
        m = re.search(r"inet\s+([\d.]+)/(\d+)", out)
        if m:
            ip_str = m.group(1)
            prefix = int(m.group(2))
            # Subnet hesapla (basit: son okteti 0 yap)
            parts = ip_str.split(".")
            if prefix == 24:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            elif prefix == 16:
                return f"{parts[0]}.{parts[1]}.0.0/16"
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"  # default /24
    except Exception as e:
        logger.warning(f"LAN subnet tespiti başarısız: {e}")
    return "192.168.1.0/24"  # fallback


async def setup_vpn_client_routing(
    vpn_interface: str = "wg-client",
    endpoint_ip: str | None = None,
):
    """VPN client için bridge trafik yonlendirmesini kur.

    Bridge-forwarded internet trafiğini Pi'nin IP stack'ine yonlendirir
    (meta pkttype set host). Pi'nin routing tablosu (wg-quick tarafindan
    ayarlanan 0.0.0.0/1 + 128.0.0.0/1 rotalar) trafiği VPN tunelinden cikarir.

    Kill switch: VPN interface down olursa internet trafiği engellenir.
    DNS redirect: Tum DNS sorgulari Pi üzerinden gecmesi saglanir.
    IPv6 engelleme: IPv6 trafik sizmasi onlenir.
    """
    vpn_interface = _validate_interface_name(vpn_interface)
    lan_subnet = await _detect_lan_subnet()

    # 1. br_netfilter yuklu oldugundan emin ol
    await _run_system_cmd(["sudo", "modprobe", "br_netfilter"], check=False)
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"], check=False
    )
    # IPv6 bridge-nf de aktif et
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-ip6tables=1"], check=False
    )

    # 2. Eski vpn_redirect tablosunu temizle (varsa)
    await run_nft(["delete", "table", "bridge", VPN_BRIDGE_TABLE], check=False)

    # VPN endpoint IP'sine direkt erişim için (tunel kurulmasi için gerekli)
    endpoint_rule = ""
    if endpoint_ip:
        endpoint_rule = f"ip daddr {endpoint_ip} return"

    # 3. Bridge vpn_redirect tablosu oluştur
    nft_commands = f"""
table bridge {VPN_BRIDGE_TABLE} {{
    chain prerouting {{
        type filter hook prerouting priority dstnat - 1; policy accept;

        # LAN trafiği bridge'den gecmeye devam etsin
        ip daddr {lan_subnet} return
        # VPN endpoint'e direkt erişim (tunel için)
        {endpoint_rule}
        # Özel ag aralıklari bridge'de kalsin
        ip daddr 10.0.0.0/8 return
        ip daddr 172.16.0.0/12 return
        # Broadcast/multicast bridge'de kalsin
        meta pkttype {{ broadcast, multicast }} return
        # Non-IPv4 frameler (ARP) bridge'de kalsin
        ether type != ip return

        # Internet-bound trafiği Pi'nin IP stack'ine yonlendir
        counter meta pkttype set host comment "vpn_bridge_redirect"
    }}
}}
"""
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=nft_commands.encode())
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.warning(f"nftables bridge tablosu oluşturulamadi: {err}")
        await _setup_vpn_ebtables_fallback(lan_subnet)
    else:
        logger.info(f"Bridge vpn_redirect tablosu oluşturuldu (LAN={lan_subnet})")

    # 4. VPN forward + masquerade kurallari
    await add_vpn_nft_rules(vpn_interface, "0.0.0.0/0", is_client=True)

    # 5. Kill switch: VPN interface down olursa internet trafiğini engelle
    # iifname "br0" ile sadece IP-forwarded trafige uygulanir (bridge-forwarded degil)
    # br_netfilter aktifken bridge-forwarded paketler de inet forward'a duser,
    # iifname "br0" filtresi bu paketleri atlar (bridge paketleri ethX olarak gorulur)
    endpoint_exclude = ""
    if endpoint_ip:
        endpoint_exclude = f" ip daddr != {endpoint_ip}"
    kill_switch_rules = f"""
add rule inet tonbilai forward iifname "br0" oifname != "{vpn_interface}" ip daddr != {lan_subnet} ip daddr != 10.0.0.0/8 ip daddr != 172.16.0.0/12{endpoint_exclude} counter drop comment "vpn_{vpn_interface}_killswitch"
"""
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=kill_switch_rules.strip().encode())
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.warning(f"Kill switch kurallari eklenemedi: {err}")
    else:
        logger.info("VPN kill switch kurallari eklendi")

    # 6. DNS redirect: Tum DNS sorgularini Pi'ye yonlendir (DNS leak onleme)
    dns_rules = f"""
add rule inet nat prerouting iifname "br0" udp dport 53 counter redirect to :53 comment "vpn_{vpn_interface}_dns_redir"
add rule inet nat prerouting iifname "br0" tcp dport 53 counter redirect to :53 comment "vpn_{vpn_interface}_dns_redir"
"""
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=dns_rules.strip().encode())
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.warning(f"DNS redirect kurallari eklenemedi: {err}")
    else:
        logger.info("VPN DNS redirect kurallari eklendi (DNS leak onleme)")

    # 7. IPv6 internet trafiğini engelle (IPv6 leak onleme)
    ipv6_rules = f"""
add rule inet tonbilai forward ip6 daddr != ::1 ip6 daddr != fe80::/10 ip6 daddr != fd00::/8 counter drop comment "vpn_{vpn_interface}_ipv6_block"
"""
    proc = await asyncio.create_subprocess_exec(
        "sudo", NFT_BIN, "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=ipv6_rules.strip().encode())
    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.warning(f"IPv6 engelleme kuralı eklenemedi: {err}")
    else:
        logger.info("IPv6 internet trafiği engellendi (leak onleme)")

    # 8. nftables persist
    await persist_nftables()

    logger.info(f"VPN client bridge routing kuruldu: {vpn_interface} (kill switch + DNS redirect + IPv6 block)")


async def teardown_vpn_client_routing(vpn_interface: str = "wg-client"):
    """VPN client bridge routing'ini temizle (kill switch + DNS redirect + IPv6 dahil)."""
    vpn_interface = _validate_interface_name(vpn_interface)

    # 1. Bridge vpn_redirect tablosunu sil
    await run_nft(["delete", "table", "bridge", VPN_BRIDGE_TABLE], check=False)
    logger.info("Bridge vpn_redirect tablosu silindi")

    # 2. Ebtables fallback temizle
    await _run_system_cmd(["sudo", "ebtables", "-t", "broute", "-F"], check=False)

    # 3. VPN nftables kurallarini temizle (forward + masquerade)
    await remove_vpn_nft_rules(vpn_interface)

    # 4. Kill switch + DNS redirect + IPv6 kurallarini temizle (comment bazli)
    comment_prefix = f"vpn_{vpn_interface}_"
    extra_chains = [
        ("inet", "tonbilai", "forward"),
        ("inet", "nat", "prerouting"),
    ]
    for family, table, chain in extra_chains:
        out = await run_nft(["-a", "list", "chain", family, table, chain], check=False)
        if not out:
            continue
        for line in out.splitlines():
            if comment_prefix in line and "handle" in line:
                handle_match = re.search(r"handle\s+(\d+)", line)
                if handle_match:
                    handle = handle_match.group(1)
                    await run_nft(
                        ["delete", "rule", family, table, chain, "handle", handle],
                        check=False,
                    )

    # 5. nftables persist
    await persist_nftables()

    logger.info(f"VPN client bridge routing temizlendi: {vpn_interface}")


async def _setup_vpn_ebtables_fallback(lan_subnet: str = "192.168.1.0/24"):
    """nftables bridge meta pkttype desteklenmiyorsa ebtables ile fallback."""
    try:
        # Subnet'ten IP kismi cikar (ebtables için)
        subnet_ip = lan_subnet.split("/")[0]
        subnet_mask = lan_subnet.split("/")[1] if "/" in lan_subnet else "24"
        # Onceki kurallari temizle
        await _run_system_cmd(["sudo", "ebtables", "-t", "broute", "-F"], check=False)
        # Internet-bound trafiği Pi'nin IP stack'ine yonlendir
        await _run_system_cmd([
            "sudo", "ebtables", "-t", "broute", "-A", "BROUTING",
            "-p", "IPv4", "--ip-dst", "!", f"{subnet_ip}/{subnet_mask}",
            "-j", "redirect", "--redirect-target", "DROP",
        ])
        logger.info(f"VPN routing: ebtables broute fallback kuruldu (LAN={lan_subnet})")
    except Exception as e:
        logger.error(f"ebtables fallback hatasi: {e}")

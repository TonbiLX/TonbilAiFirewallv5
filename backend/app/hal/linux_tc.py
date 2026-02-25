# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Linux Traffic Control (tc) yardimci modulu: HTB ile bant genisligi sinirlandirma.
# Bridge modunda çalışır: tc slave interface'lerde (eth0+eth1), nftables bridge tablosunda mark.
#
# ONEMLI: br0 (bridge) üzerindeki tc, bridge-forwarded trafige etki ETMEZ.
# Bu yuzden tc, bridge'in slave interface'lerine (eth0, eth1) uygulanir.
# nftables mark kurallari da 'bridge' tablosunda olmalıdır (inet degil).

import asyncio
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger("tonbilai.tc")

TC_BIN = "/usr/sbin/tc"
NFT_BIN = "/usr/sbin/nft"

ROOT_HANDLE = "1:"
DEFAULT_CLASSID = "9999"

# nftables bridge tablosu ve tc mark zinciri
BRIDGE_TABLE = "accounting"
TC_MARK_CHAIN = "tc_mark"

# Cache: slave interface listesi (bir kez tespit, sonra cache)
_slave_interfaces_cache: Optional[List[str]] = None


async def _detect_bridge_slaves() -> List[str]:
    """br0 bridge'in slave interface'lerini otomatik tespit et."""
    global _slave_interfaces_cache
    if _slave_interfaces_cache is not None:
        return _slave_interfaces_cache

    try:
        proc = await asyncio.create_subprocess_exec(
            "ls", "/sys/class/net/br0/brif/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            slaves = stdout.decode().strip().split()
            if slaves:
                _slave_interfaces_cache = slaves
                logger.info(f"Bridge slave interface'ler tespit edildi: {slaves}")
                return slaves
    except Exception:
        pass

    # Fallback
    _slave_interfaces_cache = ["eth0", "eth1"]
    logger.warning(f"Bridge slave tespiti başarısız, fallback: {_slave_interfaces_cache}")
    return _slave_interfaces_cache


async def run_tc(args: list, check: bool = True) -> str:
    """tc komutunu sudo ile calistir."""
    cmd = ["sudo", TC_BIN] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode().strip()
    err = stderr.decode().strip()

    if proc.returncode != 0 and check:
        logger.error(f"tc komutu başarısız: {' '.join(cmd)} -> {err}")
        raise RuntimeError(f"tc error: {err}")

    if proc.returncode != 0:
        logger.debug(f"tc komutu uyari: {' '.join(cmd)} -> {err}")

    return out


async def run_nft(args: list, check: bool = False) -> str:
    """nft komutunu sudo ile calistir."""
    cmd = ["sudo", NFT_BIN] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip()


def mac_to_classid(mac: str) -> int:
    """MAC adresinden benzersiz class ID uret (1-9998 arasi)."""
    parts = mac.replace(":", "").replace("-", "").lower()
    num = int(parts[-4:], 16)
    return (num % 9998) + 1


def mac_to_mark(mac: str) -> int:
    """MAC adresinden nftables mark degeri uret."""
    return mac_to_classid(mac) + 100  # 101-10098 arasi mark


async def _ensure_tc_mark_chain():
    """Bridge tablosunda tc_mark zincirini oluştur (yoksa).

    Bu zincir 'bridge accounting' tablosuna eklenir.
    per_device zinciri (priority -2) counter için, tc_mark (priority -1) shaping için.
    """
    out = await run_nft(
        ["-a", "list", "chain", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN],
        check=False,
    )
    if TC_MARK_CHAIN in out and "type filter" in out:
        logger.debug("Bridge tc_mark zinciri zaten mevcut")
        return

    # Tablo + zinciri oluştur (nft -f additive: tablo varsa sadece zincir eklenir)
    nft_commands = f"""
table bridge {BRIDGE_TABLE} {{
    chain {TC_MARK_CHAIN} {{
        type filter hook forward priority -1; policy accept;
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
        logger.error(f"tc_mark chain oluşturma hatasi: {err}")
        raise RuntimeError(f"tc_mark chain create error: {err}")

    logger.info("Bridge tc_mark zinciri oluşturuldu (priority -1)")


async def _cleanup_old_br0_rules():
    """Eski br0 tc kurallarini temizle (artik slave interface'ler kullanılıyor)."""
    out = await run_tc(["qdisc", "show", "dev", "br0"], check=False)
    if "htb" in out:
        await run_tc(["qdisc", "del", "dev", "br0", "root"], check=False)
        logger.info("Eski br0 HTB qdisc temizlendi")


async def setup_htb_root():
    """Tum slave interface'lerde HTB root qdisc oluştur (yoksa)."""
    # Once eski br0 kurallarini temizle
    await _cleanup_old_br0_rules()

    slaves = await _detect_bridge_slaves()
    for iface in slaves:
        out = await run_tc(["qdisc", "show", "dev", iface], check=False)
        if "htb" in out and "1:" in out:
            logger.debug(f"HTB root qdisc zaten mevcut: {iface}")
            continue

        # Mevcut qdiscleri temizle
        await run_tc(["qdisc", "del", "dev", iface, "root"], check=False)

        # HTB root qdisc oluştur
        await run_tc([
            "qdisc", "add", "dev", iface, "root",
            "handle", ROOT_HANDLE, "htb", "default", DEFAULT_CLASSID,
        ])

        # Varsayilan sinif (sinirsiz - 1Gbps)
        await run_tc([
            "class", "add", "dev", iface,
            "parent", ROOT_HANDLE,
            "classid", f"{ROOT_HANDLE}{DEFAULT_CLASSID}",
            "htb", "rate", "1000mbit", "ceil", "1000mbit",
        ])

        logger.info(f"HTB root qdisc oluşturuldu: {iface}")


async def add_device_limit(mac: str, rate_mbps: int, ceil_mbps: int = 0):
    """Cihaz için bant genisligi siniri ekle/güncelle.

    Bridge modunda çalışır:
    1. tc HTB sinifi eth0 VE eth1 üzerinde oluşturulur
    2. nftables bridge tablosunda mark kuralı eklenir (upload + download)
    3. tc fw filtresi mark'a göre sinifa yonlendirir

    Upload:  cihaz -> eth0(in) -> bridge forward -> eth1(out) - tc eth1 sinirlama
    Download: internet -> eth1(in) -> bridge forward -> eth0(out) - tc eth0 sinirlama

    Args:
        mac: Cihaz MAC adresi
        rate_mbps: Garantili hiz (Mbps)
        ceil_mbps: Maksimum hiz (Mbps), 0 ise rate ile ayni
    """
    if ceil_mbps <= 0:
        ceil_mbps = rate_mbps

    classid = mac_to_classid(mac)
    mark = mac_to_mark(mac)
    classid_str = f"{ROOT_HANDLE}{classid}"

    # 1. Root qdisc kontrol (tum slave interface'ler)
    await setup_htb_root()

    # 2. Her slave interface için tc sinif + filtre oluştur
    slaves = await _detect_bridge_slaves()
    for iface in slaves:
        # Mevcut sinifi kaldir
        await run_tc([
            "class", "del", "dev", iface,
            "parent", ROOT_HANDLE,
            "classid", classid_str,
        ], check=False)

        # Yeni sinif oluştur
        try:
            await run_tc([
                "class", "add", "dev", iface,
                "parent", ROOT_HANDLE,
                "classid", classid_str,
                "htb", "rate", f"{rate_mbps}mbit", "ceil", f"{ceil_mbps}mbit",
            ])
        except RuntimeError:
            # Sinif zaten varsa change ile güncelle
            await run_tc([
                "class", "change", "dev", iface,
                "parent", ROOT_HANDLE,
                "classid", classid_str,
                "htb", "rate", f"{rate_mbps}mbit", "ceil", f"{ceil_mbps}mbit",
            ])

        # Mevcut fw filtresi temizle
        await run_tc([
            "filter", "del", "dev", iface,
            "parent", ROOT_HANDLE,
            "prio", "1",
            "handle", str(mark), "fw",
        ], check=False)

        # fw filter: mark -> class esleme
        await run_tc([
            "filter", "add", "dev", iface,
            "parent", ROOT_HANDLE,
            "prio", "1",
            "handle", str(mark), "fw",
            "flowid", classid_str,
        ])

    # 3. Bridge nftables tablosunda mark kurallari
    await _ensure_tc_mark_chain()

    # Eski mark kurallarini temizle (bridge + inet)
    await _remove_nft_mark_rule(mac)

    mac_lower = mac.lower()

    # Upload: cihazdan gelen trafik (ether saddr)
    await run_nft([
        "add", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN,
        "ether", "saddr", mac_lower,
        "meta", "mark", "set", str(mark),
        "comment", f'"tc_mark_{mac_lower}_up"',
    ])

    # Download: cihaza giden trafik (ether daddr)
    await run_nft([
        "add", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN,
        "ether", "daddr", mac_lower,
        "meta", "mark", "set", str(mark),
        "comment", f'"tc_mark_{mac_lower}_down"',
    ])

    logger.info(
        f"Bant genişliği siniri: {mac} -> {rate_mbps}Mbps (ceil {ceil_mbps}Mbps) "
        f"[bridge mark + tc {', '.join(slaves)}]"
    )


async def remove_device_limit(mac: str):
    """Cihaz bant genisligi sinirini kaldir."""
    classid = mac_to_classid(mac)
    mark = mac_to_mark(mac)
    classid_str = f"{ROOT_HANDLE}{classid}"

    # Her slave interface'den tc sinif ve filtre temizle
    slaves = await _detect_bridge_slaves()
    for iface in slaves:
        await run_tc([
            "filter", "del", "dev", iface,
            "parent", ROOT_HANDLE,
            "prio", "1",
            "handle", str(mark), "fw",
        ], check=False)

        await run_tc([
            "class", "del", "dev", iface,
            "parent", ROOT_HANDLE,
            "classid", classid_str,
        ], check=False)

    # nftables mark kurallarini temizle (bridge + inet eski)
    await _remove_nft_mark_rule(mac)

    logger.info(f"Bant genişliği siniri kaldırıldı: {mac}")


async def _remove_nft_mark_rule(mac: str):
    """MAC için tum nftables tc mark kurallarini sil (bridge + inet eski)."""
    mac_lower = mac.lower()

    # 1. Bridge tablosundaki mark kurallarini sil (yeni format: _up, _down)
    patterns = [f"tc_mark_{mac_lower}_up", f"tc_mark_{mac_lower}_down"]

    out = await run_nft(
        ["-a", "list", "chain", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN],
        check=False,
    )
    if out:
        for line in out.splitlines():
            for pattern in patterns:
                if pattern in line:
                    match = re.search(r"# handle (\d+)", line)
                    if match:
                        handle = match.group(1)
                        await run_nft([
                            "delete", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN,
                            "handle", handle,
                        ])

    # 2. Eski inet tablosundaki mark kurallarini da temizle (gecis dönemi)
    old_pattern = f"tc_mark_{mac_lower}"
    out = await run_nft(
        ["-a", "list", "chain", "inet", "tonbilai", "forward"],
        check=False,
    )
    if out:
        for line in out.splitlines():
            # Sadece eski format (up/down suffix'i OLMAYAN) kurallar
            if old_pattern in line and f"{old_pattern}_up" not in line and f"{old_pattern}_down" not in line:
                match = re.search(r"# handle (\d+)", line)
                if match:
                    handle = match.group(1)
                    await run_nft([
                        "delete", "rule", "inet", "tonbilai", "forward",
                        "handle", handle,
                    ])


async def get_device_stats(mac: str) -> Optional[Dict]:
    """Cihazin tc sinif istatistiklerini dondur (tum slave interface'lerden toplam)."""
    classid = mac_to_classid(mac)
    classid_str = f"{ROOT_HANDLE}{classid}"

    total_bytes = 0
    total_packets = 0
    rate_str = "0bit"

    slaves = await _detect_bridge_slaves()
    for iface in slaves:
        out = await run_tc(["-s", "class", "show", "dev", iface], check=False)
        for block in out.split("\n\n"):
            if classid_str in block:
                sent_match = re.search(r"Sent (\d+) bytes (\d+) pkt", block)
                rate_match = re.search(r"rate (\d+\w+)", block)
                if sent_match:
                    total_bytes += int(sent_match.group(1))
                    total_packets += int(sent_match.group(2))
                    if rate_match:
                        rate_str = rate_match.group(1)

    if total_bytes > 0 or total_packets > 0:
        return {
            "bytes_sent": total_bytes,
            "packets_sent": total_packets,
            "rate": rate_str,
        }
    return None

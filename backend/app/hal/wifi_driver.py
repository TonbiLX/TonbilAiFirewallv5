# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WiFi AP HAL Surucusu: hostapd konfigurasyonu ve iw komutlari ile WiFi AP yonetimi.
# wlan0 interface'i br0 bridge'e eklenerek ayni subnet uzerinden calisiyor.

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("tonbilai.wifi_driver")

HOSTAPD_CONF = Path("/etc/hostapd/hostapd.conf")
HOSTAPD_GUEST_CONF = Path("/etc/hostapd/hostapd-guest.conf")
HOSTAPD_ACCEPT_FILE = Path("/etc/hostapd/hostapd.accept")
HOSTAPD_DENY_FILE = Path("/etc/hostapd/hostapd.deny")
WIFI_INTERFACE = "wlan0"
BRIDGE_INTERFACE = "br0"


async def _run_cmd(cmd: list, check: bool = True, timeout: float = 15) -> str:
    """Komut calistir (timeout korumali)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.error(f"Komut timeout ({timeout}s): {' '.join(cmd)}")
        raise RuntimeError(f"Komut zaman asimina ugradi: {' '.join(cmd[:3])}")
    out = stdout.decode().strip()
    err = stderr.decode().strip()
    if proc.returncode != 0 and check:
        logger.error(f"Komut hatasi: {' '.join(cmd)} -> {err}")
        raise RuntimeError(err)
    return out


async def _sudo_write_file(path: str, content: str) -> bool:
    """sudo tee ile dosya yaz."""
    proc = await asyncio.create_subprocess_exec(
        "sudo", "tee", path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate(input=content.encode())
    return proc.returncode == 0


# ===== DURUM =====

async def get_wifi_status() -> dict:
    """WiFi AP canli durumunu oku."""
    result = {
        "enabled": False,
        "ssid": None,
        "channel": None,
        "band": None,
        "tx_power": None,
        "clients_count": 0,
        "interface": WIFI_INTERFACE,
    }

    try:
        # hostapd calisiyor mu?
        out = await _run_cmd(["systemctl", "is-active", "hostapd"], check=False)
        is_active = out.strip() == "active"
        result["enabled"] = is_active

        if not is_active:
            # Config dosyasindan SSID oku (pasif durumda bile gosterebilmek icin)
            if HOSTAPD_CONF.exists():
                try:
                    conf = HOSTAPD_CONF.read_text()
                    for line in conf.splitlines():
                        if line.startswith("ssid="):
                            result["ssid"] = line.split("=", 1)[1].strip()
                            break
                except Exception:
                    pass
            return result

        # iw dev wlan0 info
        iw_out = await _run_cmd(["iw", "dev", WIFI_INTERFACE, "info"], check=False)
        for line in iw_out.splitlines():
            line = line.strip()
            if line.startswith("ssid"):
                result["ssid"] = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else None
            elif line.startswith("channel"):
                m = re.search(r"channel\s+(\d+)", line)
                if m:
                    result["channel"] = int(m.group(1))
                    ch = result["channel"]
                    result["band"] = "5GHz" if ch >= 36 else "2.4GHz"
            elif line.startswith("txpower"):
                m = re.search(r"([\d.]+)\s*dBm", line)
                if m:
                    result["tx_power"] = int(float(m.group(1)))

        # Bagli istemci sayisi
        station_out = await _run_cmd(
            ["iw", "dev", WIFI_INTERFACE, "station", "dump"], check=False
        )
        if station_out:
            result["clients_count"] = station_out.count("Station ")

    except Exception as e:
        logger.error(f"WiFi durum okuma hatasi: {e}")

    return result


async def get_wifi_clients() -> list[dict]:
    """Bagli WiFi istemcilerini listele."""
    clients = []
    try:
        out = await _run_cmd(
            ["iw", "dev", WIFI_INTERFACE, "station", "dump"], check=False
        )
        if not out:
            return clients

        # ARP tablosundan IP eslemesi
        arp_map: dict[str, str] = {}
        try:
            arp_out = await _run_cmd(["ip", "neigh", "show", "dev", WIFI_INTERFACE], check=False)
            for line in arp_out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[2] == "lladdr":
                    arp_map[parts[4].lower()] = parts[0]
                elif len(parts) >= 3:
                    # Alternatif format: IP lladdr MAC ...
                    for i, p in enumerate(parts):
                        if p == "lladdr" and i + 1 < len(parts):
                            arp_map[parts[i + 1].lower()] = parts[0]
        except Exception:
            pass

        # Bridge FDB + ARP tablosundan da MAC→IP eslemesi dene
        try:
            arp_all = await _run_cmd(["ip", "neigh", "show"], check=False)
            for line in arp_all.splitlines():
                parts = line.split()
                if "lladdr" in parts:
                    idx = parts.index("lladdr")
                    if idx + 1 < len(parts):
                        mac = parts[idx + 1].lower()
                        ip = parts[0]
                        if mac not in arp_map:
                            arp_map[mac] = ip
        except Exception:
            pass

        # Station dump parse
        current: dict[str, Any] | None = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Station "):
                if current:
                    clients.append(current)
                mac = line.split()[1].lower()
                current = {
                    "mac_address": mac.upper(),
                    "ip_address": arp_map.get(mac),
                    "signal_dbm": 0,
                    "tx_bitrate_mbps": 0.0,
                    "rx_bitrate_mbps": 0.0,
                    "connected_seconds": 0,
                    "hostname": None,
                }
            elif current:
                if "signal:" in line:
                    m = re.search(r"signal:\s*(-?\d+)", line)
                    if m:
                        current["signal_dbm"] = int(m.group(1))
                elif "tx bitrate:" in line:
                    m = re.search(r"tx bitrate:\s*([\d.]+)", line)
                    if m:
                        current["tx_bitrate_mbps"] = float(m.group(1))
                elif "rx bitrate:" in line:
                    m = re.search(r"rx bitrate:\s*([\d.]+)", line)
                    if m:
                        current["rx_bitrate_mbps"] = float(m.group(1))
                elif "connected time:" in line:
                    m = re.search(r"connected time:\s*(\d+)", line)
                    if m:
                        current["connected_seconds"] = int(m.group(1))

        if current:
            clients.append(current)

    except Exception as e:
        logger.error(f"WiFi istemci listesi hatasi: {e}")

    return clients


async def scan_available_channels() -> dict:
    """Kullanilabilir WiFi kanallarini listele."""
    channels: dict[str, list[int]] = {"2.4GHz": [], "5GHz": []}
    try:
        out = await _run_cmd(["iw", "phy", "phy0", "channels"], check=False)
        for line in out.splitlines():
            m = re.search(r"\*\s+(\d+)\s+MHz\s+\[(\d+)\]", line)
            if m:
                freq = int(m.group(1))
                ch = int(m.group(2))
                disabled = "disabled" in line.lower() or "no IR" in line
                if not disabled:
                    if freq < 3000:
                        channels["2.4GHz"].append(ch)
                    else:
                        channels["5GHz"].append(ch)
    except Exception as e:
        logger.error(f"Kanal tarama hatasi: {e}")
        # Varsayilan degerler
        channels["2.4GHz"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        channels["5GHz"] = [36, 40, 44, 48]

    return channels


# ===== KONFIGURASYON =====

def _build_hostapd_config(config: dict) -> str:
    """hostapd.conf icerigi olustur."""
    channel = config.get("channel", 6)
    band = config.get("band", "2.4GHz")

    # hw_mode: a (5GHz), g (2.4GHz)
    if band == "5GHz" or (isinstance(channel, int) and channel >= 36):
        hw_mode = "a"
    else:
        hw_mode = "g"

    lines = [
        f"interface={WIFI_INTERFACE}",
        f"bridge={BRIDGE_INTERFACE}",
        f"driver=nl80211",
        f"ssid={config.get('ssid', 'TonbilAiOS')}",
        f"hw_mode={hw_mode}",
        f"channel={channel}",
        f"country_code=TR",
        f"ieee80211n=1",
        f"wmm_enabled=1",
    ]

    # 802.11ac (5GHz icin)
    if hw_mode == "a":
        lines.append("ieee80211ac=1")

    # Gizli SSID
    if config.get("hidden_ssid", False):
        lines.append("ignore_broadcast_ssid=1")
    else:
        lines.append("ignore_broadcast_ssid=0")

    # TX Power (hostapd bunu desteklemez, iw ile ayarlariz)

    # WPA2 sifreleme
    password = config.get("password")
    if password and len(password) >= 8:
        lines.extend([
            "wpa=2",
            f"wpa_passphrase={password}",
            "wpa_key_mgmt=WPA-PSK",
            "rsn_pairwise=CCMP",
        ])
    else:
        # Acik ag (sifresiz)
        lines.append("# Acik ag - sifre yok")

    # MAC filtre
    mac_filter_mode = config.get("mac_filter_mode", "disabled")
    if mac_filter_mode == "whitelist":
        lines.extend([
            "macaddr_acl=1",
            f"accept_mac_file={HOSTAPD_ACCEPT_FILE}",
        ])
    elif mac_filter_mode == "blacklist":
        lines.extend([
            "macaddr_acl=0",
            f"deny_mac_file={HOSTAPD_DENY_FILE}",
        ])
    else:
        lines.append("macaddr_acl=0")

    # Logger
    lines.extend([
        "logger_syslog=-1",
        "logger_syslog_level=2",
        "logger_stdout=-1",
        "logger_stdout_level=2",
    ])

    return "\n".join(lines) + "\n"


async def write_hostapd_config(config: dict) -> bool:
    """hostapd.conf dosyasina yaz."""
    try:
        content = _build_hostapd_config(config)

        # /etc/hostapd dizininin varligini kontrol et
        await _run_cmd(["sudo", "mkdir", "-p", "/etc/hostapd"], check=False)

        ok = await _sudo_write_file(str(HOSTAPD_CONF), content)
        if ok:
            await _run_cmd(["sudo", "chmod", "600", str(HOSTAPD_CONF)], check=False)
            logger.info(f"hostapd config yazildi: {HOSTAPD_CONF}")

        # TX power ayarla (hostapd desteklemez, iw ile)
        tx_power = config.get("tx_power")
        if tx_power and isinstance(tx_power, int) and 1 <= tx_power <= 31:
            # tx_power dBm * 100 = mBm (iw birimi)
            await _run_cmd(
                ["sudo", "iw", "dev", WIFI_INTERFACE, "set", "txpower", "fixed",
                 str(tx_power * 100)],
                check=False,
            )

        return ok
    except Exception as e:
        logger.error(f"hostapd config yazma hatasi: {e}")
        return False


async def write_guest_config(config: dict) -> bool:
    """Misafir AP icin ikinci hostapd config yaz."""
    try:
        guest_ssid = config.get("guest_ssid", "TonbilAiOS-Misafir")
        guest_password = config.get("guest_password")

        lines = [
            f"interface=wlan0_guest",
            f"bridge={BRIDGE_INTERFACE}",
            f"driver=nl80211",
            f"ssid={guest_ssid}",
            f"hw_mode=g",
            f"channel={config.get('channel', 6)}",
            f"country_code=TR",
            f"ieee80211n=1",
            f"wmm_enabled=1",
            f"ignore_broadcast_ssid=0",
        ]

        if guest_password and len(guest_password) >= 8:
            lines.extend([
                "wpa=2",
                f"wpa_passphrase={guest_password}",
                "wpa_key_mgmt=WPA-PSK",
                "rsn_pairwise=CCMP",
            ])

        lines.extend([
            "logger_syslog=-1",
            "logger_syslog_level=2",
        ])

        content = "\n".join(lines) + "\n"

        ok = await _sudo_write_file(str(HOSTAPD_GUEST_CONF), content)
        if ok:
            await _run_cmd(["sudo", "chmod", "600", str(HOSTAPD_GUEST_CONF)], check=False)
            logger.info(f"Misafir hostapd config yazildi: {HOSTAPD_GUEST_CONF}")
        return ok
    except Exception as e:
        logger.error(f"Misafir hostapd config yazma hatasi: {e}")
        return False


# ===== KONTROL =====

async def start_wifi_ap() -> bool:
    """WiFi AP baslat: wlan0'i br0'a ekle + hostapd baslat."""
    try:
        # 1. wlan0 managed modda ise once down yap
        await _run_cmd(["sudo", "ip", "link", "set", WIFI_INTERFACE, "up"], check=False)

        # 2. wlan0'i br0'a ekle (zaten ekliyse hata verir, sorun degil)
        await _run_cmd(
            ["sudo", "ip", "link", "set", WIFI_INTERFACE, "master", BRIDGE_INTERFACE],
            check=False,
        )

        # 3. hostapd baslat
        await _run_cmd(["sudo", "systemctl", "start", "hostapd"])

        # 4. Dogrulama
        out = await _run_cmd(["iw", "dev", WIFI_INTERFACE, "info"], check=False)
        is_ap = "type AP" in out
        if is_ap:
            logger.info("WiFi AP basariyla baslatildi")
        else:
            logger.warning("WiFi AP baslatildi ancak AP modu dogrulanamadi")

        return True
    except Exception as e:
        logger.error(f"WiFi AP baslatma hatasi: {e}")
        return False


async def stop_wifi_ap() -> bool:
    """WiFi AP durdur: hostapd durdur + wlan0'i br0'dan cikar."""
    try:
        # 1. hostapd durdur
        await _run_cmd(["sudo", "systemctl", "stop", "hostapd"], check=False)

        # 2. Misafir AP durdur (varsa)
        await _run_cmd(["sudo", "systemctl", "stop", "hostapd-guest"], check=False)

        # 3. wlan0'i br0'dan cikar
        await _run_cmd(
            ["sudo", "ip", "link", "set", WIFI_INTERFACE, "nomaster"],
            check=False,
        )

        logger.info("WiFi AP durduruldu")
        return True
    except Exception as e:
        logger.error(f"WiFi AP durdurma hatasi: {e}")
        return False


async def restart_wifi_ap() -> bool:
    """WiFi AP yeniden baslat (config degisikligi sonrasi)."""
    await stop_wifi_ap()
    await asyncio.sleep(1)
    return await start_wifi_ap()


# ===== MISAFIR AG =====

async def start_guest_ap() -> bool:
    """Misafir sanal AP basalt."""
    try:
        # Sanal interface olustur
        await _run_cmd(
            ["sudo", "iw", "dev", WIFI_INTERFACE, "interface", "add",
             "wlan0_guest", "type", "__ap"],
            check=False,
        )
        await _run_cmd(
            ["sudo", "ip", "link", "set", "wlan0_guest", "master", BRIDGE_INTERFACE],
            check=False,
        )
        await _run_cmd(
            ["sudo", "hostapd", "-B", str(HOSTAPD_GUEST_CONF)],
            check=False,
        )
        logger.info("Misafir WiFi AP baslatildi")
        return True
    except Exception as e:
        logger.error(f"Misafir AP baslatma hatasi: {e}")
        return False


async def stop_guest_ap() -> bool:
    """Misafir sanal AP durdur."""
    try:
        # hostapd-guest procesi durdur
        await _run_cmd(["sudo", "pkill", "-f", "hostapd.*guest"], check=False)
        await asyncio.sleep(0.5)
        # Sanal interface sil
        await _run_cmd(["sudo", "iw", "dev", "wlan0_guest", "del"], check=False)
        logger.info("Misafir WiFi AP durduruldu")
        return True
    except Exception as e:
        logger.error(f"Misafir AP durdurma hatasi: {e}")
        return False


# ===== MAC FILTRE =====

async def set_mac_filter(mode: str, mac_list: list[str]) -> bool:
    """MAC filtre dosyalarini yaz."""
    try:
        # MAC adreslerini dogrula
        mac_re = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
        clean_macs = [m.upper() for m in mac_list if mac_re.match(m)]
        content = "\n".join(clean_macs) + "\n" if clean_macs else "\n"

        if mode == "whitelist":
            await _sudo_write_file(str(HOSTAPD_ACCEPT_FILE), content)
            logger.info(f"MAC whitelist yazildi: {len(clean_macs)} adres")
        elif mode == "blacklist":
            await _sudo_write_file(str(HOSTAPD_DENY_FILE), content)
            logger.info(f"MAC blacklist yazildi: {len(clean_macs)} adres")
        else:
            logger.info("MAC filtre devre disi")

        return True
    except Exception as e:
        logger.error(f"MAC filtre yazma hatasi: {e}")
        return False

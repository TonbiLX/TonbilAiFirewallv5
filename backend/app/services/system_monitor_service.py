# --- Ajan: ANALIST (THE ANALYST) ---
# Sistem Monitörü Servisi: RPi5 donanım metrik toplama,
# bellek ici gecmis, fan kontrolü.
# Docker container içinden /host-proc ve /host-sys üzerinden okuma yapar.

import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tonbilai.system_monitor")

# --- Donanım yollari (Native - Docker degil) ---
HOST_PROC = Path("/proc")
HOST_SYS_THERMAL = Path("/sys/devices/virtual/thermal/thermal_zone0")
HOST_SYS_FAN = Path("/sys/devices/platform/cooling_fan")
HOST_SYS_CPU = Path("/sys/devices/system/cpu")

# --- Sabitler ---
HISTORY_MAXLEN = 60          # 60 nokta = 5 dk (5 sn aralık)
COLLECT_INTERVAL = 5         # saniye
FAN_CONFIG_FILE = Path("/tmp/tonbilai-fan-config.json")

# --- Modul Durumu (Singleton) ---
_hardware_info: Optional[dict] = None
_metrics_history: deque = deque(maxlen=HISTORY_MAXLEN)
_current_metrics: Optional[dict] = None
_fan_config: dict = {
    "mode": "auto",
    "manual_pwm": 128,
    "auto_temp_low": 50.0,
    "auto_temp_mid": 60.0,
    "auto_temp_high": 70.0,
}
_prev_cpu_times: Optional[tuple] = None
_prev_net_bytes: dict = {}
_hwmon_fan_path: Optional[Path] = None
_hwmon_pwm_path: Optional[Path] = None


# ============================================================
# DOSYA OKUMA YARDIMCISI
# ============================================================

def _read_file(path: Path, default: str = "") -> str:
    """Guvenli dosya okuma."""
    try:
        return path.read_text().strip()
    except Exception:
        return default


# ============================================================
# FAN HWMON KESFETME
# ============================================================

def _find_fan_hwmon() -> tuple[Optional[Path], Optional[Path]]:
    """RPi5 Active Cooler'in hwmon dizinini bul.
    /host-sys/cooling_fan/hwmon/hwmonX içinde fan1_input arar.
    Returns: (fan_input_path, pwm_path) veya (None, None).
    """
    try:
        hwmon_parent = HOST_SYS_FAN / "hwmon"
        if not hwmon_parent.exists():
            # Dogrudan cooling_fan altinda da olabilir
            fan_input = HOST_SYS_FAN / "fan1_input"
            if fan_input.exists():
                pwm_file = HOST_SYS_FAN / "pwm1"
                return (fan_input, pwm_file if pwm_file.exists() else None)
            return (None, None)
        for hwmon_dir in sorted(hwmon_parent.iterdir()):
            if not hwmon_dir.is_dir():
                continue
            fan_input = hwmon_dir / "fan1_input"
            pwm_file = hwmon_dir / "pwm1"
            if fan_input.exists():
                name = _read_file(hwmon_dir / "name")
                logger.info(f"Fan hwmon bulundu: {hwmon_dir} (name={name})")
                return (fan_input, pwm_file if pwm_file.exists() else None)
    except Exception as e:
        logger.debug(f"Fan hwmon arama hatasi: {e}")
    return (None, None)


# ============================================================
# DONANIM OKUMA FONKSIYONLARI
# ============================================================

def read_cpu_temperature() -> float:
    """CPU sicakligini oku (derece Celsius)."""
    raw = _read_file(HOST_SYS_THERMAL / "temp", "0")
    try:
        return int(raw) / 1000.0
    except ValueError:
        return 0.0


def read_cpu_frequency() -> float:
    """Anlik CPU frekansini MHz olarak oku."""
    raw = _read_file(HOST_SYS_CPU / "cpu0" / "cpufreq" / "scaling_cur_freq", "0")
    try:
        return int(raw) / 1000.0
    except ValueError:
        return 0.0


def read_cpu_max_frequency() -> float:
    """Maksimum CPU frekansini MHz olarak oku."""
    raw = _read_file(HOST_SYS_CPU / "cpu0" / "cpufreq" / "cpuinfo_max_freq", "0")
    try:
        return int(raw) / 1000.0
    except ValueError:
        return 0.0


def read_cpu_usage() -> float:
    """CPU kullanım yuzdesi (/proc/stat delta)."""
    global _prev_cpu_times
    try:
        content = _read_file(HOST_PROC / "stat")
        stat_line = ""
        for line in content.splitlines():
            if line.startswith("cpu "):
                stat_line = line
                break
        if not stat_line:
            return 0.0

        parts = stat_line.split()
        values = [int(x) for x in parts[1:]]
        idle = values[3] + values[4]   # idle + iowait
        total = sum(values)

        if _prev_cpu_times is None:
            _prev_cpu_times = (idle, total)
            return 0.0

        prev_idle, prev_total = _prev_cpu_times
        _prev_cpu_times = (idle, total)

        idle_delta = idle - prev_idle
        total_delta = total - prev_total
        if total_delta == 0:
            return 0.0

        usage = (1.0 - idle_delta / total_delta) * 100.0
        return round(max(0.0, min(100.0, usage)), 1)
    except Exception as e:
        logger.debug(f"CPU usage okuma hatasi: {e}")
        return 0.0


def read_memory() -> dict:
    """/proc/meminfo oku. MB cinsinden dondur."""
    try:
        content = _read_file(HOST_PROC / "meminfo")
        info = {}
        for line in content.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                info[key] = int(parts[1])

        total = info.get("MemTotal", 0) / 1024.0
        available = info.get("MemAvailable", 0) / 1024.0
        used = total - available
        pct = (used / total * 100) if total > 0 else 0

        return {
            "total_mb": round(total, 1),
            "available_mb": round(available, 1),
            "used_mb": round(used, 1),
            "usage_percent": round(pct, 1),
        }
    except Exception as e:
        logger.debug(f"Memory okuma hatasi: {e}")
        return {"total_mb": 0, "available_mb": 0, "used_mb": 0, "usage_percent": 0}


def read_disk() -> dict:
    """Disk kullanımini oku (os.statvfs)."""
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        total_gb = total / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        pct = (used / total * 100) if total > 0 else 0
        return {
            "total_gb": round(total_gb, 1),
            "free_gb": round(free_gb, 1),
            "used_gb": round(used_gb, 1),
            "usage_percent": round(pct, 1),
        }
    except Exception as e:
        logger.debug(f"Disk okuma hatasi: {e}")
        return {"total_gb": 0, "free_gb": 0, "used_gb": 0, "usage_percent": 0}


def read_network() -> list[dict]:
    """/proc/net/dev oku, interface başına RX/TX byte ve hiz hesapla."""
    global _prev_net_bytes
    result = []
    now = time.monotonic()
    try:
        content = _read_file(HOST_PROC / "net" / "dev")
        for line in content.splitlines()[2:]:
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0].rstrip(":")
            if iface == "lo":
                continue
            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])

            rx_rate = 0.0
            tx_rate = 0.0
            prev = _prev_net_bytes.get(iface)
            if prev:
                prev_rx, prev_tx, prev_time = prev
                elapsed = now - prev_time
                if elapsed > 0:
                    rx_rate = ((rx_bytes - prev_rx) * 8) / (elapsed * 1000)
                    tx_rate = ((tx_bytes - prev_tx) * 8) / (elapsed * 1000)

            _prev_net_bytes[iface] = (rx_bytes, tx_bytes, now)

            result.append({
                "interface": iface,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "rx_rate_kbps": round(max(0, rx_rate), 1),
                "tx_rate_kbps": round(max(0, tx_rate), 1),
            })
    except Exception as e:
        logger.debug(f"Network okuma hatasi: {e}")
    return result


def read_fan() -> dict:
    """Fan RPM ve PWM oku."""
    global _hwmon_fan_path, _hwmon_pwm_path

    if _hwmon_fan_path is None:
        _hwmon_fan_path, _hwmon_pwm_path = _find_fan_hwmon()

    rpm = 0
    pwm = 0
    if _hwmon_fan_path:
        try:
            rpm = int(_read_file(_hwmon_fan_path, "0"))
        except ValueError:
            pass
    if _hwmon_pwm_path:
        try:
            pwm = int(_read_file(_hwmon_pwm_path, "0"))
        except ValueError:
            pass

    return {
        "rpm": rpm,
        "pwm": pwm,
        "pwm_percent": round(pwm / 255 * 100, 1) if pwm > 0 else 0.0,
    }


def read_uptime() -> float:
    """Sistem uptime (saniye)."""
    raw = _read_file(HOST_PROC / "uptime", "0 0")
    try:
        return float(raw.split()[0])
    except (ValueError, IndexError):
        return 0.0


def read_hardware_info() -> dict:
    """Statik donanım bilgilerini oku (bir kez cagirilir)."""
    global _hardware_info
    if _hardware_info:
        return _hardware_info

    # Model: /proc/device-tree/model (bind mount içinde olmayabilir)
    model = _read_file(HOST_PROC / "device-tree" / "model", "")
    model = model.rstrip("\x00")
    if not model:
        # Fallback: /sys path veya kernel version'dan cikar
        kernel_ver = _read_file(HOST_PROC / "version", "")
        if "rpi-2712" in kernel_ver or "raspberrypi" in kernel_ver:
            model = "Raspberry Pi 5"
        elif "rpi" in kernel_ver:
            model = "Raspberry Pi"
        else:
            model = "Linux Sistemi"

    # CPU bilgisi: ARM64 cpuinfo'da Hardware satiri yok
    cpuinfo = _read_file(HOST_PROC / "cpuinfo")
    cpu_model = "Unknown"
    cpu_cores = 0
    cpu_part = ""
    for line in cpuinfo.splitlines():
        if line.startswith("Hardware"):
            cpu_model = line.split(":")[1].strip()
        if line.startswith("CPU part"):
            cpu_part = line.split(":")[1].strip()
        if line.startswith("processor"):
            cpu_cores += 1

    # ARM CPU part numarasindan model cikar
    if cpu_model == "Unknown" and cpu_part:
        arm_parts = {
            "0xd0b": "ARM Cortex-A76 (BCM2712)",
            "0xd08": "ARM Cortex-A72 (BCM2711)",
            "0xd03": "ARM Cortex-A53 (BCM2837)",
        }
        cpu_model = arm_parts.get(cpu_part, f"ARM ({cpu_part})")

    # Maks frekans
    cpu_max_freq = read_cpu_max_frequency()

    # RAM
    mem = read_memory()

    # Disk
    disk = read_disk()

    # OS bilgisi
    os_info = _read_file(HOST_PROC / "version", "Unknown")

    _hardware_info = {
        "model": model,
        "cpu_model": cpu_model,
        "cpu_cores": cpu_cores,
        "cpu_max_freq_mhz": cpu_max_freq,
        "ram_total_mb": mem["total_mb"],
        "disk_total_gb": disk["total_gb"],
        "os_info": os_info[:120],
    }

    logger.info(
        f"Donanım: {model}, {cpu_cores} cekirdek, "
        f"{mem['total_mb']:.0f}MB RAM, {disk['total_gb']:.1f}GB disk"
    )
    return _hardware_info


# ============================================================
# FAN KONTROL
# ============================================================

def _load_fan_config():
    """Fan config'i JSON dosyadan yukle."""
    global _fan_config
    try:
        if FAN_CONFIG_FILE.exists():
            data = json.loads(FAN_CONFIG_FILE.read_text())
            _fan_config.update(data)
            logger.info(f"Fan config yuklendi: mode={_fan_config['mode']}")
    except Exception as e:
        logger.debug(f"Fan config yüklenemedi: {e}")


def _save_fan_config():
    """Fan config'i JSON dosyaya kaydet."""
    try:
        FAN_CONFIG_FILE.write_text(json.dumps(_fan_config, indent=2))
    except Exception as e:
        logger.debug(f"Fan config kaydedilemedi: {e}")


def _write_fan_pwm(pwm_value: int):
    """Fan PWM degerini yaz (0-255)."""
    global _hwmon_fan_path, _hwmon_pwm_path

    if _hwmon_pwm_path is None:
        _, _hwmon_pwm_path = _find_fan_hwmon()

    if _hwmon_pwm_path is None:
        logger.debug("Fan PWM yolu bulunamadı, yazma atlandi.")
        return

    pwm_value = max(0, min(255, pwm_value))

    try:
        # Manuel mod aktif et (pwm1_enable: 1=manual)
        enable_path = _hwmon_pwm_path.parent / "pwm1_enable"
        if enable_path.exists():
            enable_path.write_text("1")

        _hwmon_pwm_path.write_text(str(pwm_value))
        logger.debug(f"Fan PWM ayarlandi: {pwm_value}")
    except PermissionError:
        logger.warning(f"Fan PWM yazma yetkisi yok: {_hwmon_pwm_path}")
    except Exception as e:
        logger.error(f"Fan PWM yazma hatasi: {e}")


def _apply_auto_fan(temperature: float):
    """Sicakliga göre otomatik fan egrisi uygula."""
    config = _fan_config
    t_low = config["auto_temp_low"]
    t_mid = config["auto_temp_mid"]
    t_high = config["auto_temp_high"]

    if temperature <= t_low:
        pwm = 0
    elif temperature >= t_high:
        pwm = 255
    elif temperature <= t_mid:
        ratio = (temperature - t_low) / max(t_mid - t_low, 1)
        pwm = int(ratio * 128)
    else:
        ratio = (temperature - t_mid) / max(t_high - t_mid, 1)
        pwm = int(128 + ratio * 127)

    _write_fan_pwm(pwm)


def get_fan_config() -> dict:
    """Fan config'i dondur."""
    return dict(_fan_config)


def update_fan_config(updates: dict) -> dict:
    """Fan config'i güncelle ve hemen uygula."""
    global _fan_config

    for key in ("mode", "manual_pwm", "auto_temp_low", "auto_temp_mid", "auto_temp_high"):
        if key in updates and updates[key] is not None:
            _fan_config[key] = updates[key]

    if _fan_config["mode"] not in ("auto", "manual"):
        _fan_config["mode"] = "auto"

    # Hemen uygula
    if _fan_config["mode"] == "manual":
        _write_fan_pwm(_fan_config["manual_pwm"])
    else:
        temp = read_cpu_temperature()
        _apply_auto_fan(temp)

    _save_fan_config()
    logger.info(f"Fan config güncellendi: {_fan_config}")
    return dict(_fan_config)


# ============================================================
# METRIK TOPLAMA & WORKER
# ============================================================

def collect_metrics() -> tuple[dict, dict]:
    """Tum metrikleri topla. (snapshot, history_point) tuple dondurur."""
    cpu_usage = read_cpu_usage()
    cpu_temp = read_cpu_temperature()
    cpu_freq = read_cpu_frequency()
    mem = read_memory()
    disk = read_disk()
    net = read_network()
    fan = read_fan()
    uptime = read_uptime()

    # Fan kontrolü: otomatik veya manuel
    if _fan_config["mode"] == "auto":
        _apply_auto_fan(cpu_temp)
    elif _fan_config["mode"] == "manual":
        _write_fan_pwm(_fan_config["manual_pwm"])

    ts = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "timestamp": ts,
        "cpu": {
            "usage_percent": cpu_usage,
            "temperature_c": cpu_temp,
            "frequency_mhz": cpu_freq,
        },
        "memory": mem,
        "disk": disk,
        "fan": fan,
        "network": net,
        "uptime_seconds": uptime,
    }

    total_rx = sum(n.get("rx_rate_kbps", 0) for n in net)
    total_tx = sum(n.get("tx_rate_kbps", 0) for n in net)

    history_point = {
        "timestamp": ts,
        "cpu_usage": cpu_usage,
        "cpu_temp": cpu_temp,
        "ram_usage": mem["usage_percent"],
        "net_rx_kbps": round(total_rx, 1),
        "net_tx_kbps": round(total_tx, 1),
        "fan_rpm": fan["rpm"],
    }

    return snapshot, history_point


def get_current_metrics() -> Optional[dict]:
    """Son metrik snapshot'ini dondur."""
    return _current_metrics


def get_metrics_history() -> list[dict]:
    """Gecmis veri noktalarıni dondur."""
    return list(_metrics_history)


async def start_system_monitor_worker():
    """Arka plan worker: her 5 saniyede metrik topla."""
    global _current_metrics

    logger.info("Sistem Monitörü worker başlatildi.")

    _load_fan_config()
    read_hardware_info()

    # Ilk okuma (CPU delta için)
    try:
        collect_metrics()
    except Exception:
        pass
    await asyncio.sleep(1)

    while True:
        try:
            snapshot, history_point = collect_metrics()
            _current_metrics = snapshot
            _metrics_history.append(history_point)
        except Exception as e:
            logger.error(f"Metrik toplama hatasi: {e}")

        await asyncio.sleep(COLLECT_INTERVAL)

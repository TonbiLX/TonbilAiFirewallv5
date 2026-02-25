# --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
# Sistem Monitörü Pydantic semalari: donanım bilgileri, metrikler, fan kontrolü.

from pydantic import BaseModel, Field
from typing import Optional


class SystemHardwareInfo(BaseModel):
    """Statik donanım bilgileri."""
    model: str = "Unknown"
    cpu_model: str = "Unknown"
    cpu_cores: int = 0
    cpu_max_freq_mhz: float = 0.0
    ram_total_mb: float = 0.0
    disk_total_gb: float = 0.0
    os_info: str = "Unknown"


class CpuMetrics(BaseModel):
    usage_percent: float = 0.0
    temperature_c: float = 0.0
    frequency_mhz: float = 0.0


class MemoryMetrics(BaseModel):
    used_mb: float = 0.0
    total_mb: float = 0.0
    available_mb: float = 0.0
    usage_percent: float = 0.0


class DiskMetrics(BaseModel):
    used_gb: float = 0.0
    total_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0


class NetworkInterfaceMetrics(BaseModel):
    interface: str
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_rate_kbps: float = 0.0
    tx_rate_kbps: float = 0.0


class FanMetrics(BaseModel):
    rpm: int = 0
    pwm: int = 0
    pwm_percent: float = 0.0


class SystemMetricsSnapshot(BaseModel):
    """Tek bir anlik metrik noktasi."""
    timestamp: str
    cpu: CpuMetrics = CpuMetrics()
    memory: MemoryMetrics = MemoryMetrics()
    disk: DiskMetrics = DiskMetrics()
    fan: FanMetrics = FanMetrics()
    network: list[NetworkInterfaceMetrics] = []
    uptime_seconds: float = 0.0


class SystemMetricsHistoryPoint(BaseModel):
    """Grafik için hafif gecmis noktasi."""
    timestamp: str
    cpu_usage: float = 0.0
    cpu_temp: float = 0.0
    ram_usage: float = 0.0
    net_rx_kbps: float = 0.0
    net_tx_kbps: float = 0.0
    fan_rpm: int = 0


class SystemMetricsResponse(BaseModel):
    """Anlik metrikler + gecmis."""
    current: SystemMetricsSnapshot
    history: list[SystemMetricsHistoryPoint] = []


class FanConfig(BaseModel):
    """Fan kontrol yapılandirmasi."""
    mode: str = "auto"
    manual_pwm: int = Field(default=128, ge=0, le=255)
    auto_temp_low: float = 50.0
    auto_temp_mid: float = 60.0
    auto_temp_high: float = 70.0


class FanConfigUpdate(BaseModel):
    """Fan config güncelleme istegi."""
    mode: Optional[str] = None
    manual_pwm: Optional[int] = Field(default=None, ge=0, le=255)
    auto_temp_low: Optional[float] = None
    auto_temp_mid: Optional[float] = None
    auto_temp_high: Optional[float] = None

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WiFi AP Pydantic semalari: istek/yanit dogrulama.

from pydantic import BaseModel, field_validator
from typing import Optional


class WifiStatusResponse(BaseModel):
    """WiFi AP canli durum bilgisi."""
    enabled: bool = False
    ssid: Optional[str] = None
    channel: Optional[int] = None
    band: Optional[str] = None
    tx_power: Optional[int] = None
    clients_count: int = 0
    interface: str = "wlan0"


class WifiConfigResponse(BaseModel):
    """DB'deki WiFi ayarlari (sifre maskelenmis)."""
    ssid: str = "TonbilAiOS"
    password: Optional[str] = None
    channel: int = 6
    band: str = "2.4GHz"
    tx_power: int = 20
    hidden_ssid: bool = False
    enabled: bool = False
    guest_enabled: bool = False
    guest_ssid: Optional[str] = None
    guest_password: Optional[str] = None
    mac_filter_mode: str = "disabled"
    mac_filter_list: list[str] = []
    schedule_enabled: bool = False
    schedule_start: Optional[str] = None
    schedule_stop: Optional[str] = None


class WifiConfigUpdate(BaseModel):
    """WiFi ana ag ayarlarini guncelle."""
    ssid: Optional[str] = None
    password: Optional[str] = None
    channel: Optional[int] = None
    band: Optional[str] = None
    tx_power: Optional[int] = None
    hidden_ssid: Optional[bool] = None

    @field_validator("ssid")
    @classmethod
    def validate_ssid(cls, v: str | None) -> str | None:
        if v is not None and (len(v) < 1 or len(v) > 32):
            raise ValueError("SSID 1-32 karakter olmali")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None and v != "" and (len(v) < 8 or len(v) > 63):
            raise ValueError("Sifre 8-63 karakter olmali")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: int | None) -> int | None:
        if v is not None and v != 0 and not (1 <= v <= 196):
            raise ValueError("Kanal 0 (auto), 1-13 (2.4GHz) veya 36-165 (5GHz) olmali")
        return v

    @field_validator("tx_power")
    @classmethod
    def validate_tx_power(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("TX gucu 1-31 dBm arasinda olmali")
        return v

    @field_validator("band")
    @classmethod
    def validate_band(cls, v: str | None) -> str | None:
        if v is not None and v not in ("2.4GHz", "5GHz"):
            raise ValueError("Band '2.4GHz' veya '5GHz' olmali")
        return v


class WifiGuestUpdate(BaseModel):
    """Misafir ag ayarlarini guncelle."""
    guest_enabled: Optional[bool] = None
    guest_ssid: Optional[str] = None
    guest_password: Optional[str] = None

    @field_validator("guest_ssid")
    @classmethod
    def validate_ssid(cls, v: str | None) -> str | None:
        if v is not None and (len(v) < 1 or len(v) > 32):
            raise ValueError("Misafir SSID 1-32 karakter olmali")
        return v

    @field_validator("guest_password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None and v != "" and (len(v) < 8 or len(v) > 63):
            raise ValueError("Misafir sifresi 8-63 karakter olmali")
        return v


class WifiScheduleUpdate(BaseModel):
    """Zamanlama ayarlarini guncelle."""
    schedule_enabled: Optional[bool] = None
    schedule_start: Optional[str] = None  # "HH:MM"
    schedule_stop: Optional[str] = None

    @field_validator("schedule_start", "schedule_stop")
    @classmethod
    def validate_time(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^\d{2}:\d{2}$", v):
                raise ValueError("Saat formati HH:MM olmali")
            h, m = v.split(":")
            if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                raise ValueError("Gecersiz saat")
        return v


class WifiMacFilterUpdate(BaseModel):
    """MAC filtre ayarlarini guncelle."""
    mac_filter_mode: str = "disabled"  # "disabled" | "whitelist" | "blacklist"
    mac_filter_list: list[str] = []

    @field_validator("mac_filter_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("disabled", "whitelist", "blacklist"):
            raise ValueError("MAC filtre modu: disabled, whitelist veya blacklist")
        return v


class WifiClientResponse(BaseModel):
    """Bagli WiFi istemci bilgisi."""
    mac_address: str
    ip_address: Optional[str] = None
    signal_dbm: int = 0
    tx_bitrate_mbps: float = 0.0
    rx_bitrate_mbps: float = 0.0
    connected_seconds: int = 0
    hostname: Optional[str] = None

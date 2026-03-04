# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WiFi AP konfigürasyon modeli: hostapd ayarlarini DB'de saklar.

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func

from app.db.base import Base


class WifiConfig(Base):
    __tablename__ = "wifi_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interface = Column(String(20), default="wlan0")
    ssid = Column(String(32), nullable=False, default="TonbilAiOS")
    password = Column(String(63), nullable=True)          # WPA2: 8-63 char
    channel = Column(Integer, default=6)
    band = Column(String(10), default="2.4GHz")           # "2.4GHz" | "5GHz"
    tx_power = Column(Integer, default=20)                 # dBm (1-31)
    hidden_ssid = Column(Boolean, default=False)
    enabled = Column(Boolean, default=False)

    # Misafir agi
    guest_enabled = Column(Boolean, default=False)
    guest_ssid = Column(String(32), default="TonbilAiOS-Misafir")
    guest_password = Column(String(63), nullable=True)

    # MAC filtre
    mac_filter_mode = Column(String(20), default="disabled")  # disabled/whitelist/blacklist
    mac_filter_list = Column(Text, nullable=True)              # JSON array

    # Zamanlama
    schedule_enabled = Column(Boolean, default=False)
    schedule_start = Column(String(5), nullable=True)     # "08:00"
    schedule_stop = Column(String(5), nullable=True)      # "23:00"

    # Meta
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# --- Ajan: MIMAR (THE ARCHITECT) ---
# Cihaz modeli: aga bagli her cihaz (gercek veya simule).

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mac_address = Column(String(17), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    hostname = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    is_blocked = Column(Boolean, default=False)
    is_online = Column(Boolean, default=True)
    first_seen = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now())
    total_online_seconds = Column(Integer, default=0)
    last_online_start = Column(DateTime, nullable=True)

    # DNS Fingerprinting (Faz 3.5 v3)
    detected_os = Column(String(100), nullable=True)       # "Android", "iOS", "Windows", "Tizen"
    device_type = Column(String(50), nullable=True)         # "phone", "tv", "computer", "iot", "vr_headset"

    # Bant genişliği sinirlandirma
    bandwidth_limit_mbps = Column(Integer, nullable=True)   # None = limitsiz, >0 = Mbps sinir

    # IPTV cihaz modu: DNS filtreleme bypass + multicast öncelik
    is_iptv = Column(Boolean, default=False)

    # Dış DNS istemcisi: Pi'ye dışarıdan bağlanan cihaz (DoT/DoH/DNS)
    is_external = Column(Boolean, default=False)
    connection_type = Column(String(10), nullable=True)  # "dns" | "dot" | "doh"

    # Risk Degerlendirme (Faz 3.5 v3)
    risk_score = Column(Integer, default=0)                 # 0-100 risk puani
    risk_level = Column(String(20), default="safe")         # safe/suspicious/dangerous
    last_risk_assessment = Column(DateTime, nullable=True)  # Son değerlendirme zamani

    # Iliskiler
    profile = relationship("Profile", back_populates="devices")
    traffic_logs = relationship("TrafficLog", back_populates="device")

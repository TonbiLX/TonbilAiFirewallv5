# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DDoS koruma yapılandirma modeli: tek satirlik config tablosu.
# 8 koruma mekanizmasi: SYN/UDP/ICMP flood, bağlantı limiti,
# geçersiz paket, HTTP flood, kernel sertlestirme, uvicorn worker.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.base import Base


class DdosConfig(Base):
    """DDoS koruma yapılandirmasi (singleton)."""
    __tablename__ = "ddos_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 1. SYN Flood Korumasi
    syn_flood_enabled = Column(Boolean, default=True)
    syn_flood_rate = Column(Integer, default=25)       # paket/saniye
    syn_flood_burst = Column(Integer, default=50)

    # 2. UDP Flood Korumasi
    udp_flood_enabled = Column(Boolean, default=True)
    udp_flood_rate = Column(Integer, default=50)
    udp_flood_burst = Column(Integer, default=100)

    # 3. ICMP Flood Korumasi
    icmp_flood_enabled = Column(Boolean, default=True)
    icmp_flood_rate = Column(Integer, default=10)
    icmp_flood_burst = Column(Integer, default=20)

    # 4. Bağlantı Limiti (per-IP)
    conn_limit_enabled = Column(Boolean, default=True)
    conn_limit_per_ip = Column(Integer, default=100)

    # 5. Geçersiz Paket Filtreleme
    invalid_packet_enabled = Column(Boolean, default=True)

    # 6. HTTP Flood Korumasi (nginx rate limit)
    http_flood_enabled = Column(Boolean, default=False)
    http_flood_rate = Column(String(20), default="30r/s")
    http_flood_burst = Column(Integer, default=60)

    # 7. Kernel Sertlestirme (sysctl)
    kernel_hardening_enabled = Column(Boolean, default=True)
    tcp_max_syn_backlog = Column(Integer, default=4096)
    tcp_synack_retries = Column(Integer, default=2)
    netfilter_conntrack_max = Column(Integer, default=262144)

    # 8. Uvicorn Worker Sayısı
    uvicorn_workers_enabled = Column(Boolean, default=False)
    uvicorn_workers = Column(Integer, default=2)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

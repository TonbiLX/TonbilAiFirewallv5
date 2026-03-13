# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Guvenlik ayarlari yapilandirma modeli: tek satirlik singleton config tablosu.
# Tehdit analizi, DNS guvenlik, DDoS uyari ve DNS fingerprint sabitleri.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from app.db.base import Base


class SecurityConfig(Base):
    """Guvenlik ayarlari yapilandirmasi (singleton)."""
    __tablename__ = "security_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Tehdit Analizi (threat_analyzer.py) ---
    external_rate_threshold = Column(Integer, default=20)
    local_rate_threshold = Column(Integer, default=300)
    block_duration_sec = Column(Integer, default=3600)
    dga_detection_enabled = Column(Boolean, default=True)
    dga_entropy_threshold = Column(Float, default=3.5)
    insight_cooldown_sec = Column(Integer, default=1800)
    subnet_flood_enabled = Column(Boolean, default=True)
    subnet_flood_threshold = Column(Integer, default=5)
    subnet_window_sec = Column(Integer, default=300)
    subnet_block_duration_sec = Column(Integer, default=3600)
    scan_pattern_enabled = Column(Boolean, default=True)
    scan_pattern_threshold = Column(Integer, default=3)
    scan_pattern_window_sec = Column(Integer, default=300)
    threat_score_auto_block = Column(Integer, default=15)
    threat_score_ttl = Column(Integer, default=3600)
    aggregated_cooldown_sec = Column(Integer, default=1800)

    # --- DNS Guvenlik (dns_proxy.py) ---
    dns_rate_limit_per_sec = Column(Integer, default=5)
    dns_blocked_qtypes = Column(String(100), default="10,252,255")
    sinkhole_ipv4 = Column(String(45), default="192.168.1.2")
    sinkhole_ipv6 = Column(String(45), default="::")

    # --- DDoS Uyari (ddos_service.py) ---
    ddos_alert_syn_flood = Column(Integer, default=100)
    ddos_alert_udp_flood = Column(Integer, default=200)
    ddos_alert_icmp_flood = Column(Integer, default=50)
    ddos_alert_conn_limit = Column(Integer, default=500)
    ddos_alert_invalid_packet = Column(Integer, default=100)
    ddos_alert_cooldown_sec = Column(Integer, default=1800)

    # --- DNS Guvenlik Katmanlari (Kritik 1-2-3) ---
    dnssec_enabled = Column(Boolean, default=True)
    dnssec_mode = Column(String(20), default="log_only")  # log_only, enforce
    dns_tunneling_enabled = Column(Boolean, default=True)
    dns_tunneling_max_subdomain_len = Column(Integer, default=50)
    dns_tunneling_max_labels_per_min = Column(Integer, default=100)
    dns_tunneling_txt_ratio_threshold = Column(Integer, default=30)  # yuzde
    doh_enabled = Column(Boolean, default=True)

    # --- DNS Fingerprint (dns_fingerprint.py) ---
    fingerprint_ttl = Column(Integer, default=3600)
    fingerprint_min_matches = Column(Integer, default=1)
    fingerprint_update_cooldown = Column(Integer, default=300)

    # --- Meta ---
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

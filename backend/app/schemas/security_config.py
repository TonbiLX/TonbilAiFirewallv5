# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Guvenlik ayarlari Pydantic semalari: istek/yanit dogrulama.

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class SecurityConfigResponse(BaseModel):
    """Guvenlik ayarlari yanit semasi."""
    id: int

    # Tehdit Analizi
    external_rate_threshold: int
    local_rate_threshold: int
    block_duration_sec: int
    dga_detection_enabled: bool
    dga_entropy_threshold: float
    insight_cooldown_sec: int
    subnet_flood_enabled: bool
    subnet_flood_threshold: int
    subnet_window_sec: int
    subnet_block_duration_sec: int
    scan_pattern_enabled: bool
    scan_pattern_threshold: int
    scan_pattern_window_sec: int
    threat_score_auto_block: int
    threat_score_ttl: int
    aggregated_cooldown_sec: int

    # DNS Guvenlik
    dns_rate_limit_per_sec: int
    dns_blocked_qtypes: list[int]
    sinkhole_ipv4: str
    sinkhole_ipv6: str

    # DDoS Uyari
    ddos_alert_syn_flood: int
    ddos_alert_udp_flood: int
    ddos_alert_icmp_flood: int
    ddos_alert_conn_limit: int
    ddos_alert_invalid_packet: int
    ddos_alert_cooldown_sec: int

    # DNS Fingerprint
    fingerprint_ttl: int
    fingerprint_min_matches: int
    fingerprint_update_cooldown: int

    # DNS Guvenlik Katmanlari (Kritik 1-2-3)
    dnssec_enabled: bool = True
    dnssec_mode: str = "log_only"
    dns_tunneling_enabled: bool = True
    dns_tunneling_max_subdomain_len: int = 50
    dns_tunneling_max_labels_per_min: int = 100
    dns_tunneling_txt_ratio_threshold: int = 30
    doh_enabled: bool = True

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("dns_blocked_qtypes", mode="before")
    @classmethod
    def parse_blocked_qtypes(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    model_config = {"from_attributes": True}


class SecurityConfigUpdate(BaseModel):
    """Guvenlik ayarlari guncelleme semasi (tum alanlar opsiyonel)."""
    external_rate_threshold: Optional[int] = None
    local_rate_threshold: Optional[int] = None
    block_duration_sec: Optional[int] = None
    dga_detection_enabled: Optional[bool] = None
    dga_entropy_threshold: Optional[float] = None
    insight_cooldown_sec: Optional[int] = None
    subnet_flood_enabled: Optional[bool] = None
    subnet_flood_threshold: Optional[int] = None
    subnet_window_sec: Optional[int] = None
    subnet_block_duration_sec: Optional[int] = None
    scan_pattern_enabled: Optional[bool] = None
    scan_pattern_threshold: Optional[int] = None
    scan_pattern_window_sec: Optional[int] = None
    threat_score_auto_block: Optional[int] = None
    threat_score_ttl: Optional[int] = None
    aggregated_cooldown_sec: Optional[int] = None

    dns_rate_limit_per_sec: Optional[int] = None
    dns_blocked_qtypes: Optional[str] = None
    sinkhole_ipv4: Optional[str] = None
    sinkhole_ipv6: Optional[str] = None

    ddos_alert_syn_flood: Optional[int] = None
    ddos_alert_udp_flood: Optional[int] = None
    ddos_alert_icmp_flood: Optional[int] = None
    ddos_alert_conn_limit: Optional[int] = None
    ddos_alert_invalid_packet: Optional[int] = None
    ddos_alert_cooldown_sec: Optional[int] = None

    fingerprint_ttl: Optional[int] = None
    fingerprint_min_matches: Optional[int] = None
    fingerprint_update_cooldown: Optional[int] = None

    # DNS Guvenlik Katmanlari (Kritik 1-2-3)
    dnssec_enabled: Optional[bool] = None
    dnssec_mode: Optional[str] = None
    dns_tunneling_enabled: Optional[bool] = None
    dns_tunneling_max_subdomain_len: Optional[int] = None
    dns_tunneling_max_labels_per_min: Optional[int] = None
    dns_tunneling_txt_ratio_threshold: Optional[int] = None
    doh_enabled: Optional[bool] = None


class SecurityStatsResponse(BaseModel):
    """Canli guvenlik istatistikleri."""
    blocked_ip_count: int = 0
    total_auto_blocks: int = 0
    total_external_blocked: int = 0
    total_suspicious: int = 0
    dga_detections: int = 0
    blocked_subnet_count: int = 0
    last_threat_time: str | None = None

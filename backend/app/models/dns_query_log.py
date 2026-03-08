# --- Ajan: MUHAFIZ (THE GUARDIAN) + ANALIST (THE ANALYST) ---
# DNS sorgu log modeli: her DNS cozumleme girişiminin kaydi.
# Engellenen ve izin verilen sorgular ayri takip edilir.

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.base import Base


class DnsQueryLog(Base):
    __tablename__ = "dns_query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, index=True)
    client_ip = Column(String(45), nullable=True)
    domain = Column(String(255), nullable=False, index=True)
    query_type = Column(String(10), default="A")
    blocked = Column(Boolean, default=False, index=True)
    block_reason = Column(String(255), nullable=True)
    upstream_response_ms = Column(Integer, nullable=True)
    answer_ip = Column(String(45), nullable=True)

    # 5651 Kanun Uyumu: ek alanlar
    mac_address = Column(String(17), nullable=True)         # Cihaz MAC adresi (denormalize)
    destination_port = Column(Integer, nullable=True)        # Hedef port (DNS=53, DoT=853)
    wan_ip = Column(String(45), nullable=True)               # Dış IP (NAT ceviri için)

    # Kaynak tipi: INTERNAL (yerel LAN), EXTERNAL (dışarıdan gelen), DOT (DNS-over-TLS)
    source_type = Column(String(20), nullable=True, default="INTERNAL", index=True)

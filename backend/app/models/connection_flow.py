# --- Ajan: ANALIST (THE ANALYST) ---
# Baglanti akisi modeli: conntrack'ten gelen per-flow detay kayitlari.
# Her bir TCP/UDP baglantisinin src/dst IP:port, byte, paket, durum bilgisini saklar.

from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ConnectionFlow(Base):
    __tablename__ = "connection_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Flow kimligi: md5(src_ip:src_port:dst_ip:dst_port:proto)[:16]
    flow_id = Column(String(32), nullable=False, index=True)

    # Cihaz (LAN kaynagi)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # Kaynak (LAN cihazi)
    src_ip = Column(String(45), nullable=False)
    src_port = Column(Integer, nullable=True)

    # Hedef (dis sunucu)
    dst_ip = Column(String(45), nullable=False)
    dst_port = Column(Integer, nullable=True)
    dst_domain = Column(String(255), nullable=True)

    # Protokol ve durum
    protocol = Column(String(10), nullable=False)   # TCP, UDP
    state = Column(String(20), nullable=True)        # ESTABLISHED, TIME_WAIT, SYN_SENT ...

    # Byte ve paket sayaclari (toplam, conntrack'ten)
    bytes_sent = Column(BigInteger, default=0)       # cihaz -> dis (upload)
    bytes_received = Column(BigInteger, default=0)   # dis -> cihaz (download)
    packets_sent = Column(BigInteger, default=0)
    packets_received = Column(BigInteger, default=0)

    # Kategori
    category = Column(String(100), nullable=True)

    # Zaman damgalari
    first_seen = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)  # NULL = hala aktif

    # Composite indexler
    __table_args__ = (
        Index("idx_cf_device_lastseen", "device_id", "last_seen"),
        Index("idx_cf_dst_domain", "dst_domain"),
        Index("idx_cf_ended", "ended_at"),
        Index("idx_cf_first_seen", "first_seen"),
    )

    # Iliskiler
    device = relationship("Device")

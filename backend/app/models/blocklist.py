# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Blocklist kaynak modeli: DNS engelleme listeleri ve yönetimi.
# AdGuard, Steven Black gibi kaynaklardan indirilen domain listeleri.

import enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.sql import func

from app.db.base import Base


class BlocklistFormat(str, enum.Enum):
    HOSTS = "hosts"              # 0.0.0.0 domain.com veya 127.0.0.1 domain.com
    DOMAIN_LIST = "domain_list"  # Satır başına bir domain
    ADBLOCK = "adblock"          # ||domain.com^ formati


class Blocklist(Base):
    __tablename__ = "blocklists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    format = Column(SAEnum(BlocklistFormat), default=BlocklistFormat.HOSTS)
    enabled = Column(Boolean, default=True)
    domain_count = Column(Integer, default=0)
    last_updated = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)  # SHA256 checksum - degismemis içerik için tekrar parse onleme
    update_frequency_hours = Column(Integer, default=24)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

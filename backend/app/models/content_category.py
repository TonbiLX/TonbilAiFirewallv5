# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# İçerik filtre kategorisi modeli: engelleme kategorilerini tanimlar.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from app.db.base import Base


class ContentCategory(Base):
    """İçerik filtre kategorisi - profillerde kullanilan engelleme gruplari."""
    __tablename__ = "content_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)  # "gambling", "adult", vb.
    name = Column(String(100), nullable=False)  # "Kumar Siteleri"
    description = Column(Text, nullable=True)  # Detayli açıklama
    icon = Column(String(50), nullable=True)  # Lucide icon adi
    color = Column(String(20), nullable=True)  # "red", "amber", vb.
    example_domains = Column(JSON, nullable=True)  # ["bet365.com", "casino.com"]
    custom_domains = Column(Text, nullable=True)  # Kullanici girisi, satir basina bir domain
    domain_count = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- Ajan: MIMAR (THE ARCHITECT) ---
# Telegram Bot yapılandirma modeli: tek satirlik config tablosu.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.base import Base


class TelegramConfig(Base):
    """Telegram bot yapılandirmasi."""
    __tablename__ = "telegram_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_token = Column(String(255), nullable=True)
    chat_ids = Column(String(500), nullable=True)  # Virgul ile ayrilmis chat ID'ler
    enabled = Column(Boolean, default=False)
    notify_new_device = Column(Boolean, default=True)
    notify_blocked_ip = Column(Boolean, default=True)
    notify_trusted_ip_threat = Column(Boolean, default=True)
    notify_ai_insight = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

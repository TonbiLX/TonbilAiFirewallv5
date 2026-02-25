# --- Ajan: ANALIST (THE ANALYST) ---
# AI Sohbet mesaj modeli: kullanıcı-asistan konusmalarini saklar.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.base import Base


class ChatMessage(Base):
    """AI sohbet gecmisi."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)  # "user" veya "assistant"
    content = Column(Text, nullable=False)
    action_type = Column(String(50), nullable=True)  # "device_update", "dns_block", vb.
    action_result = Column(Text, nullable=True)  # JSON sonuç
    timestamp = Column(DateTime, default=datetime.utcnow)

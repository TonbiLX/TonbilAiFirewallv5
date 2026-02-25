# --- Ajan: ANALIST (THE ANALYST) ---
# AI uretimi icgoruler: anomaliler, oneriler ve uyarılar.

import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.sql import func

from app.db.base import Base


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    severity = Column(SAEnum(Severity), nullable=False, default=Severity.INFO)
    message = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=True)
    related_device_id = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)  # "anomaly", "optimization", "security"
    is_dismissed = Column(Boolean, default=False, nullable=False, server_default="0")

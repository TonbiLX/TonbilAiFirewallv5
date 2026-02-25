# --- Ajan: MIMAR (THE ARCHITECT) ---
# Profil modeli: çocuk/yetişkin/misafir erişim profilleri ve zaman tabanli kurallar.

import enum

from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProfileType(str, enum.Enum):
    CHILD = "child"
    ADULT = "adult"
    GUEST = "guest"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    profile_type = Column(SAEnum(ProfileType), nullable=False, default=ProfileType.ADULT)
    allowed_hours = Column(JSON, nullable=True)           # {"start": "08:00", "end": "22:00"}
    content_filters = Column(JSON, nullable=True)          # ["gambling", "adult"]
    bandwidth_limit_mbps = Column(Integer, nullable=True)  # Maks Mbps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Iliskiler
    devices = relationship("Device", back_populates="profile")

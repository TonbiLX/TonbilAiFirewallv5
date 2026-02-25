# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Kategori-Blocklist iliskisi: icerik kategorilerini engelleme listeleriyle eslestir.

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CategoryBlocklist(Base):
    """Icerik kategorisi ile blocklist arasindaki coka-cok iliski."""
    __tablename__ = "category_blocklists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(
        Integer,
        ForeignKey("content_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blocklist_id = Column(
        Integer,
        ForeignKey("blocklists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("category_id", "blocklist_id", name="uq_category_blocklist"),
    )

    category = relationship("ContentCategory", backref="category_blocklists")
    blocklist = relationship("Blocklist", backref="category_blocklists")

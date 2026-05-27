import uuid

from sqlalchemy import String, Text, ForeignKey, Integer, Index, Uuid as UuidType
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class StrategyVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (
        Index("ix_strategy_versions_sid_ver", "strategy_id", "version"),
    )

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict | None] = mapped_column(postgresql.JSONB, nullable=True)
    change_note: Mapped[str | None] = mapped_column(String(256), nullable=True)
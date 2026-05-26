import uuid

from sqlalchemy import String, ForeignKey, Boolean, Integer, Uuid as UuidType
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class RiskRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=True
    )
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

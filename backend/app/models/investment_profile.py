import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Uuid as UuidType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class InvestmentProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "investment_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_investment_profile_user_version"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    investment_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_stock_weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_industry_weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    min_cash_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_daily_turnover: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)

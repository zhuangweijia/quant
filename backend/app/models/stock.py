from datetime import date

from sqlalchemy import Boolean, Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Stock(TimestampMixin, Base):
    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("symbol", name="uq_stocks_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    in_csi300: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_st: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_quality: Mapped[str] = mapped_column(String(16), default="ok", nullable=False)
    last_synced_date: Mapped[date | None] = mapped_column(Date, nullable=True)

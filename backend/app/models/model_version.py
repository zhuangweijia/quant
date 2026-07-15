from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ModelVersion(TimestampMixin, Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_start: Mapped[date] = mapped_column(Date, nullable=False)
    data_end: Mapped[date] = mapped_column(Date, nullable=False)
    ic: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    val_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    top_features: Mapped[dict | None] = mapped_column(postgresql.JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_path: Mapped[str] = mapped_column(String(256), nullable=False)
    n_estimators: Mapped[int] = mapped_column(Integer, default=200, nullable=False)

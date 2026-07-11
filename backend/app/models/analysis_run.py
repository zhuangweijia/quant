import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Uuid as UuidType
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AnalysisRun(TimestampMixin, Base):
    __tablename__ = "analysis_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stages: Mapped[dict | None] = mapped_column(postgresql.JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SetupRun(TimestampMixin, Base):
    __tablename__ = "setup_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stages: Mapped[dict] = mapped_column(
        postgresql.JSONB,
        default=dict,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)

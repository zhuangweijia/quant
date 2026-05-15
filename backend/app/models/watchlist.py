from sqlalchemy import String, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class UserWatchlist(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "market", name="uq_watchlist_user_symbol"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

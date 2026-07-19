"""add portfolio decision domain

Revision ID: c2d4e6f8a0b1
Revises: f4c9e8a7b6d5
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2d4e6f8a0b1"
down_revision: str | None = "f4c9e8a7b6d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "investment_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("investment_horizon_days", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("max_stock_weight", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("max_industry_weight", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("min_cash_ratio", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("max_daily_turnover", sa.Numeric(precision=8, scale=6), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "version", name="uq_investment_profile_user_version"),
    )
    op.create_index("ix_investment_profiles_user_id", "investment_profiles", ["user_id"])
    op.create_index(
        "ix_investment_profile_user_active", "investment_profiles", ["user_id", "is_active"]
    )

    op.create_table(
        "portfolios",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("cash", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_portfolio_user"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    op.create_table(
        "portfolio_positions",
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_position_portfolio_symbol"),
    )
    op.create_index("ix_portfolio_positions_portfolio_id", "portfolio_positions", ["portfolio_id"])
    op.create_index("ix_portfolio_positions_symbol", "portfolio_positions", ["symbol"])

    op.create_table(
        "portfolio_events",
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("cash_delta", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("reversal_of_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reversal_of_id"], ["portfolio_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_events_portfolio_id", "portfolio_events", ["portfolio_id"])
    op.create_index(
        "ix_portfolio_event_portfolio_time", "portfolio_events", ["portfolio_id", "occurred_at"]
    )

    op.create_table(
        "portfolio_snapshots",
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("cash", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("market_value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("total_asset", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=True),
        sa.Column("positions", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_snapshots_portfolio_id", "portfolio_snapshots", ["portfolio_id"])

    op.create_table(
        "daily_advices",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("source_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("data_date", sa.Date(), nullable=False),
        sa.Column("current_exposure", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("target_exposure", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("estimated_cash", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["investment_profiles.id"]),
        sa.ForeignKeyConstraint(["source_snapshot_id"], ["portfolio_snapshots.id"]),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["daily_advices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "signal_date", "version", name="uq_advice_user_signal_version"
        ),
    )
    op.create_index("ix_daily_advices_user_id", "daily_advices", ["user_id"])
    op.create_index("ix_daily_advices_signal_date", "daily_advices", ["signal_date"])
    op.create_index(
        "ix_daily_advice_user_signal_status", "daily_advices", ["user_id", "signal_date", "status"]
    )

    op.create_table(
        "advice_items",
        sa.Column("advice_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("industry", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("current_quantity", sa.Integer(), nullable=False),
        sa.Column("target_quantity", sa.Integer(), nullable=False),
        sa.Column("delta_quantity", sa.Integer(), nullable=False),
        sa.Column("current_weight", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("target_weight", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("reference_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("price_tolerance", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("score", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("positive_factors", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("invalidation_conditions", sa.JSON(), nullable=False),
        sa.Column("constraint_notes", sa.JSON(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["advice_id"], ["daily_advices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advice_id", "symbol", name="uq_advice_item_symbol"),
    )
    op.create_index("ix_advice_items_advice_id", "advice_items", ["advice_id"])
    op.create_index("ix_advice_item_advice_status", "advice_items", ["advice_id", "status"])

    op.create_table(
        "execution_records",
        sa.Column("advice_item_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("disposition", sa.String(length=24), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("fee", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("within_price_band", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["advice_item_id"], ["advice_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advice_item_id", name="uq_execution_item"),
    )
    op.create_index("ix_execution_records_advice_item_id", "execution_records", ["advice_item_id"])
    op.create_index("ix_execution_records_user_id", "execution_records", ["user_id"])

    op.create_table(
        "execution_mutations",
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("portfolio_event_ids", sa.JSON(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["execution_id"], ["execution_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_execution_mutation_key"),
    )
    op.create_index("ix_execution_mutations_execution_id", "execution_mutations", ["execution_id"])


def downgrade() -> None:
    op.drop_index("ix_execution_mutations_execution_id", table_name="execution_mutations")
    op.drop_table("execution_mutations")
    op.drop_index("ix_execution_records_user_id", table_name="execution_records")
    op.drop_index("ix_execution_records_advice_item_id", table_name="execution_records")
    op.drop_table("execution_records")
    op.drop_index("ix_advice_item_advice_status", table_name="advice_items")
    op.drop_index("ix_advice_items_advice_id", table_name="advice_items")
    op.drop_table("advice_items")
    op.drop_index("ix_daily_advice_user_signal_status", table_name="daily_advices")
    op.drop_index("ix_daily_advices_signal_date", table_name="daily_advices")
    op.drop_index("ix_daily_advices_user_id", table_name="daily_advices")
    op.drop_table("daily_advices")
    op.drop_index("ix_portfolio_snapshots_portfolio_id", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_index("ix_portfolio_event_portfolio_time", table_name="portfolio_events")
    op.drop_index("ix_portfolio_events_portfolio_id", table_name="portfolio_events")
    op.drop_table("portfolio_events")
    op.drop_index("ix_portfolio_positions_symbol", table_name="portfolio_positions")
    op.drop_index("ix_portfolio_positions_portfolio_id", table_name="portfolio_positions")
    op.drop_table("portfolio_positions")
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index("ix_investment_profile_user_active", table_name="investment_profiles")
    op.drop_index("ix_investment_profiles_user_id", table_name="investment_profiles")
    op.drop_table("investment_profiles")

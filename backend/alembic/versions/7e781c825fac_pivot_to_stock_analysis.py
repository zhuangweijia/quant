"""pivot to stock analysis platform

Revision ID: 7e781c825fac
Revises: 1718a313bd6e
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "7e781c825fac"
down_revision: Union[str, None] = "733c9ef0c923"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old trading domain tables (CASCADE to handle FK dependencies)
    op.execute("DROP TABLE IF EXISTS backtest_results CASCADE")
    op.execute("DROP TABLE IF EXISTS strategy_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS strategy_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS risk_events CASCADE")
    op.execute("DROP TABLE IF EXISTS risk_rules CASCADE")
    op.execute("DROP TABLE IF EXISTS alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS equity_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS positions CASCADE")
    op.execute("DROP TABLE IF EXISTS orders CASCADE")
    op.execute("DROP TABLE IF EXISTS strategies CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")

    # Create new analysis domain tables
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("industry", sa.String(64), nullable=True),
        sa.Column("list_date", sa.Date(), nullable=True),
        sa.Column("in_csi300", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_st", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("data_quality", sa.String(16), server_default="ok", nullable=False),
        sa.Column("last_synced_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_stocks_symbol"),
    )

    op.create_table(
        "daily_bars",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 4), nullable=False),
        sa.Column("high", sa.Numeric(20, 4), nullable=False),
        sa.Column("low", sa.Numeric(20, 4), nullable=False),
        sa.Column("close", sa.Numeric(20, 4), nullable=False),
        sa.Column("volume", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_daily_bars_symbol_date"),
    )
    op.create_index("ix_daily_bars_symbol_date", "daily_bars", ["symbol", "trade_date"])
    op.create_index("ix_daily_bars_date", "daily_bars", ["trade_date"])

    op.create_table(
        "stock_factors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("return_5d", sa.Numeric(12, 6), nullable=True),
        sa.Column("return_10d", sa.Numeric(12, 6), nullable=True),
        sa.Column("return_20d", sa.Numeric(12, 6), nullable=True),
        sa.Column("return_60d", sa.Numeric(12, 6), nullable=True),
        sa.Column("excess_return_20d", sa.Numeric(12, 6), nullable=True),
        sa.Column("momentum_12_1", sa.Numeric(12, 6), nullable=True),
        sa.Column("pe_ttm", sa.Numeric(12, 4), nullable=True),
        sa.Column("pb", sa.Numeric(12, 4), nullable=True),
        sa.Column("ps_ttm", sa.Numeric(12, 4), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(12, 6), nullable=True),
        sa.Column("pe_industry_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("pb_industry_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("roe_ttm", sa.Numeric(12, 4), nullable=True),
        sa.Column("gross_margin", sa.Numeric(12, 4), nullable=True),
        sa.Column("debt_ratio", sa.Numeric(12, 4), nullable=True),
        sa.Column("cashflow_to_profit", sa.Numeric(12, 4), nullable=True),
        sa.Column("revenue_yoy", sa.Numeric(12, 4), nullable=True),
        sa.Column("profit_yoy", sa.Numeric(12, 4), nullable=True),
        sa.Column("revenue_qoq", sa.Numeric(12, 4), nullable=True),
        sa.Column("turnover_5d_avg", sa.Numeric(12, 4), nullable=True),
        sa.Column("volatility_20d", sa.Numeric(12, 6), nullable=True),
        sa.Column("vol_price_corr_20d", sa.Numeric(12, 6), nullable=True),
        sa.Column("volume_ratio", sa.Numeric(12, 4), nullable=True),
        sa.Column("rsi_14", sa.Numeric(12, 4), nullable=True),
        sa.Column("macd_hist", sa.Numeric(12, 6), nullable=True),
        sa.Column("boll_position", sa.Numeric(6, 4), nullable=True),
        sa.Column("ma_alignment", sa.Numeric(2, 0), nullable=True),
        sa.Column("northbound_holding_pct", sa.Numeric(12, 6), nullable=True),
        sa.Column("northbound_holding_change", sa.Numeric(12, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_stock_factors_symbol_date"),
    )
    op.create_index("ix_stock_factors_date", "stock_factors", ["trade_date"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Numeric(8, 6), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(16), nullable=True),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("confidence", sa.String(16), server_default="normal", nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rank_change", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "trade_date", "model_version", name="uq_predictions_sym_date_ver"),
    )
    op.create_index("ix_predictions_date", "predictions", ["trade_date"])
    op.create_index("ix_predictions_date_rank", "predictions", ["trade_date", "rank"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_start", sa.Date(), nullable=False),
        sa.Column("data_end", sa.Date(), nullable=False),
        sa.Column("ic", sa.Numeric(8, 6), nullable=True),
        sa.Column("val_accuracy", sa.Numeric(6, 4), nullable=True),
        sa.Column("top_features", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("file_path", sa.String(256), nullable=False),
        sa.Column("n_estimators", sa.Integer(), server_default="200", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("trigger_type", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(16), server_default="running", nullable=False),
        sa.Column("error", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )

    # Recreate alerts table for analysis notifications
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("rule_name", sa.String(128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("analysis_runs")
    op.drop_table("model_versions")
    op.drop_table("predictions")
    op.drop_index("ix_stock_factors_date", table_name="stock_factors")
    op.drop_table("stock_factors")
    op.drop_index("ix_daily_bars_date", table_name="daily_bars")
    op.drop_index("ix_daily_bars_symbol_date", table_name="daily_bars")
    op.drop_table("daily_bars")
    op.drop_table("stocks")

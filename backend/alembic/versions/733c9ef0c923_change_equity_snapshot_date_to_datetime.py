"""change_equity_snapshot_date_to_datetime

Revision ID: 733c9ef0c923
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 23:43:40.383131
"""

import sqlalchemy as sa

from alembic import op

revision = "733c9ef0c923"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_equity_snapshot_user_date", "equity_snapshots", type_="unique")
    op.add_column(
        "equity_snapshots", sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE equity_snapshots SET timestamp = (date || ' 15:30:00+00')::timestamptz")
    op.alter_column("equity_snapshots", "timestamp", nullable=False)
    op.drop_column("equity_snapshots", "date")
    op.create_unique_constraint(
        "uq_equity_snapshot_user_timestamp", "equity_snapshots", ["user_id", "timestamp"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_equity_snapshot_user_timestamp", "equity_snapshots", type_="unique")
    op.add_column("equity_snapshots", sa.Column("date", sa.String(10), nullable=True))
    op.execute(
        "UPDATE equity_snapshots SET date = to_char(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD')"
    )
    op.alter_column("equity_snapshots", "date", nullable=False)
    op.drop_column("equity_snapshots", "timestamp")
    op.create_unique_constraint(
        "uq_equity_snapshot_user_date", "equity_snapshots", ["user_id", "date"]
    )

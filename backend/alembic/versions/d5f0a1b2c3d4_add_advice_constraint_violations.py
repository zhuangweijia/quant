"""add advice constraint violations

Revision ID: d5f0a1b2c3d4
Revises: c2d4e6f8a0b1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5f0a1b2c3d4"
down_revision: str | None = "c2d4e6f8a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "daily_advices",
        sa.Column(
            "constraint_violations",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("daily_advices", "constraint_violations")

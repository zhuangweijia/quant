"""add global settings unique index

Revision ID: f4c9e8a7b6d5
Revises: b8f31a2c4d90
Create Date: 2026-07-18 16:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4c9e8a7b6d5"
down_revision: str | None = "b8f31a2c4d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY category, key
                           ORDER BY updated_at DESC, created_at DESC, id DESC
                       ) AS row_number
                FROM settings
                WHERE user_id IS NULL
            )
            DELETE FROM settings
            WHERE id IN (SELECT id FROM ranked WHERE row_number > 1)
            """
        )
    )
    op.create_index(
        "uq_settings_global_cat_key",
        "settings",
        ["category", "key"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
        sqlite_where=sa.text("user_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_settings_global_cat_key", table_name="settings")

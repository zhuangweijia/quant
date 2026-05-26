"""add_missing_tables

Revision ID: 847925f8963b
Revises: cdc47b1fabfd
Create Date: 2026-05-27 00:34:59.188306
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision = '847925f8963b'
down_revision = 'cdc47b1fabfd'
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table('accounts',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('mode', sa.String(length=8), nullable=False),
    sa.Column('cash', sa.Numeric(precision=20, scale=8), nullable=False),
    sa.Column('initial_capital', sa.Numeric(precision=20, scale=8), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('equity_snapshots',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('date', sa.String(length=10), nullable=False),
    sa.Column('total_equity', sa.Numeric(precision=20, scale=4), nullable=False),
    sa.Column('cash', sa.Numeric(precision=20, scale=4), nullable=False),
    sa.Column('position_value', sa.Numeric(precision=20, scale=4), nullable=False),
    sa.Column('daily_pnl', sa.Numeric(precision=20, scale=4), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'date', name='uq_equity_snapshot_user_date')
    )
    op.create_index(op.f('ix_equity_snapshots_user_id'), 'equity_snapshots', ['user_id'], unique=False)
    op.create_table('notification_logs',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel', sa.String(length=16), nullable=False),
    sa.Column('event_type', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=128), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notification_logs_user_created', 'notification_logs', ['user_id', 'created_at'], unique=False)
    op.create_table('settings',
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('encrypted', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'category', 'key', name='uq_settings_user_cat_key')
    )
    op.create_index(op.f('ix_settings_user_id'), 'settings', ['user_id'], unique=False)
    op.create_table('user_watchlist',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('symbol', sa.String(length=32), nullable=False),
    sa.Column('market', sa.String(length=16), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'symbol', 'market', name='uq_watchlist_user_symbol')
    )
    op.create_index(op.f('ix_user_watchlist_user_id'), 'user_watchlist', ['user_id'], unique=False)
    op.create_table('strategy_logs',
    sa.Column('strategy_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('level', sa.String(length=8), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategy_logs_strategy_created', 'strategy_logs', ['strategy_id', 'created_at'], unique=False)
    op.create_table('risk_events',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('strategy_id', sa.Uuid(), nullable=True),
    sa.Column('rule_id', sa.Uuid(), nullable=True),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('rule_type', sa.String(length=32), nullable=False),
    sa.Column('result', sa.String(length=16), nullable=False),
    sa.Column('detail', sa.JSON(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['rule_id'], ['risk_rules.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_events_user_created', 'risk_events', ['user_id', 'created_at'], unique=False)
def downgrade() -> None:
    op.drop_index('ix_risk_events_user_created', table_name='risk_events')
    op.drop_table('risk_events')
    op.drop_index('ix_strategy_logs_strategy_created', table_name='strategy_logs')
    op.drop_table('strategy_logs')
    op.drop_index(op.f('ix_user_watchlist_user_id'), table_name='user_watchlist')
    op.drop_table('user_watchlist')
    op.drop_index(op.f('ix_settings_user_id'), table_name='settings')
    op.drop_table('settings')
    op.drop_index('ix_notification_logs_user_created', table_name='notification_logs')
    op.drop_table('notification_logs')
    op.drop_index(op.f('ix_equity_snapshots_user_id'), table_name='equity_snapshots')
    op.drop_table('equity_snapshots')
    op.drop_table('accounts')
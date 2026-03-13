"""add webhook events tables

Revision ID: webhook_events_monitoring
Revises: oauth2_auth
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'webhook_events_monitoring'
down_revision = 'oauth2_auth'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create webhook_events and webhook_stats tables."""
    
    # Таблица webhook_events
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('order_id', sa.String(length=255), nullable=False),
        sa.Column('gateway', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum(
            'pending', 'processing', 'success', 'retry', 'failed',
            name='webhookeventstatus'
        ), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=5),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    
    # Индексы для webhook_events
    op.create_index('ix_webhook_gateway', 'webhook_events', ['gateway', 'created_at'])
    op.create_index('ix_webhook_status', 'webhook_events', ['status'])
    op.create_index('ix_webhook_order', 'webhook_events', ['order_id'])
    op.create_index('ix_webhook_event_id', 'webhook_events', ['event_id'], unique=True)
    
    # Таблица webhook_stats
    op.create_table(
        'webhook_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gateway', sa.String(length=100), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('total_received', sa.Integer(), nullable=False, default=0),
        sa.Column('total_processed', sa.Integer(), nullable=False, default=0),
        sa.Column('total_failed', sa.Integer(), nullable=False, default=0),
        sa.Column('total_retries', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Уникальный индекс для webhook_stats
    op.create_index('ix_stats_gateway_date', 'webhook_stats', ['gateway', 'date'], unique=True)


def downgrade() -> None:
    """Drop webhook_events and webhook_stats tables."""
    op.drop_index('ix_stats_gateway_date', table_name='webhook_stats')
    op.drop_table('webhook_stats')
    
    op.drop_index('ix_webhook_event_id', table_name='webhook_events')
    op.drop_index('ix_webhook_order', table_name='webhook_events')
    op.drop_index('ix_webhook_status', table_name='webhook_events')
    op.drop_index('ix_webhook_gateway', table_name='webhook_events')
    op.drop_table('webhook_events')
    
    op.execute('DROP TYPE IF EXISTS webhookeventstatus')

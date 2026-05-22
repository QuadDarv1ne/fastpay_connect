"""add subscriptions table

Revision ID: add_subscriptions
Revises: add_audit_logs
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_subscriptions"
down_revision = "add_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create subscriptions table."""
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("plan_id", sa.String(), nullable=False, index=True),
        sa.Column("plan_name", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(), server_default="RUB"),
        sa.Column("interval", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="active", index=True),
        sa.Column("payment_gateway", sa.String(), nullable=False),
        sa.Column("gateway_subscription_id", sa.String(), nullable=True),
        sa.Column("trial_end", sa.DateTime(), nullable=True),
        sa.Column("current_period_start", sa.DateTime(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column("next_billing_date", sa.DateTime(), nullable=False, index=True),
        sa.Column("cancel_at_period_end", sa.String(), server_default=""),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Drop subscriptions table."""
    op.drop_table("subscriptions")

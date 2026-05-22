"""add_split_payments

Revision ID: add_split_payments
Revises: add_subscriptions
Create Date: 2026-05-22

Add split_payments table for marketplace support.
"""

from alembic import op
import sqlalchemy as sa

revision = "add_split_payments"
down_revision = "add_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "split_payments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("parent_payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False, index=True),
        sa.Column("order_id", sa.String(), nullable=False, index=True),
        sa.Column("recipient_id", sa.String(), nullable=False, index=True),
        sa.Column("recipient_name", sa.String(), nullable=True),
        sa.Column("recipient_type", sa.String(), nullable=True, server_default="vendor"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(), server_default="RUB"),
        sa.Column("commission_percent", sa.Numeric(5, 2), server_default="0"),
        sa.Column("commission_amount", sa.Numeric(10, 2), server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "failed", "refunded", "cancelled", name="splitstatus"),
            server_default="pending",
            index=True,
        ),
        sa.Column("gateway_payment_id", sa.String(), nullable=True),
        sa.Column("gateway", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_split_parent_payment", "split_payments", ["parent_payment_id"])
    op.create_index("ix_split_recipient", "split_payments", ["recipient_id"])
    op.create_index("ix_split_status", "split_payments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_split_status", table_name="split_payments")
    op.drop_index("ix_split_recipient", table_name="split_payments")
    op.drop_index("ix_split_parent_payment", table_name="split_payments")
    op.drop_table("split_payments")

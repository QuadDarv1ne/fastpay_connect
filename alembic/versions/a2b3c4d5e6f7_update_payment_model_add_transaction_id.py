"""update payment model add transaction_id webhook_processed and indexes

Revision ID: a2b3c4d5e6f7
Revises: e177d6c0b9cc
Create Date: 2024-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'e177d6c0b9cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('payments', sa.Column('transaction_id', sa.String(), nullable=True))
    op.add_column('payments', sa.Column('webhook_processed', sa.String(), nullable=True, server_default=''))

    op.create_index('ix_transaction_id', 'payments', ['transaction_id'], unique=False)
    op.create_index('ix_order_id', 'payments', ['order_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_order_id', table_name='payments')
    op.drop_index('ix_transaction_id', table_name='payments')

    op.drop_column('payments', 'webhook_processed')
    op.drop_column('payments', 'transaction_id')

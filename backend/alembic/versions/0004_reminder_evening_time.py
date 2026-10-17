"""reminder evening time

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # У существующих напоминаний всё как было: основное включено, «если не отмечено» — в 21:00.
    op.add_column('reminders', sa.Column('morning', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('reminders', sa.Column('evening_time', sa.Time(), server_default=sa.text("'21:00'"), nullable=False))


def downgrade() -> None:
    op.drop_column('reminders', 'evening_time')
    op.drop_column('reminders', 'morning')

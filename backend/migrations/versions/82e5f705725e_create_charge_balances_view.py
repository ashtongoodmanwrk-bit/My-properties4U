"""create charge balances view

Revision ID: 82e5f705725e
Revises: b88606c714bc
Create Date: 2026-10-05 00:56:47.889070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82e5f705725e'
down_revision: Union[str, Sequence[str], None] = 'b88606c714bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE VIEW v_charge_balances AS
        SELECT rc.id AS charge_id,
               rc.lease_id,
               rc.due_date,
               rc.amount,
               rc.status,
               COALESCE(SUM(p.amount), 0) AS paid,
               rc.amount - COALESCE(SUM(p.amount), 0) AS outstanding
        FROM rent_charges rc
        LEFT JOIN payments p ON p.rent_charge_id = rc.id
        GROUP BY rc.id
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP VIEW v_charge_balances")


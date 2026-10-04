"""prevent overlapping leases

Revision ID: eee39b432e07
Revises: de74759a0bd9
Create Date: 2026-10-04 20:44:08.862479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eee39b432e07'
down_revision: Union[str, Sequence[str], None] = 'de74759a0bd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE leases ADD CONSTRAINT ex_leases_no_overlap
        EXCLUDE USING gist (
            unit_id WITH =,
            daterange(start_date, end_date, '[]') WITH &&
        ) WHERE (status = 'active')
        """
    )
def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE leases DROP CONSTRAINT ex_leases_no_overlap")

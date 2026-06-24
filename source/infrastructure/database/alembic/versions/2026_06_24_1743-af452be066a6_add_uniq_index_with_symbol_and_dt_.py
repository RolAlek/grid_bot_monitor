"""add uniq index with symbol and dt column  on snapshot table

Revision ID: af452be066a6
Revises: 1e86a420479c
Create Date: 2026-06-24 17:43:14.793619

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "af452be066a6"
down_revision: Union[str, Sequence[str], None] = "1e86a420479c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_oi_snapshot_symbol_date",
        "oi_snapshots",
        [sa.text("symbol"), sa.text("date(created_at)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_oi_snapshot_symbol_date", table_name="oi_snapshots")

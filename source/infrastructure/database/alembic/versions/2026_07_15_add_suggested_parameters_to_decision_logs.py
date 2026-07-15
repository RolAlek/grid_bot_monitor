"""Add suggested_parameters_json column to decision_logs.

Stores the ProposedGridParams (grid range, levels, leverage, etc.) as a
JSONB column so that the launch digest and keyboard can display the
proposed parameters even after the verdict has been persisted.

Revision ID: add_suggested_params
Revises: change_pk_fk_to_native_uuid
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "add_suggested_params"
down_revision: str | None = "change_pk_fk_to_native_uuid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "decision_logs",
        sa.Column("suggested_parameters_json", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("decision_logs", "suggested_parameters_json")

"""Change PK and FK columns from String(36) to native PostgreSQL UUID.

PostgreSQL native UUID is more efficient than VARCHAR(36) and provides
proper type checking.  All oid PKs and FK references are migrated in a
single transaction.

Revision ID: change_pk_fk_to_native_uuid
Revises: ee11aadbec68
Create Date: 2026-07-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "change_pk_fk_to_native_uuid"
down_revision: str | None = "ee11aadbec68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE grid_launches DROP CONSTRAINT IF EXISTS grid_launches_decision_verdict_oid_fkey")
    op.execute("ALTER TABLE health_snapshots DROP CONSTRAINT IF EXISTS health_snapshots_grid_launch_oid_fkey")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_health_snapshot_oid_fkey")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_grid_launch_oid_fkey")

    for table in ("decision_logs", "oi_snapshots", "grid_launches", "health_snapshots", "alerts"):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN oid TYPE UUID USING oid::UUID")

    op.execute("ALTER TABLE grid_launches ALTER COLUMN decision_verdict_oid TYPE UUID USING decision_verdict_oid::UUID")
    op.execute("ALTER TABLE health_snapshots ALTER COLUMN grid_launch_oid TYPE UUID USING grid_launch_oid::UUID")
    op.execute("ALTER TABLE alerts ALTER COLUMN health_snapshot_oid TYPE UUID USING health_snapshot_oid::UUID")
    op.execute("ALTER TABLE alerts ALTER COLUMN grid_launch_oid TYPE UUID USING grid_launch_oid::UUID")

    op.create_foreign_key(
        "grid_launches_decision_verdict_oid_fkey",
        "grid_launches",
        "decision_logs",
        ["decision_verdict_oid"],
        ["oid"],
    )
    op.create_foreign_key(
        "health_snapshots_grid_launch_oid_fkey",
        "health_snapshots",
        "grid_launches",
        ["grid_launch_oid"],
        ["oid"],
    )
    op.create_foreign_key(
        "alerts_health_snapshot_oid_fkey",
        "alerts",
        "health_snapshots",
        ["health_snapshot_oid"],
        ["oid"],
    )
    op.create_foreign_key(
        "alerts_grid_launch_oid_fkey",
        "alerts",
        "grid_launches",
        ["grid_launch_oid"],
        ["oid"],
    )


def downgrade() -> None:
    op.execute("ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_grid_launch_oid_fkey")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_health_snapshot_oid_fkey")
    op.execute("ALTER TABLE health_snapshots DROP CONSTRAINT IF EXISTS health_snapshots_grid_launch_oid_fkey")
    op.execute("ALTER TABLE grid_launches DROP CONSTRAINT IF EXISTS grid_launches_decision_verdict_oid_fkey")

    for table in ("alerts", "health_snapshots", "grid_launches", "oi_snapshots", "decision_logs"):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN oid TYPE VARCHAR(36)")

    op.execute("ALTER TABLE alerts ALTER COLUMN grid_launch_oid TYPE VARCHAR(36)")
    op.execute("ALTER TABLE alerts ALTER COLUMN health_snapshot_oid TYPE VARCHAR(36)")
    op.execute("ALTER TABLE health_snapshots ALTER COLUMN grid_launch_oid TYPE VARCHAR(36)")
    op.execute("ALTER TABLE grid_launches ALTER COLUMN decision_verdict_oid TYPE VARCHAR(36)")

    op.create_foreign_key(
        "alerts_grid_launch_oid_fkey",
        "alerts",
        "grid_launches",
        ["grid_launch_oid"],
        ["oid"],
    )
    op.create_foreign_key(
        "alerts_health_snapshot_oid_fkey",
        "alerts",
        "health_snapshots",
        ["health_snapshot_oid"],
        ["oid"],
    )
    op.create_foreign_key(
        "health_snapshots_grid_launch_oid_fkey",
        "health_snapshots",
        "grid_launches",
        ["grid_launch_oid"],
        ["oid"],
    )
    op.create_foreign_key(
        "grid_launches_decision_verdict_oid_fkey",
        "grid_launches",
        "decision_logs",
        ["decision_verdict_oid"],
        ["oid"],
    )

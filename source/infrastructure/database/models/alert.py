import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.domain.value_objects import AlertType
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import SymbolType


if TYPE_CHECKING:
    from source.infrastructure.database.models.grid_launch import GridLaunchModel
    from source.infrastructure.database.models.health_snapshot import HealthSnapshotModel


class AlertModel(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alert_bot_time", "grid_launch_oid", "created_at"),
        Index("idx_alert_symbol_severity", "symbol", "severity"),
        CheckConstraint(
            f"alert_type IN ({', '.join(f"'{type_.value}'" for type_ in AlertType)})",
            name="chk_alert_type",
        ),
    )

    symbol: Mapped[SymbolType]
    alert_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str]
    acknowledged: Mapped[bool] = mapped_column(default=False)
    acknowledged_by: Mapped[str | None]
    acknowledged_at: Mapped[datetime | None]

    # Relationships
    health_snapshot_oid: Mapped[uuid.UUID | None] = mapped_column(
        UUID,
        ForeignKey("health_snapshots.oid"),
        index=True,
    )
    health_snapshot: Mapped["HealthSnapshotModel | None"] = relationship(back_populates="alerts")

    grid_launch_oid: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("grid_launches.oid"), index=True)
    grid_launch: Mapped["GridLaunchModel"] = relationship(back_populates="alerts")

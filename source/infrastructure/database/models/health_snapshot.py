from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.domain.value_objects import HealthStatus
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import SymbolType


if TYPE_CHECKING:
    from source.infrastructure.database.models.alert import AlertModel
    from source.infrastructure.database.models.grid_launch import GridLaunchModel


class HealthSnapshotModel(Base):
    __tablename__ = "health_snapshots"
    __table_args__ = (
        Index("idx_health_snapshot_bot_time", "grid_launch_oid", "created_at"),
        CheckConstraint(
            f"health_status IN ({', '.join(f"'{status.value}'" for status in HealthStatus)})",
            name="chk_health_status",
        ),
    )

    symbol: Mapped[SymbolType]

    adx14: Mapped[float]
    atr14: Mapped[float]
    atr_pct_of_price: Mapped[float]
    rsi14: Mapped[float]
    realized_vol_1d: Mapped[float]
    realized_vol_7d: Mapped[float]
    last_price: Mapped[float]

    unrealized_pnl: Mapped[float]
    unrealized_pnl_pct: Mapped[float]
    grid_fill_ratio: Mapped[float]
    matched_orders: Mapped[int] = mapped_column(default=0)
    total_orders: Mapped[int] = mapped_column(default=0)

    distance_to_liquidation_pct: Mapped[float]
    liquidation_price: Mapped[float | None]
    leverage: Mapped[int]

    funding_rate: Mapped[float] = mapped_column(default=0.0)
    funding_rate_annualized_pct: Mapped[float] = mapped_column(default=0.0)

    health_status: Mapped[str] = mapped_column(String(16))
    health_score: Mapped[float] = mapped_column(default=1.0)

    # Relationships
    grid_launch_oid: Mapped[str] = mapped_column(String(36), ForeignKey("grid_launches.oid"), index=True)
    grid_launch: Mapped["GridLaunchModel"] = relationship(back_populates="health_snapshots")
    alerts: Mapped[list["AlertModel"]] = relationship(back_populates="health_snapshot")

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.domain.value_objects import GridLaunchStatus, GridType, HealthStatus, Trend
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.decision_log import DecisionLog
from source.infrastructure.database.models.types import CreatedAt, SymbolType, UpdatedAt


if TYPE_CHECKING:
    from source.infrastructure.database.models.alert import AlertModel


class GridLaunchModel(Base):
    __tablename__ = "grid_launches"
    __table_args__ = (
        CheckConstraint("grid_top > grid_bottom", name="ck_grid_launches_top_gt_bottom"),
        CheckConstraint("grid_leverage >= 1", name="ck_grid_launches_leverage_positive"),
        CheckConstraint("grid_levels >= 2 AND grid_levels <= 500", name="ck_grid_launches_levels_platform_range"),
        CheckConstraint(
            f"grid_regime IN ({', '.join(f"'{trend.value}'" for trend in Trend)})",
            name="chk_regime",
        ),
        CheckConstraint(
            f"grid_type IN ({', '.join(f"'{type_.value}'" for type_ in GridType)})",
            name="chk_type",
        ),
        CheckConstraint(
            f"status IN ({', '.join(f"'{status.value}'" for status in GridLaunchStatus)})",
            name="chk_status",
        ),
        CheckConstraint(
            "(closed_at IS NULL AND status IN ('running', 'paused')) "
            "OR (closed_at IS NOT NULL AND status IN ('closed', 'liquidated'))",
            name="ck_grid_launches_status_closed_at_consistency",
        ),
        CheckConstraint(
            f"health_status IN ({', '.join(f"'{s.value}'" for s in HealthStatus)})",
            name="chk_grid_launches_health_status",
        ),
        Index(
            "ux_grid_launches_open_per_symbol",
            "symbol",
            unique=True,
            postgresql_where=text("status IN ('running', 'paused')"),
        ),
    )

    symbol: Mapped[SymbolType]
    grid_top: Mapped[float]
    grid_bottom: Mapped[float]
    grid_levels: Mapped[int]
    grid_regime: Mapped[str] = mapped_column(String(16))
    grid_type: Mapped[str] = mapped_column(String(16))
    grid_leverage: Mapped[int]
    quote_investment: Mapped[float]
    stop_loss: Mapped[float | None]
    take_profit: Mapped[float | None]

    # Outcome tracking
    updated_at: Mapped[UpdatedAt]
    closed_at: Mapped[CreatedAt | None]
    realized_pnl: Mapped[float | None]
    status: Mapped[str] = mapped_column(String(16))
    external_id: Mapped[str | None]

    # Monitoring fields (merged from ActiveBotModel)
    health_status: Mapped[str] = mapped_column(String(16), default=HealthStatus.GREEN.value)
    distance_to_liquidation_pct: Mapped[float | None]
    grid_fill_ratio: Mapped[float | None]
    last_price: Mapped[float | None]
    last_health_check_at: Mapped[datetime | None]
    auto_adjust_enabled: Mapped[bool] = mapped_column(default=False)
    paused_by_monitor: Mapped[bool] = mapped_column(default=False)

    decision_verdict_oid: Mapped[str] = mapped_column(String(36), ForeignKey("decision_logs.oid"), index=True)
    decision_verdict: Mapped[DecisionLog] = relationship(back_populates="launched_grid", lazy="joined")

    # Monitoring relationships
    alerts: Mapped[list["AlertModel"]] = relationship(back_populates="grid_launch")

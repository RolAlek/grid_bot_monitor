from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.domain.value_objects import GridLaunchStatus, GridType, Trend, VerdictAction
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import CreatedAt, JSONType, SymbolType, UpdatedAt


class OISnapshot(Base):
    __tablename__ = "oi_snapshots"
    __table_args__ = (
        Index("idx_oi_snapshot_symbol_created_at", "symbol", "created_at"),
        Index("uq_oi_snapshot_symbol_date", "symbol", func.date(text("created_at")), unique=True),
    )

    symbol: Mapped[SymbolType]
    funding_rate_last: Mapped[float]
    funding_rate_annualized_pct: Mapped[float]
    open_interest: Mapped[float]
    oi_pct_change_7d: Mapped[float | None]


class DecisionLog(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({', '.join(f"'{action.value}'" for action in VerdictAction)})",
            name="chk_action",
        ),
    )

    symbol: Mapped[SymbolType]
    action: Mapped[str] = mapped_column(String(32))
    gates_json: Mapped[tuple[dict[str, Any]]] = mapped_column(JSONType)
    notes: Mapped[str | None]

    launched_grid: Mapped["GridLaunchModel | None"] = relationship(back_populates="decision_verdict", lazy="joined")


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
        Index(
            "ux_grid_launches_open_per_symbol",
            "symbol",
            unique=True,
            sqlite_where=text("status IN ('running', 'paused')"),
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

    # Outcome tracking — nullable, populated later, never guessed at write time.
    updated_at: Mapped[UpdatedAt]
    closed_at: Mapped[CreatedAt | None]
    realized_pnl: Mapped[float | None]
    status: Mapped[str] = mapped_column(String(16))
    external_id: Mapped[str | None]

    decision_verdict_oid: Mapped[str] = mapped_column(String(36), ForeignKey("decision_logs.oid"), index=True)
    decision_verdict: Mapped[DecisionLog] = relationship(back_populates="launched_grid", lazy="joined")

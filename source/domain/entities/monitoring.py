from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from source.domain.value_objects import AlertType, GridLaunchStatus, GridType, HealthStatus, Symbol, Trend


@dataclass
class Bot:
    # ── Identity ──
    symbol: Symbol
    oid: UUID | None = None
    external_id: str | None = None
    status: GridLaunchStatus = GridLaunchStatus.RUNNING

    # ── Grid configuration (set at launch, immutable thereafter) ──
    top: float | None = None
    bottom: float | None = None
    levels: int | None = None
    trend: Trend | None = None
    grid_type: GridType | None = None
    leverage: int = 1
    investment: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None

    # ── Lifecycle ──
    decision_verdict_oid: UUID | None = None
    created_at: datetime | None = None
    closed_at: datetime | None = None
    updated_at: datetime | None = None

    # ── Financials ──
    realized_pnl: float | None = None
    current_pnl: float | None = None  # set by health-check, NOT from DB
    current_pnl_pct: float | None = None

    # ── Runtime monitoring ──
    health_status: HealthStatus = HealthStatus.GREEN
    distance_to_liquidation_pct: float | None = None
    grid_fill_ratio: float | None = None
    last_price: float | None = None
    last_health_check_at: datetime | None = None
    auto_adjust_enabled: bool = False
    paused_by_monitor: bool = False


@dataclass(frozen=True)
class HealthMetricsInput:
    symbol: Symbol
    last_price: float
    leverage: int

    adx14: float
    atr14: float
    atr_pct_of_price: float
    rsi14: float
    realized_vol_1d: float
    realized_vol_7d: float

    unrealized_pnl: float
    grid_fill_ratio: float

    distance_to_liquidation_pct: float
    unrealized_pnl_pct: float | None = None
    liquidation_price: float | None = None

    funding_rate_annualized_pct: float = 0.0


@dataclass(frozen=True, kw_only=True)
class HealthSnapshot(HealthMetricsInput):
    grid_launch_oid: UUID
    created_at: datetime

    matched_orders: int = 0
    total_orders: int = 0

    funding_rate: float = 0.0

    health_status: HealthStatus = HealthStatus.GREEN
    health_score: float = 1.0
    triggered_alerts: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class Alert:
    grid_launch_oid: UUID
    symbol: Symbol
    alert_type: AlertType
    severity: HealthStatus
    message: str
    health_snapshot_oid: UUID | None = None
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    oid: UUID | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ClassificationResult:
    status: HealthStatus
    score: float
    alerts: tuple[AlertType, ...]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BotOrderSnapshot:
    trend: Trend
    profit_reduce: float = 0.0
    funding_fee_payment: float = 0.0
    quote_investment: float | None = None
    position: float | None = None
    row: int = 0
    per_volume: float | None = None
    leverage: int = 1
    estimate_liquidation_price_up: float | None = None
    estimate_liquidation_price_down: float | None = None

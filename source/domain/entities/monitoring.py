from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from source.domain.value_objects import AlertType, HealthStatus, Symbol


@dataclass
class ActiveBot:
    symbol: Symbol
    oid: str | None = None
    external_bot_id: str | None = None
    status: str = ""
    health_status: HealthStatus = HealthStatus.GREEN
    current_pnl: float | None = None
    current_pnl_pct: float | None = None
    distance_to_liquidation_pct: float | None = None
    grid_fill_ratio: float | None = None
    last_price: float | None = None
    last_health_check_at: datetime | None = None
    auto_adjust_enabled: bool = False
    paused_by_monitor: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


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
    unrealized_pnl_pct: float
    grid_fill_ratio: float

    distance_to_liquidation_pct: float
    liquidation_price: float | None = None

    funding_rate_annualized_pct: float = 0.0


@dataclass(frozen=True, kw_only=True)
class HealthSnapshot(HealthMetricsInput):
    grid_launch_oid: str
    created_at: datetime

    matched_orders: int = 0
    total_orders: int = 0

    funding_rate: float = 0.0

    health_status: HealthStatus = HealthStatus.GREEN
    health_score: float = 1.0
    triggered_alerts: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class Alert:
    grid_launch_oid: str
    symbol: Symbol
    alert_type: AlertType
    severity: HealthStatus
    message: str
    health_snapshot_oid: str | None = None
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    oid: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ClassificationResult:
    status: HealthStatus
    score: float
    alerts: tuple[AlertType, ...]
    details: dict[str, Any] = field(default_factory=dict)

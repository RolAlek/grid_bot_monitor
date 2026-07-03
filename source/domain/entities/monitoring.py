from dataclasses import dataclass, field
from datetime import datetime

from source.domain.value_objects import AlertType, HealthStatus, Symbol


@dataclass
class ActiveBot:
    grid_launch_oid: str
    symbol: Symbol
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
    oid: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class HealthSnapshot:
    active_bot_oid: str
    symbol: Symbol
    created_at: datetime

    adx14: float
    atr14: float
    atr_pct_of_price: float
    rsi14: float
    realized_vol_1d: float
    realized_vol_7d: float
    last_price: float

    unrealized_pnl: float
    unrealized_pnl_pct: float
    grid_fill_ratio: float
    matched_orders: int = 0
    total_orders: int = 0

    distance_to_liquidation_pct: float = 0.0
    liquidation_price: float | None = None
    leverage: int = 1

    funding_rate: float = 0.0
    funding_rate_annualized_pct: float = 0.0

    health_status: HealthStatus = HealthStatus.GREEN
    health_score: float = 1.0
    triggered_alerts: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class Alert:
    active_bot_oid: str
    symbol: Symbol
    alert_type: AlertType
    severity: HealthStatus
    message: str
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    oid: str | None = None
    created_at: datetime | None = None

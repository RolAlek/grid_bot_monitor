from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID

from source.domain.entities.indicators import IndicatorSet
from source.domain.exceptions import BotIntegrityError
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

    @classmethod
    def build_from(
        cls,
        symbol: Symbol,
        indicators: IndicatorSet,
        leverage: int,
        unrealized_pnl: float,
        fil_ratio: float,
        distance_to_liq_pct: float,
        funding_annualized: float,
        unrealized_pnl_pct: float | None,
        liq_price: float | None,
    ) -> Self:
        return cls(
            symbol=symbol,
            last_price=indicators.last_price,
            leverage=leverage,
            adx14=indicators.adx14,
            atr14=indicators.atr14,
            atr_pct_of_price=indicators.atr_pct_of_price,
            rsi14=indicators.rsi14,
            realized_vol_1d=indicators.realized_vol_1d,
            realized_vol_7d=indicators.realized_vol_7d,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            grid_fill_ratio=fil_ratio,
            distance_to_liquidation_pct=distance_to_liq_pct,
            liquidation_price=liq_price,
            funding_rate_annualized_pct=funding_annualized,
        )


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

    @classmethod
    def build_from(  # type: ignore[override]
        cls,
        bot: Bot,
        indicators: IndicatorSet,
        metrics: HealthMetricsInput,
        funding_rate: float,
        classified: "ClassificationResult",
    ) -> "HealthSnapshot":
        if bot.oid is None:
            raise BotIntegrityError("Bot must have oid to create HealthSnapshot")

        return cls(
            grid_launch_oid=bot.oid,
            symbol=bot.symbol,
            created_at=datetime.now(UTC),
            adx14=indicators.adx14,
            atr14=indicators.atr14,
            atr_pct_of_price=indicators.atr_pct_of_price,
            rsi14=indicators.rsi14,
            realized_vol_1d=indicators.realized_vol_1d,
            realized_vol_7d=indicators.realized_vol_7d,
            last_price=indicators.last_price,
            unrealized_pnl=metrics.unrealized_pnl,
            unrealized_pnl_pct=metrics.unrealized_pnl_pct,
            grid_fill_ratio=metrics.grid_fill_ratio,
            distance_to_liquidation_pct=metrics.distance_to_liquidation_pct,
            liquidation_price=metrics.liquidation_price,
            leverage=metrics.leverage,
            funding_rate_annualized_pct=metrics.funding_rate_annualized_pct,
            funding_rate=funding_rate,
            health_status=classified.status,
            health_score=classified.score,
            triggered_alerts=classified.alerts,
        )


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

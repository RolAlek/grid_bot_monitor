from dataclasses import dataclass
from datetime import datetime

from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.exceptions import InvalidGridParamsError
from source.domain.value_objects import GateResult, GridLaunchStatus, GridType, Symbol, Trend, VerdictAction


@dataclass(frozen=True)
class ProposedGridParams:
    symbol: Symbol
    top: float
    bottom: float
    grid_levels: int
    leverage: int
    quote_investment: float
    trend: Trend
    grid_type: GridType

    stop_loss: float | None = None
    take_profit: float | None = None

    def __post_init__(self) -> None:
        if self.trend in {Trend.LONG, Trend.SHORT} and self.stop_loss is None and self.take_profit is None:
            raise InvalidGridParamsError(f"Stop-loss and take-profit must be set for {self.trend.value} grid")

    @property
    def grid_range(self) -> float:
        return self.top - self.bottom


@dataclass(frozen=True)
class LiquidationEstimate:
    proposal: ProposedGridParams

    estimate_liquidation_price_up: float | None
    estimate_liquidation_price_down: float | None

    @property
    def buffer_multiplier_up(self) -> float | None:
        if self.estimate_liquidation_price_up:
            return (self.estimate_liquidation_price_up - self.proposal.top) / self.proposal.grid_range

        return None

    @property
    def buffer_multiplier_down(self) -> float | None:
        if self.estimate_liquidation_price_down:
            return (self.proposal.bottom - self.estimate_liquidation_price_down) / self.proposal.grid_range

        return None


@dataclass(frozen=True)
class IndicatorSet:
    interval: str
    as_of: datetime
    adx14: float
    atr14: float
    atr_pct_of_price: float
    sma50: float
    macd: float
    macd_signal: float
    rsi14: float
    last_price: float
    swing_high_14d: float
    swing_low_14d: float
    # Realized-vol term structure — computed by IndicatorService, consumed by Gate 1
    realized_vol_1d: float
    realized_vol_7d: float
    realized_vol_30d: float


@dataclass(frozen=True)
class DecisionVerdict:
    symbol: Symbol
    as_of: datetime
    action: VerdictAction
    gates: tuple[GateResult, ...]
    oid: str | None = None
    notes: str | None = None

    # Suggested parameters
    suggested_grid_top: float | None = None
    suggested_grid_bottom: float | None = None
    suggested_grid_levels: int | None = None
    suggested_grid_regime: Trend | None = None
    suggested_grid_type: GridType | None = None
    suggested_leverage: int | None = None


@dataclass(frozen=True)
class FundingOiSnapshot:
    symbol: Symbol
    as_of: datetime
    funding_rate_last: float
    open_interest: float
    oi_pct_change_7d: float | None  # None until 7 days of stored history exist

    @property
    def funding_rate_annualized_pct(self) -> float:
        return self.funding_rate_last * FUNDING_ANNUALIZATION_FACTOR


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    close: float
    high: float
    low: float
    volume: float


@dataclass(frozen=True)
class FundingRate:
    rate: float
    time: datetime


@dataclass(frozen=True)
class OpenInterest:
    symbol: Symbol
    open_interest: float


@dataclass(frozen=True)
class IndexPrice:
    pass


@dataclass
class Grid:
    symbol: Symbol
    top: float
    bottom: float
    levels: int
    trend: Trend
    grid_type: GridType
    leverage: float
    investment: float
    status: GridLaunchStatus
    decision_verdict: DecisionVerdict

    created_at: datetime
    realized_pnl: float | None = None
    oid: str | None = None
    closed_at: datetime | None = None

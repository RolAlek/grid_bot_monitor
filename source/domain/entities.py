from dataclasses import dataclass
from datetime import datetime
from typing import Any

from source.domain.value_objects import Gate, GateStatus, GridType, Symbol, Trend, VerdictAction


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    status: GateStatus
    reasons: tuple[str, ...]
    raw_values: dict[str, Any]


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
    suggested_grid_top: float | None = None
    suggested_grid_bottom: float | None = None
    suggested_leverage: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class FundingOiSnapshot:
    symbol: Symbol
    as_of: datetime
    funding_rate_last: float
    funding_rate_annualized_pct: float
    open_interest: float
    oi_pct_change_7d: float | None  # None until 7 days of stored history exist


@dataclass(frozen=True)
class Kline:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class FundingRate:
    rate: str
    time: datetime


@dataclass(frozen=True)
class OpenInterest:
    symbol: str
    open_interest: float


@dataclass(frozen=True)
class IndexPrice:
    pass

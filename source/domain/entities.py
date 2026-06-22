from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum, StrEnum
from typing import Any


class GateStatus(IntEnum):
    PASS = 0
    CAUTION = 1
    FAIL = 2


class VerdictAction(StrEnum):
    LAUNCH = "launch"
    HOLD = "hold"
    REVIEW = "review"


class Gate(Enum):
    REGIME_RANGE_FIT = 1
    POSITIONING = 2
    LIQUIDATION_SAFETY = 3


class Symbol(StrEnum):
    BTC = "USDT_BTC_REPR"


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    status: GateStatus
    reasons: tuple[str, ...]
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class ProposedGridParams:
    top: float
    bottom: float
    grid_levels: int
    leverage: int
    quote_investment: float


@dataclass(frozen=True)
class LiquidationEstimate:
    proposal: ProposedGridParams
    # None means no liquidation risk on that side (e.g. long-only grid has no upper liq)
    # 0.0 from API also means no risk — never treat as missing
    estimate_liquidation_price_up: float | None
    estimate_liquidation_price_down: float | None
    buffer_multiplier_up: float | None  # distance to liq / grid range width
    buffer_multiplier_down: float | None


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

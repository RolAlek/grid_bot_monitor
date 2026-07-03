from dataclasses import dataclass
from datetime import datetime

from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.value_objects import Symbol


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

    realized_vol_1d: float
    realized_vol_7d: float
    realized_vol_30d: float


@dataclass(frozen=True)
class FundingOiSnapshot:
    symbol: Symbol
    created_at: datetime
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

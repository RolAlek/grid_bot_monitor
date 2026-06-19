import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum
from typing import Self
from uuid import UUID


class GateStatus(StrEnum):
    PASS = "pass"
    CAUTION = "caution"
    FAIL = "fail"


class VerdictAction(StrEnum):
    LAUNCH = "launch"
    HOLD = "hold"
    REVIEW = "review"


class Gate(Enum):
    REGIME_RANGE_FIT = 1
    POSITIONING = 2
    LIQUIDATION_SAFETY = 3


@dataclass(frozen=True)
class Symbol:
    base: str
    quote: str
    suffix: str | None = None

    def __post_init__(self):
        if not re.match(r"^[A-Z0-9]+$", self.base):
            raise ValueError(f"Invalid base currency: {self.base}")
        if not re.match(r"^[A-Z0-9]+$", self.quote):
            raise ValueError(f"Invalid quote currency: {self.quote}")
        if self.suffix is not None and not re.match(r"^[A-Z0-9_]+$", self.suffix):
            raise ValueError(f"Invalid suffix: {self.suffix}")

    @classmethod
    def from_string(cls, raw: str) -> Self:
        raw = raw.strip().upper()

        separators = ["_", "/", "-"]
        parts = None

        for sep in separators:
            if sep in raw:
                parts = raw.split(sep)
                break

        if parts is None:
            raise ValueError(
                f"Unrecognized symbol format: {raw}. Expected separator among {separators}"
            )

        if len(parts) == 2:
            base, quote = parts[0], parts[1]
            suffix = None
        else:
            if len(parts) > 3:
                raise ValueError(f"Too many parts in symbol: {raw}")
            base = parts[0]
            quote = parts[1]
            suffix = parts[2] if len(parts) == 3 else None

        return cls(base=base, quote=quote, suffix=suffix)

    def to_pionex_format(self) -> str:
        if self.suffix:
            return f"{self.base}_{self.quote}_{self.suffix}"
        return f"{self.base}_{self.quote}"

    def to_binance_format(self) -> str:
        if self.suffix:
            return f"{self.base}{self.quote}_{self.suffix}"
        return f"{self.base}{self.quote}"

    def to_human_readable(self) -> str:
        if self.suffix:
            return f"{self.base}/{self.quote} ({self.suffix})"
        return f"{self.base}/{self.quote}"

    def __str__(self) -> str:
        return self.to_human_readable()

    def __repr__(self) -> str:
        return (
            f"Symbol(base={self.base!r}, quote={self.quote!r}, suffix={self.suffix!r})"
        )


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    status: GateStatus
    reasons: tuple[str]
    raw_values: dict


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
    decision_id: UUID
    symbol: Symbol
    as_of: datetime
    action: VerdictAction
    gates: list[GateResult]
    suggested_grid_top: float | None
    suggested_grid_bottom: float | None
    suggested_leverage: int | None
    notes: str


@dataclass(frozen=True)
class FundingOiSnapshot:
    snapshot_id: UUID
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
    pass


@dataclass(frozen=True)
class OpenInterest:
    pass


@dataclass(frozen=True)
class IndexPrice:
    pass

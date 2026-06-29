from dataclasses import dataclass
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


class GridType(StrEnum):
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class Trend(StrEnum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "no_trend"


class GridLaunchStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class Symbol(StrEnum):
    BTC = "BTC_USDT_PERP"

    @property
    def get_quote(self) -> str:
        return self.split("_")[0]

    @property
    def get_base(self) -> str:
        return self.split("_")[1]

    @property
    def get_type(self) -> str:
        return self.split("_")[2]


@dataclass(frozen=True)
class GateRule:
    triggered: bool
    status: GateStatus
    message: str


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    status: GateStatus
    reasons: tuple[str, ...]
    raw_values: dict[str, Any]

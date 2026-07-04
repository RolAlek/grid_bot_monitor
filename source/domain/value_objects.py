from enum import Enum, IntEnum, StrEnum, nonmember


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
    ETH = "ETH_USDT_PERP"
    SOL = "SOL_USDT_PERP"
    XRP = "XRP_USDT_PERP"
    XAUT = "XAUT_USDT_PERP"

    @property
    def quote(self) -> str:
        return self.split("_")[1]

    @property
    def base(self) -> str:
        return self.split("_")[0]

    @property
    def type_(self) -> str:
        return self.split("_")[2]

    @property
    def regime(self) -> GridType:
        if self in {self.XRP, self.XAUT}:
            return GridType.ARITHMETIC

        return GridType.GEOMETRIC


class HealthStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

    _ORDER = nonmember({GREEN: 0, YELLOW: 1, RED: 2})  # type: ignore[valid-type]

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, HealthStatus):
            return NotImplemented
        return self._ORDER[self] > self._ORDER[other]

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, HealthStatus):
            return NotImplemented
        return self._ORDER[self] >= self._ORDER[other]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HealthStatus):
            return NotImplemented
        return self._ORDER[self] < self._ORDER[other]

    def __le__(self, other: object) -> bool:
        if not isinstance(other, HealthStatus):
            return NotImplemented
        return self._ORDER[self] <= self._ORDER[other]


class AlertType(StrEnum):
    STATUS_CHANGE = "status_change"
    LIQUIDATION_RISK = "liquidation_risk"
    GRID_DEPLETION = "grid_depletion"
    HIGH_FUNDING = "high_funding"
    VOLATILITY_SPIKE = "volatility_spike"
    PNL_DRAWDOWN = "pnl_drawdown"
    API_ERROR = "api_error"


class ActionType(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    CLOSE = "close"
    RECONFIGURE = "reconfigure"
    ACKNOWLEDGE = "acknowledge"
    NONE = "none"

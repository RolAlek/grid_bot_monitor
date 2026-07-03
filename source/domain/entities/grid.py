from dataclasses import dataclass
from datetime import datetime

from source.domain.exceptions import InvalidGridParamsError
from source.domain.value_objects import GridLaunchStatus, GridType, Symbol, Trend


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

    last_price: float

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


@dataclass
class Grid:
    symbol: Symbol
    top: float
    bottom: float
    levels: int
    trend: Trend
    grid_type: GridType
    leverage: int
    investment: float
    status: GridLaunchStatus
    decision_verdict_oid: str

    oid: str | None = None
    external_id: str | None = None
    realized_pnl: float | None = None
    created_at: datetime | None = None
    closed_at: datetime | None = None
    stop_loss: float | None = None
    take_profit: float | None = None

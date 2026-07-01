from abc import ABC, abstractmethod
from typing import Protocol

from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingRate,
    GateResult,
    Grid,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
)
from source.domain.value_objects import GateStatus, Symbol


class Notifier(ABC):
    @abstractmethod
    async def send_alert(self, verdict: GateResult, prev_status: GateStatus | None = None) -> None: ...

    @abstractmethod
    async def send_digest(self, verdict: DecisionVerdict) -> None: ...


class MarketDataPort(Protocol):
    @abstractmethod
    async def get_funding_rates(self, symbol: Symbol, limit: int = 1) -> list[FundingRate]: ...

    @abstractmethod
    async def get_open_interest(self, symbol: Symbol) -> OpenInterest: ...

    @abstractmethod
    async def get_candles(self, symbol: Symbol, interval: str, limit: int) -> list[Candle]: ...


class GridPort(Protocol):
    @abstractmethod
    async def check_grid_params(self, params: ProposedGridParams) -> LiquidationEstimate: ...

    @abstractmethod
    async def place_grid(self, verdict: DecisionVerdict) -> Grid: ...

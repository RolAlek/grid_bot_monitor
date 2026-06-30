from abc import abstractmethod
from typing import Protocol

from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingRate,
    Grid,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
)
from source.domain.value_objects import GateResult, GateStatus, Symbol


class MarketDataPort(Protocol):
    @abstractmethod
    async def get_candles(
        self,
        symbol: Symbol,
        interval: str,
        limit: int,
    ) -> list[Candle]: ...

    @abstractmethod
    async def get_funding_rates(
        self,
        symbol: Symbol,
        limit: int,
    ) -> list[FundingRate]: ...

    @abstractmethod
    async def get_open_interest(self, symbol: Symbol) -> OpenInterest: ...


class NotifierPort(Protocol):
    @abstractmethod
    async def send_alert(self, result: GateResult, prev_status: GateStatus | None) -> None: ...

    @abstractmethod
    async def send_digest(self, verdict: DecisionVerdict) -> None: ...


class GridPort(Protocol):
    @abstractmethod
    async def check_grid_params(self, params: ProposedGridParams) -> LiquidationEstimate: ...

    @abstractmethod
    async def create_grid(self, verdict: DecisionVerdict) -> Grid: ...

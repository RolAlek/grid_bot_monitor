from abc import ABC, abstractmethod

from source.domain.value_objects import (
    DecisionVerdict,
    FundingRate,
    IndexPrice,
    Kline,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
    Symbol,
)


class MarketDataPort(ABC):
    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ) -> list[Kline]: ...

    @abstractmethod
    async def get_funding_rates(
        self,
        symbol: Symbol,
        limit: int,
    ) -> list[FundingRate]: ...

    @abstractmethod
    async def get_open_interest(self, symbol: Symbol) -> OpenInterest: ...

    @abstractmethod
    async def get_index_prices(self, symbol: Symbol) -> IndexPrice: ...


class NotifierPort(ABC):
    @abstractmethod
    async def send_alert(self, message: str) -> None: ...

    @abstractmethod
    async def send_digest(self, verdict: DecisionVerdict) -> None: ...


class GridValidationPort(ABC):
    @abstractmethod
    async def check_params(self, params: ProposedGridParams) -> LiquidationEstimate: ...

from abc import ABC, abstractmethod

from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingRate,
    GateResult,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
)
from source.domain.entities.monitoring import Bot, BotOrderSnapshot, ClassificationResult
from source.domain.value_objects import GateStatus, HealthStatus, Symbol


class Notifier(ABC):
    @abstractmethod
    async def send_alert(self, verdict: GateResult, prev_status: GateStatus | None = None) -> None: ...

    @abstractmethod
    async def send_digest(self, verdict: DecisionVerdict) -> None: ...

    @abstractmethod
    async def send_health_alert(
        self,
        bot: Bot,
        previous_status: HealthStatus,
        result: ClassificationResult,
    ) -> None: ...


class MarketDataPort(ABC):
    @abstractmethod
    async def get_funding_rates(self, symbol: Symbol, limit: int = 1) -> list[FundingRate]: ...

    @abstractmethod
    async def get_open_interest(self, symbol: Symbol) -> OpenInterest: ...

    @abstractmethod
    async def get_candles(self, symbol: Symbol, interval: str, limit: int) -> list[Candle]: ...


class GridPort(ABC):
    @abstractmethod
    async def check_grid_params(self, params: ProposedGridParams) -> LiquidationEstimate: ...

    @abstractmethod
    async def place_grid(self, verdict: DecisionVerdict) -> Bot: ...

    @abstractmethod
    async def get_futures_grid_order(self, bu_order_id: str) -> BotOrderSnapshot: ...

    @abstractmethod
    async def cancel_futures_grid(self, bu_order_id: str, close_note: str | None = None) -> bool: ...

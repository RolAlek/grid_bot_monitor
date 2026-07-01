from abc import ABC, abstractmethod
from typing import Protocol

from source.domain.entities import DecisionVerdict, FundingRate, GateResult, OpenInterest
from source.domain.value_objects import GateStatus


class Notifier(ABC):
    @abstractmethod
    async def send_alert(
        self,
        verdict: GateResult,
        prev_status: GateStatus | None = None,
        previous_message_id: int | None = None,
    ) -> None: ...

    @abstractmethod
    async def send_digest(self, verdict: DecisionVerdict, previous_message_id: int | None = None) -> None: ...


class MarketDataPort(Protocol):
    @abstractmethod
    async def get_funding_rates(self, symbol: str, limit: int = 1) -> list[FundingRate]: ...

    @abstractmethod
    async def get_open_interest(self, symbol: str) -> OpenInterest: ...

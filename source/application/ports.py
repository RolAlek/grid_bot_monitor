from abc import ABC, abstractmethod

from source.domain.entities import DecisionVerdict, GateResult
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

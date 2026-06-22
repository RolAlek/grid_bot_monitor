from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from source.domain.entities import DecisionVerdict, Symbol
from source.infrastructure.database.repositories.decision_repository import DecisionLogRepository


class DecisionLogService:
    def __init__(
        self,
        provider_decision_log_repository: Callable[[], AbstractAsyncContextManager[DecisionLogRepository]],
    ) -> None:
        self._provider_decision_log_repository = provider_decision_log_repository

    async def persist_verdict(self, verdict: DecisionVerdict) -> None:

        async with self._provider_decision_log_repository() as repository:
            await repository.save_decision(verdict)

    async def get_last_decision(self, symbol: Symbol) -> DecisionVerdict | None:

        async with self._provider_decision_log_repository() as repository:
            return await repository.get_last_decision(symbol)

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from source.domain.entities import DecisionVerdict
from source.domain.exceptions import DecisionNotFoundError
from source.domain.value_objects import Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters.base import BaseFieldCondition, BaseQueryFilter, Operator


class DecisionLogService:
    def __init__(
        self,
        provider_decision_log_repository: Callable[
            [], AbstractAsyncContextManager[AbstractRepository[DecisionVerdict]]
        ],
    ) -> None:
        self._provider_decision_log_repository = provider_decision_log_repository

    async def persist_verdict(self, verdict: DecisionVerdict) -> DecisionVerdict:

        async with self._provider_decision_log_repository() as repository:
            return await repository.add(verdict)

    async def get_last_decision(self, symbol: Symbol) -> DecisionVerdict | None:
        filters = BaseQueryFilter(
            conditions=(BaseFieldCondition(field="symbol", operator=Operator.EQUALS, value=symbol.value),),
            order_by=("-created_at",),
        )

        async with self._provider_decision_log_repository() as repository:
            return await repository.get_one(filters)

    async def get_decision_by_oid(self, oid: str) -> DecisionVerdict:
        async with self._provider_decision_log_repository() as repository:
            verdict = await repository.get_by_oid(oid)

        if not verdict:
            raise DecisionNotFoundError(f"Decision with {oid} does not exist")

        return verdict

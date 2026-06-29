from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from source.domain.entities import Grid
from source.domain.value_objects import GridLaunchStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters.base import BaseFieldCondition, BaseQueryFilter, Operator


class GridBotService:
    def __init__(
        self,
        provider_oi_snapshot_repository: Callable[[], AbstractAsyncContextManager[AbstractRepository[Grid]]],
    ) -> None:
        self._provider_oi_snapshot_repository = provider_oi_snapshot_repository

    async def get_grid(self, symbol: Symbol, status: GridLaunchStatus) -> Grid | None:
        filters = BaseQueryFilter(
            conditions=(
                BaseFieldCondition("symbol", Operator.EQUALS, symbol.value),
                BaseFieldCondition("status", Operator.EQUALS, status.value),
            ),
        )
        async with self._provider_oi_snapshot_repository() as repository:
            return await repository.get_one(filters)

    async def persist_grid(self, grid: Grid) -> None:
        async with self._provider_oi_snapshot_repository() as repository:
            await repository.add(grid)

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from source.application.ports import GridPort
from source.domain.entities import DecisionVerdict, Grid
from source.domain.value_objects import GridLaunchStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters.base import BaseFieldCondition, BaseQueryFilter, Operator


class GridBotService:
    def __init__(
        self,
        provider_launch_grid_repository: Callable[[], AbstractAsyncContextManager[AbstractRepository[Grid]]],
        grid_port: GridPort,
    ) -> None:
        self._provider_launch_grid_repository = provider_launch_grid_repository
        self._grid_port = grid_port

    async def get_grid(self, symbol: Symbol, status: GridLaunchStatus) -> Grid | None:
        filters = BaseQueryFilter(
            conditions=(
                BaseFieldCondition("symbol", Operator.EQUALS, symbol.value),
                BaseFieldCondition("status", Operator.EQUALS, status.value),
            ),
        )
        async with self._provider_launch_grid_repository() as repository:
            return await repository.get_one(filters)

    async def persist_grid(self, grid: Grid) -> None:
        async with self._provider_launch_grid_repository() as repository:
            await repository.add(grid)

    async def create_grid_with_api(self, verdict: DecisionVerdict) -> None:
        api_result = await self._grid_port.create_grid(verdict)

        await self.persist_grid(api_result)

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from source.application.ports import GridPort
from source.domain.entities import DecisionVerdict, Grid
from source.domain.exceptions import DecisionNotFoundError
from source.domain.value_objects import GridLaunchStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters.base import BaseFieldCondition, BaseQueryFilter, Operator


class GridBotService:
    def __init__(
        self,
        provider_launch_grid_repository: Callable[[], AbstractAsyncContextManager[AbstractRepository[Grid]]],
        provider_decision_log_repository: Callable[
            [], AbstractAsyncContextManager[AbstractRepository[DecisionVerdict]]
        ],
        grid_port: GridPort,
    ) -> None:
        self._provider_launch_grid_repository = provider_launch_grid_repository
        self._provider_decision_log_repository = provider_decision_log_repository
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

    async def persist_grid(self, grid: Grid) -> Grid:
        async with self._provider_launch_grid_repository() as repository:
            return await repository.add(grid)

    async def launch_grid_with_api(self, verdict_oid: str) -> Grid:
        async with self._provider_decision_log_repository() as repository:
            verdict = await repository.get_by_oid(verdict_oid)

        if not verdict:
            raise DecisionNotFoundError(f"Decision with {verdict_oid} does not exist")

        api_result = await self._grid_port.create_grid(verdict)

        return await self.persist_grid(api_result)

    async def launch_grid_manual(self, verdict_oid: str) -> Grid:
        async with self._provider_decision_log_repository() as repository:
            verdict = await repository.get_by_oid(verdict_oid)

        if not verdict or not verdict.suggested_parameters or not verdict.oid:
            raise DecisionNotFoundError(f"Decision with {verdict_oid} does not exist")

        return await self.persist_grid(
            Grid(
                symbol=verdict.symbol,
                top=verdict.suggested_parameters.top,
                bottom=verdict.suggested_parameters.bottom,
                trend=verdict.suggested_parameters.trend,
                levels=verdict.suggested_parameters.grid_levels,
                grid_type=verdict.suggested_parameters.grid_type,
                leverage=verdict.suggested_parameters.leverage,
                investment=verdict.suggested_parameters.quote_investment,
                status=GridLaunchStatus.RUNNING,
                decision_verdict_oid=verdict.oid,
                stop_loss=verdict.suggested_parameters.stop_loss,
                take_profit=verdict.suggested_parameters.take_profit,
            )
        )

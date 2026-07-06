from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from source.application.ports import GridPort
from source.domain.entities import DecisionVerdict
from source.domain.entities.monitoring import Bot
from source.domain.exceptions import DecisionNotFoundError
from source.domain.value_objects import GridLaunchStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter, Operator


class GridBotService:
    def __init__(
        self,
        provider_bot_repository: Callable[[], AbstractAsyncContextManager[AbstractRepository[Bot]]],
        provider_decision_log_repository: Callable[
            [], AbstractAsyncContextManager[AbstractRepository[DecisionVerdict]]
        ],
        grid_port: GridPort,
        on_launch: Callable[[Symbol], None] | None = None,
    ) -> None:
        self._provider_bot_repository = provider_bot_repository
        self._provider_decision_log_repository = provider_decision_log_repository
        self._grid_port = grid_port
        self._on_launch = on_launch

    async def get_grid(self, symbol: Symbol, status: GridLaunchStatus) -> Bot | None:
        filters = BaseQueryFilter(
            conditions=(
                BaseFieldCondition("symbol", Operator.EQUALS, symbol.value),
                BaseFieldCondition("status", Operator.EQUALS, status.value),
            ),
        )
        async with self._provider_bot_repository() as repository:
            return await repository.get_one(filters)

    async def persist_grid(self, grid: Bot) -> Bot:
        async with self._provider_bot_repository() as repository:
            return await repository.add(grid)

    async def launch_grid_with_api(self, verdict_oid: UUID) -> Bot:
        async with self._provider_decision_log_repository() as repository:
            verdict = await repository.get_by_oid(verdict_oid)

        if not verdict:
            raise DecisionNotFoundError(f"Decision with {verdict_oid} does not exist")

        api_result = await self._grid_port.place_grid(verdict)
        bot = await self.persist_grid(api_result)

        if self._on_launch is not None:
            self._on_launch(verdict.symbol)
        return bot

    async def launch_grid_manual(self, verdict_oid: UUID) -> Bot:
        async with self._provider_decision_log_repository() as repository:
            verdict = await repository.get_by_oid(verdict_oid)

        if not verdict or not verdict.suggested_parameters or not verdict.oid:
            raise DecisionNotFoundError(f"Decision with {verdict_oid} does not exist")

        bot = await self.persist_grid(
            Bot(
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

        if self._on_launch is not None:
            self._on_launch(verdict.symbol)
        return bot

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime

import structlog

from source.application.ports import GridPort
from source.application.services.gates.assess_liquidation_safety_third_gate import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.application.services.grid_builder import GridProposalBuilder
from source.application.services.indicator_service import IndicatorService
from source.domain.entities import ProposedGridParams
from source.domain.entities.monitoring import Bot
from source.domain.exceptions import BotIntegrityError, BotNotFoundError
from source.domain.value_objects import GateStatus, GridLaunchStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter, Operator
from source.infrastructure.exceptions import HttpRequestError
from source.utils.error_logging import log_error


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class BotManagementService:
    def __init__(
        self,
        grid_port: GridPort,
        active_bot_repo_factory: Callable[[], AbstractAsyncContextManager[AbstractRepository[Bot]]],
        indicator_service: IndicatorService,
        grid_builder: GridProposalBuilder,
        gate1: AssessMarketRegimeService,
        gate2: AssessPositioningService,
        gate3: AssessLiquidationSafetyService,
        on_close: Callable[[Symbol], None] | None = None,
    ) -> None:
        self._grid_port = grid_port
        self._active_bot_repo_factory = active_bot_repo_factory
        self._indicator_service = indicator_service
        self._grid_builder = grid_builder
        self._gate1 = gate1
        self._gate2 = gate2
        self._gate3 = gate3
        self._on_close = on_close

    def set_on_close(self, callback: Callable[[Symbol], None]) -> None:
        self._on_close = callback

    async def pause_bot(self, symbol: Symbol) -> bool:
        bot = await self._find_by_statuses(symbol, [GridLaunchStatus.RUNNING])
        if bot is None:
            raise BotNotFoundError(f"No running bot found for {symbol.value}")

        bot.paused_by_monitor = True
        bot.status = GridLaunchStatus.PAUSED
        await self._save(bot)
        logger.info("Bot paused by monitor", symbol=symbol.value, bot_oid=str(bot.oid))
        return True

    async def resume_bot(self, symbol: Symbol) -> bool:
        bot = await self._find_by_statuses(symbol, [GridLaunchStatus.PAUSED])
        if bot is None:
            raise BotNotFoundError(f"No paused bot found for {symbol.value}")

        bot.paused_by_monitor = False
        bot.status = GridLaunchStatus.RUNNING
        await self._save(bot)
        logger.info("Bot resumed by monitor", symbol=symbol.value, bot_oid=str(bot.oid))
        return True

    async def close_bot(self, symbol: Symbol, reason: str = "") -> bool:
        bot = await self._find_by_statuses(symbol, [GridLaunchStatus.RUNNING, GridLaunchStatus.PAUSED])
        if not bot:
            raise BotNotFoundError(f"No active bot found for {symbol.value}")

        if not bot.external_id:
            raise BotIntegrityError(f"Bot {symbol.value} has no external_id — cannot close via API")

        try:
            await self._grid_port.cancel_futures_grid(bot.external_id, close_note=reason or None)
        except HttpRequestError as exc:
            log_error(logger, exc, level="warning", symbol=symbol.value, bot_oid=str(bot.oid))

        bot.status = GridLaunchStatus.CLOSED
        bot.closed_at = datetime.now(UTC)
        await self._save(bot)
        logger.info("Bot closed via API", symbol=symbol.value, bot_oid=str(bot.oid), reason=reason)

        if self._on_close is not None:
            self._on_close(symbol)

        return True

    async def reconfigure_bot(self, symbol: Symbol) -> ProposedGridParams | None:
        gate1_result, proposal = await self._gate1.execute(symbol)
        gate2_result = await self._gate2.execute(symbol)
        gate3_result = await self._gate3.execute(proposal)

        failed = [
            result.gate.name
            for result in (gate1_result, gate2_result, gate3_result)
            if result.status == GateStatus.FAIL
        ]

        if failed:
            logger.warning(
                "Reconfigure blocked by failed gates",
                symbol=symbol.value,
                failed_gates=failed,
            )
            return None

        logger.info("Reconfigure proposal generated", symbol=symbol.value)
        return proposal

    async def _find_by_statuses(
        self,
        symbol: Symbol,
        statuses: list[GridLaunchStatus],
    ) -> Bot | None:
        filters = BaseQueryFilter(
            conditions=(
                BaseFieldCondition("symbol", Operator.EQUALS, symbol.value),
                BaseFieldCondition("status", Operator.IN, {status.value for status in statuses}),
            ),
        )
        async with self._active_bot_repo_factory() as repo:
            return await repo.get_one(filters)

    async def _save(self, bot: Bot) -> None:
        async with self._active_bot_repo_factory() as repo:
            await repo.add(bot)

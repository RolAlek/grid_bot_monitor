from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

import structlog

from source.application.ports import Notifier
from source.application.services.bot_management_service import BotManagementService
from source.domain.entities.monitoring import Bot, ClassificationResult, HealthSnapshot
from source.domain.exceptions import BotNotFoundError
from source.domain.value_objects import ActionType, HealthStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter, Operator
from source.infrastructure.exceptions import InfrastructureError
from source.settings import MonitoringSettings
from source.utils.error_logging import log_error


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AutoAdjustService:
    def __init__(
        self,
        settings: MonitoringSettings,
        bot_management: BotManagementService,
        notifier: Notifier,
        bot_repo_factory: Callable[[], AbstractAsyncContextManager[AbstractRepository[Bot]]],
        health_snapshot_repo_factory: Callable[[], AbstractAsyncContextManager[AbstractRepository[HealthSnapshot]]],
    ) -> None:
        self._settings = settings
        self._bot_management = bot_management
        self._notifier = notifier
        self._bot_repo_factory = bot_repo_factory
        self._health_snapshot_repo_factory = health_snapshot_repo_factory

    async def evaluate_and_act(self, bot: Bot) -> ActionType:
        if not self._settings.auto_adjust_enabled or bot.paused_by_monitor:
            return ActionType.NONE

        if bot.health_status == HealthStatus.RED and self._settings.auto_pause_on_red:
            return await self._handle_red(bot)

        if bot.health_status == HealthStatus.YELLOW:
            return await self._handle_yellow(bot)

        return ActionType.NONE

    async def evaluate_all(self) -> list[str]:
        actions: list[str] = []
        async with self._bot_repo_factory() as repo:
            bots = await repo.get_list()

        for bot in bots:
            action = await self.evaluate_and_act(bot)
            if action != ActionType.NONE:
                actions.append(f"{bot.symbol.value}: {action.value}")

        logger.info("Auto-adjust cycle complete", total=len(bots), actions=len(actions))
        return actions

    async def evaluate_one(self, symbol: Symbol) -> ActionType:
        criteria = BaseQueryFilter(
            conditions=(BaseFieldCondition(field="symbol", operator=Operator.EQUALS, value=symbol.value),)
        )
        async with self._bot_repo_factory() as repo:
            bot = await repo.get_one(criteria)

        if not bot:
            logger.debug("Auto-adjust skipped — bot not found", symbol=symbol.value)
            return ActionType.NONE

        try:
            return await self.evaluate_and_act(bot)
        except InfrastructureError as exc:
            log_error(logger, exc, level="error", symbol=symbol.value)
            return ActionType.NONE

    async def _handle_red(self, bot: Bot) -> ActionType:
        try:
            await self._bot_management.pause_bot(bot.symbol)
        except BotNotFoundError as exc:
            log_error(logger, exc, level="warning", symbol=bot.symbol.value)
            return ActionType.NONE

        await self._notifier.send_health_alert(
            bot,
            previous_status=bot.health_status,
            result=ClassificationResult(
                status=HealthStatus.RED,
                score=0.0,
                alerts=(),
                details={"reason": "Auto-paused by monitor (RED status)"},
            ),
        )
        logger.info("Bot auto-paused", symbol=bot.symbol.value, bot_oid=str(bot.oid))
        return ActionType.PAUSE

    async def _handle_yellow(self, bot: Bot) -> ActionType:
        if bot.oid is None:
            return ActionType.NONE

        consecutive = await self._count_consecutive_yellow(bot.oid)
        threshold = self._settings.max_consecutive_yellow_before_action

        if consecutive >= threshold:
            await self._notifier.send_health_alert(
                bot,
                previous_status=bot.health_status,
                result=ClassificationResult(
                    status=HealthStatus.YELLOW,
                    score=0.5,
                    alerts=(),
                    details={"reason": f"YELLOW for {consecutive} consecutive cycles — consider reconfigure"},
                ),
            )
            logger.info(
                "Consecutive YELLOW threshold reached",
                symbol=bot.symbol.value,
                consecutive=consecutive,
                threshold=threshold,
            )
            return ActionType.RECONFIGURE

        return ActionType.NONE

    async def _count_consecutive_yellow(self, bot_oid: UUID) -> int:
        lookback = self._settings.max_consecutive_yellow_before_action + 1
        filters = BaseQueryFilter(
            conditions=(BaseFieldCondition("grid_launch_oid", Operator.EQUALS, bot_oid),),
            order_by=("-created_at",),
            limit=lookback,
        )
        async with self._health_snapshot_repo_factory() as repo:
            snapshots = await repo.get_list(filters)

        count = 0
        for snapshot in snapshots:
            if snapshot.health_status == HealthStatus.YELLOW:
                count += 1
            else:
                break
        return count

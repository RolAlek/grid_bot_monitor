import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from uuid import UUID

import structlog
from httpx import ConnectError, NetworkError, RemoteProtocolError, TimeoutException

from source.application.ports import GridPort, MarketDataPort
from source.application.services.alert_service import AlertService
from source.application.services.health_classifier import HealthClassifier
from source.application.services.indicator_service import IndicatorService
from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.entities.indicators import IndicatorSet
from source.domain.entities.monitoring import (
    Bot,
    BotOrderSnapshot,
    ClassificationResult,
    HealthMetricsInput,
    HealthSnapshot,
)
from source.domain.exceptions import BotIntegrityError, BotNotFoundError
from source.domain.value_objects import AlertType, GridLaunchStatus, HealthStatus, Symbol, Trend
from source.infrastructure.database.repositories.alchemy.health_snapshot_repository import (
    SQLAlchemyHealthSnapshotRepository,
)
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter, Operator
from source.infrastructure.exceptions import BaseInfrastructureError


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class HealthMonitorService:
    def __init__(
        self,
        indicator_service: IndicatorService,
        grid_port: GridPort,
        market_data: MarketDataPort,
        classifier: HealthClassifier,
        bot_repo_factory: Callable[[], AbstractAsyncContextManager[AbstractRepository[Bot]]],
        health_snapshot_repo_factory: Callable[[], AbstractAsyncContextManager[SQLAlchemyHealthSnapshotRepository]],
        alert_service: AlertService | None = None,
    ) -> None:
        self._indicator_service = indicator_service
        self._grid_port = grid_port
        self._market_data = market_data
        self._classifier = classifier
        self._bot_repo_factory = bot_repo_factory
        self._health_snapshot_repo_factory = health_snapshot_repo_factory
        self._alert_service = alert_service

    async def run_all_checks(self) -> list[ClassificationResult]:
        bots = await self._pull_active_bots()
        tasks = [self._check_single_bot(bot) for bot in bots]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: list[ClassificationResult] = []
        for bot, result in zip(bots, results, strict=False):
            if isinstance(result, ClassificationResult):
                outputs.append(result)
            else:
                logger.error("Health check failed for bot", symbol=bot.symbol.value, error=str(result))

        logger.info("Health check cycle complete", total=len(bots), success=len(outputs))
        return outputs

    async def check_single_bot_by_symbol(self, symbol: Symbol) -> ClassificationResult | None:
        bot = await self._pull_active_bot(symbol)

        if bot is None:
            return None
        return await self._check_single_bot(bot)

    async def _pull_active_bots(self) -> list[Bot]:
        filters = BaseQueryFilter((
            BaseFieldCondition(
                "status",
                Operator.IN,
                (GridLaunchStatus.RUNNING.value, GridLaunchStatus.PAUSED.value),
            ),
        ))
        async with self._bot_repo_factory() as repo:
            bots = await repo.get_list(filters)

        if not bots:
            raise BotNotFoundError("No running or paused bots found for check")

        return bots

    async def _pull_active_bot(self, symbol: Symbol | None = None) -> Bot | None:
        conditions: list[BaseFieldCondition] = [
            BaseFieldCondition(
                "status",
                Operator.IN,
                (GridLaunchStatus.RUNNING.value, GridLaunchStatus.PAUSED.value),
            ),
        ]
        if symbol is not None:
            conditions.append(BaseFieldCondition("symbol", Operator.EQUALS, symbol.value))

        async with self._bot_repo_factory() as repo:
            bot = await repo.get_one(BaseQueryFilter(conditions=tuple(conditions)))

        if not bot:
            raise BotNotFoundError(f"No running or paused bots found for {symbol}")

        return bot

    async def _check_single_bot(self, bot: Bot) -> ClassificationResult:

        previous_status = bot.health_status

        try:
            return await self._do_check_single_bot(bot, previous_status)
        except (BaseInfrastructureError, ConnectError, TimeoutException, NetworkError, RemoteProtocolError) as exc:
            logger.warning(
                "Health check failed — infrastructure error",
                symbol=bot.symbol.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return ClassificationResult(
                status=previous_status,
                score=0.5,
                alerts=(AlertType.API_ERROR,),
                details={"error": f"{type(exc).__name__}: {exc}"},
            )

    async def _do_check_single_bot(
        self,
        bot: Bot,
        previous_status: HealthStatus,
    ) -> ClassificationResult:
        if not bot.external_id:
            raise BotIntegrityError(f"Bot {bot.oid} ({bot.symbol.value}) has no external_id in _do_check")
        order = await self._grid_port.get_futures_grid_order(bot.external_id)
        indicators = await self._indicator_service.compute(bot.symbol)

        rates = await self._market_data.get_funding_rates(bot.symbol, limit=1)
        funding_rate = rates[-1].rate if rates else 0.0

        derived = self._derive_metrics(order, indicators, funding_rate, bot.symbol)
        result = self._classifier.classify(derived)

        if result.status != previous_status:
            logger.info(
                "Health status changed from [%s] => [%s] for %s}",
                previous_status.name,
                result.status.name,
                bot.symbol.value,
            )
            result = ClassificationResult(
                status=result.status,
                score=result.score,
                alerts=(*result.alerts, AlertType.STATUS_CHANGE),
                details=result.details,
            )

        if self._alert_service is not None:
            await self._alert_service.send_health_alert(bot, previous_status, result)

        await self._create_snapshot(bot, indicators, derived, funding_rate, result)

        await self._update_bot(bot, result.status, derived.liquidation_price, derived)

        return result

    def _derive_metrics(
        self,
        order: BotOrderSnapshot,
        indicators: IndicatorSet,
        funding_rate: float,
        symbol: Symbol,
    ) -> HealthMetricsInput:
        unrealized_pnl, _unrealized_pnl_pct = self._calculate_pnl(order, symbol)
        liq_price, distance_to_liq_pct = self._calculate_liquidation_metrics(order, indicators.last_price)
        funding_annualized = funding_rate * FUNDING_ANNUALIZATION_FACTOR

        return HealthMetricsInput.build_from(
            symbol,
            indicators,
            order.leverage,
            unrealized_pnl,
            self._calculate_fill_ratio(order),
            distance_to_liq_pct,
            funding_annualized,
            unrealized_pnl,
            liq_price,
        )

    @staticmethod
    def _calculate_pnl(order: BotOrderSnapshot, symbol: Symbol) -> tuple[float, float | None]:
        unrealized_pnl = order.profit_reduce + order.funding_fee_payment
        quote_investment = order.quote_investment

        if quote_investment:
            unrealized_pnl_pct = unrealized_pnl / quote_investment * 100

        else:
            logger.warning("quote_investment missing from response — PnL % unavailable", symbol=symbol.value)
            unrealized_pnl_pct = None

        return unrealized_pnl, unrealized_pnl_pct

    def _calculate_fill_ratio(self, order: BotOrderSnapshot) -> float:
        position = abs(order.position or 0.0)
        per_volume = order.per_volume or 0.0
        row = order.row
        return min(position / (row * per_volume), 1.0) if row > 0 and per_volume > 0 else 0.0

    def _calculate_liquidation_metrics(self, order: BotOrderSnapshot, last_price: float) -> tuple[float | None, float]:
        liq_price_up = order.estimate_liquidation_price_up or 0.0
        liq_price_down = order.estimate_liquidation_price_down or 0.0

        if order.trend == Trend.LONG and liq_price_down > 0:
            liq_price = liq_price_down
        elif order.trend == Trend.SHORT and liq_price_up > 0:
            liq_price = liq_price_up
        else:
            candidates = [price for price in (liq_price_up, liq_price_down) if price]
            liq_price = min(candidates, key=lambda p: abs(last_price - p)) if candidates else None

        distance_to_liq_pct = abs(last_price - liq_price) / last_price * 100 if liq_price and liq_price > 0 else 100.0

        return liq_price, distance_to_liq_pct

    async def _get_latest_snapshot(self, grid_launch_oid: UUID) -> HealthSnapshot | None:
        criteria = BaseQueryFilter(
            conditions=(BaseFieldCondition("grid_launch_oid", Operator.EQUALS, grid_launch_oid),),
            order_by=("-created_at",),
            limit=1,
        )
        async with self._health_snapshot_repo_factory() as repo:
            return await repo.get_one(criteria)

    async def _create_snapshot(
        self,
        bot: Bot,
        indicators: IndicatorSet,
        metrics: HealthMetricsInput,
        funding_rate: float,
        classified: ClassificationResult,
    ) -> None:

        async with self._health_snapshot_repo_factory() as repo:
            await repo.add(HealthSnapshot.build_from(bot, indicators, metrics, funding_rate, classified))

    async def _update_bot(
        self,
        bot: Bot,
        status: HealthStatus,
        liq_price: float | None,
        metrics: HealthMetricsInput,
    ) -> None:
        bot.health_status = status
        bot.current_pnl = metrics.unrealized_pnl
        bot.current_pnl_pct = metrics.unrealized_pnl_pct
        bot.distance_to_liquidation_pct = metrics.distance_to_liquidation_pct
        bot.grid_fill_ratio = metrics.grid_fill_ratio
        bot.last_price = liq_price
        bot.last_health_check_at = datetime.now(UTC)

        async with self._bot_repo_factory() as repository:
            updated = await repository.update_monitoring_fields(bot)  # type: ignore[attr-defined]

            if not updated:
                logger.warning(
                    "Monitoring update had no effect — bot may have been closed",
                    bot_oid=bot.oid,
                    symbol=bot.symbol.value,
                )

    async def cleanup_old_snapshots(self, ttl_days: int) -> int:
        async with self._health_snapshot_repo_factory() as repo:
            return await repo.delete_older_than(ttl_days)

from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import cache
from typing import Any

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.gates.assess_liquidation_safety_third_gate import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.application.services.grid_builder import GridProposalBuilder
from source.application.services.grid_service import GridBotService
from source.application.services.indicator_service import IndicatorService
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.services.run_daily_positioning_check import RunDailyPositioningCheck
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.infrastructure.database.engine import async_session_factory
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository
from source.infrastructure.database.repositories.alchemy.decision_repository import SQLAlchemyDecisionLogRepository
from source.infrastructure.database.repositories.alchemy.launched_grid_repository import (
    SQLAlchemyLaunchedGridRepository,
)
from source.infrastructure.database.repositories.alchemy.snapshot_repository import SQLAlchemySnapshotRepository
from source.infrastructure.http.pionex.auth_strategy import CustomPionexAuth
from source.infrastructure.http.pionex.pionex_http_client import PionexHTTPClient
from source.infrastructure.http.pionex.staleness_guard_adapter import StalenessGuardAdapter
from source.infrastructure.telegram.aiogram_notifier import AiogramNotifier
from source.settings import get_settings


@cache
def get_telegram_bot() -> Bot:
    settings = get_settings()
    return Bot(token=settings.telegram.token.get_secret_value())


@cache
def get_notifier() -> AiogramNotifier:
    settings = get_settings()
    return AiogramNotifier(bot=get_telegram_bot(), chat_id=settings.telegram.chat_id)


@cache
def create_service_provider_dependency[RC: SQLAlchemyBaseRepository[Any, Any]](
    repository_class: Callable[[AsyncSession], RC],
) -> Callable[[], AbstractAsyncContextManager[RC]]:
    @asynccontextmanager
    async def provider() -> AsyncGenerator[RC]:
        async with async_session_factory() as session:
            try:
                yield repository_class(session)
                await session.commit()
            except Exception:
                await session.rollback()

    return provider


@cache
def get_pionex_client() -> PionexHTTPClient:
    settings = get_settings()

    return PionexHTTPClient(
        base_url=settings.pionex.connection_url,
        timeout=settings.pionex.timeout,
        auth=CustomPionexAuth(settings=settings.pionex),
    )


@cache
def get_snapshot_service() -> OISnapshotService:
    return OISnapshotService(
        provider_oi_snapshot_repository=create_service_provider_dependency(SQLAlchemySnapshotRepository),
        market_data_client=get_pionex_client(),
    )


@cache
def get_decision_service() -> DecisionLogService:
    return DecisionLogService(
        provider_decision_log_repository=create_service_provider_dependency(SQLAlchemyDecisionLogRepository)
    )


@cache
def get_launch_service() -> GridBotService:
    return GridBotService(
        provider_launch_grid_repository=create_service_provider_dependency(SQLAlchemyLaunchedGridRepository),
        provider_decision_log_repository=create_service_provider_dependency(SQLAlchemyDecisionLogRepository),
        grid_port=get_pionex_client(),
    )


@cache
def get_first_gate_service() -> AssessMarketRegimeService:
    settings = get_settings()

    return AssessMarketRegimeService(
        settings=settings,
        indicator_service=IndicatorService(settings=settings.pionex, market_data=get_pionex_client()),
        grid_builder=GridProposalBuilder(settings.decision_engine),
    )


@cache
def get_second_gate_service() -> AssessPositioningService:
    settings = get_settings()

    return AssessPositioningService(
        settings=settings.decision_engine,
        market_data=get_pionex_client(),
        oi_service=get_snapshot_service(),
    )


@cache
def get_third_gate_service() -> AssessLiquidationSafetyService:
    settings = get_settings()

    return AssessLiquidationSafetyService(
        settings=settings.decision_engine,
        grid_validation=StalenessGuardAdapter(delegate=get_pionex_client()),
    )


@cache
def get_daily_runner() -> RunDailyPositioningCheck:
    settings = get_settings()
    return RunDailyPositioningCheck(
        second_gate=get_second_gate_service(),
        decision_service=get_decision_service(),
        notifier=get_notifier(),
        settings=settings,
    )


@cache
def get_weekly_runner() -> RunWeeklyFullAssessment:
    settings = get_settings()

    return RunWeeklyFullAssessment(
        decision_service=get_decision_service(),
        gate1=get_first_gate_service(),
        gate2=get_second_gate_service(),
        gate3=get_third_gate_service(),
        notifier=get_notifier(),
        settings=settings,
    )

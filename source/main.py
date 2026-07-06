import asyncio

import structlog
from aiogram import Dispatcher
from aiogram.types import BotCommand

from source.dependencies import (
    get_bot_management_service,
    get_daily_runner,
    get_decision_service,
    get_health_monitor_service,
    get_launch_service,
    get_scheduler,
    get_telegram_bot,
    get_weekly_runner,
)
from source.presentation.bot.handlers.common_handlers import common_router
from source.presentation.bot.handlers.decision_handlers import decision_router
from source.presentation.bot.handlers.launch_grid_handlers import grid_router
from source.presentation.bot.handlers.monitor_handlers import monitor_router
from source.presentation.scheduler.jobs import register_jobs
from source.presentation.scheduler.jobs.lifecycle import schedule_bot_monitoring, unschedule_bot_monitoring
from source.presentation.scheduler.jobs.monitor import register_cleanup_job
from source.settings import get_settings
from source.utils.logging_config import configure_logging


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.app)

    bot = get_telegram_bot()
    dp = Dispatcher()
    dp.include_router(common_router())
    dp.include_router(
        decision_router(
            weekly_runner=get_weekly_runner(),
            daily_runner=get_daily_runner(),
            decision_service=get_decision_service(),
        )
    )
    dp.include_router(grid_router(grid_launch_service=get_launch_service()))
    dp.include_router(
        monitor_router(
            monitor_service=get_health_monitor_service(),
            bot_management=get_bot_management_service(),
            settings=settings,
        )
    )

    scheduler = get_scheduler()
    register_jobs(scheduler, daily_runner=get_daily_runner(), weekly_runner=get_weekly_runner())
    register_cleanup_job(
        scheduler,
        monitor_service=get_health_monitor_service(),
        settings=settings.monitoring,
    )
    # Wire per-symbol job lifecycle callbacks
    launch_svc = get_launch_service()
    launch_svc._on_launch = schedule_bot_monitoring  # noqa: SLF001
    mgmt_svc = get_bot_management_service()
    mgmt_svc._on_close = unschedule_bot_monitoring  # noqa: SLF001
    scheduler.start()

    await bot.set_my_commands([
        BotCommand(command="status", description="Show bot health status"),
        BotCommand(command="pause", description="Pause a bot (e.g. /pause BTC_USDT_PERP)"),
        BotCommand(command="resume", description="Resume a paused bot"),
        BotCommand(command="close", description="Close a bot via API"),
        BotCommand(command="reconfigure", description="Re-evaluate grid parameters"),
        BotCommand(command="settings", description="Show monitoring settings"),
        BotCommand(command="weekly_assessment", description="Run a full three-gate assessment"),
        BotCommand(command="daily_assessment", description="Run a daily second gate assessment"),
        BotCommand(command="verdict", description="Show the most recent stored verdict"),
        BotCommand(command="help", description="Show available commands"),
    ])

    logger.info("Starting grid bot monitor…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

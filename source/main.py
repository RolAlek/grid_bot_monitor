import asyncio

import structlog
from aiogram import Dispatcher
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from source.dependencies import (
    get_daily_runner,
    get_decision_service,
    get_launch_service,
    get_telegram_bot,
    get_weekly_runner,
)
from source.presentation.bot.handlers.common_handlers import common_router
from source.presentation.bot.handlers.decision_handlers import decision_router
from source.presentation.bot.handlers.launch_grid_handlers import grid_router
from source.presentation.scheduler.jobs import register_jobs
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

    scheduler = AsyncIOScheduler()
    register_jobs(scheduler, daily_runner=get_daily_runner(), weekly_runner=get_weekly_runner())
    scheduler.start()

    await bot.set_my_commands([
        BotCommand(command="weekly_assessment", description="Run a full three-gate assessment"),
        BotCommand(command="daily_assessment", description="Run a daily second gate assessment"),
        BotCommand(command="verdict", description="Show the most recent stored verdict"),
        BotCommand(command="help", description="Show available commands"),
    ])

    logger.info("Starting grid bot monitor…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

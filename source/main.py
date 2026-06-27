import asyncio

import structlog
from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from source.dependencies import get_daily_runner, get_decision_service, get_telegram_bot, get_weekly_runner
from source.logging_config import configure_logging
from source.presentation.bot.handlers.common_handlers import common_router
from source.presentation.bot.handlers.decision_handlers import router_factory
from source.presentation.scheduler.jobs import register_jobs
from source.settings import get_settings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.app)

    bot = get_telegram_bot()
    dp = Dispatcher()
    dp.include_router(common_router())
    dp.include_router(
        router_factory(
            weekly_runner=get_weekly_runner(),
            decision_service=get_decision_service(),
            symbol=settings.pionex.symbol,
        )
    )

    scheduler = AsyncIOScheduler()
    register_jobs(scheduler, daily_runner=get_daily_runner(), weekly_runner=get_weekly_runner())
    scheduler.start()

    logger.info("Starting grid bot monitor…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

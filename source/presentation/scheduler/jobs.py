import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from source.application.services.run_daily_positioning_check import RunDailyPositioningCheck
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.value_objects import Symbol


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def register_jobs(  # type: ignore[no-any-unimported]
    scheduler: AsyncIOScheduler,
    daily_runner: RunDailyPositioningCheck,
    weekly_runner: RunWeeklyFullAssessment,
) -> None:
    scheduler.add_job(
        _run_daily,
        trigger=CronTrigger(hour=0, minute=5, timezone="UTC"),
        args=[daily_runner],
        id="daily_positioning_check",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_weekly,
        trigger=CronTrigger(day_of_week="sat", hour=9, minute=0, timezone="UTC"),
        args=[weekly_runner],
        id="weekly_full_assessment",
        replace_existing=True,
    )
    logger.info("Scheduled daily positioning check (00:05 UTC) and weekly assessment (Sat 09:00 UTC)")


async def _run_daily(runner: RunDailyPositioningCheck) -> None:
    try:
        for symbol in Symbol:
            await runner.run(symbol)
    except Exception:
        logger.exception("Daily positioning check failed")


async def _run_weekly(runner: RunWeeklyFullAssessment) -> None:
    try:
        for symbol in Symbol:
            await runner.run(symbol)
    except Exception:
        logger.exception("Weekly full assessment failed")

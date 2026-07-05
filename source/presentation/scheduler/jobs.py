import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from source.application.services.auto_adjust_service import AutoAdjustService
from source.application.services.health_monitor_service import HealthMonitorService
from source.application.services.run_daily_positioning_check import RunDailyPositioningCheck
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.value_objects import Symbol
from source.settings import MonitoringSettings


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


def register_monitor_jobs(  # type: ignore[no-any-unimported]
    scheduler: AsyncIOScheduler,
    monitor_service: HealthMonitorService,
    auto_adjust_service: AutoAdjustService,
    settings: MonitoringSettings,
) -> None:
    scheduler.add_job(
        _run_health_check,
        trigger=IntervalTrigger(minutes=settings.intervals.health_check_minutes),
        args=[monitor_service],
        id="health_check",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_auto_adjust,
        trigger=IntervalTrigger(minutes=settings.intervals.auto_adjust_minutes),
        args=[auto_adjust_service],
        id="auto_adjust",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_cleanup,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        args=[monitor_service, settings],
        id="metrics_cleanup",
        replace_existing=True,
    )
    logger.info(
        "Scheduled monitor jobs",
        health_check_min=settings.intervals.health_check_minutes,
        auto_adjust_min=settings.intervals.auto_adjust_minutes,
    )


async def _run_health_check(monitor_service: HealthMonitorService) -> None:
    try:
        await monitor_service.run_all_checks()
    except Exception:
        logger.exception("Health check job failed")


async def _run_auto_adjust(auto_adjust_service: AutoAdjustService) -> None:
    try:
        await auto_adjust_service.evaluate_all()
    except Exception:
        logger.exception("Auto-adjust job failed")


async def _run_cleanup(monitor_service: HealthMonitorService, settings: MonitoringSettings) -> None:
    try:
        deleted = await monitor_service.cleanup_old_snapshots(settings.intervals.metrics_ttl_days)
        logger.info("Snapshot cleanup complete", deleted_rows=deleted)
    except Exception:
        logger.exception("Snapshot cleanup job failed")

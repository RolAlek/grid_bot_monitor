import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from source.application.services.health_monitor_service import HealthMonitorService
from source.settings import MonitoringSettings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def register_cleanup_job(  # type: ignore[no-any-unimported]
    scheduler: AsyncIOScheduler,
    monitor_service: HealthMonitorService,
    settings: MonitoringSettings,
) -> None:
    scheduler.add_job(
        _run_cleanup,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        args=[monitor_service, settings],
        id="metrics_cleanup",
        replace_existing=True,
    )
    logger.info("Scheduled metrics cleanup (daily 03:00 UTC)")


async def _run_cleanup(monitor_service: HealthMonitorService, settings: MonitoringSettings) -> None:
    try:
        deleted = await monitor_service.cleanup_old_snapshots(settings.intervals.metrics_ttl_days)
        logger.info("Snapshot cleanup complete", deleted_rows=deleted)
    except Exception:
        logger.exception("Snapshot cleanup job failed")

import structlog
from apscheduler.triggers.interval import IntervalTrigger

from source.application.services.auto_adjust_service import AutoAdjustService
from source.application.services.health_monitor_service import HealthMonitorService
from source.dependencies import get_auto_adjust_service, get_health_monitor_service, get_scheduler
from source.domain.value_objects import Symbol


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_HC_PREFIX = "hc_"
_AA_PREFIX = "aa_"
_HC_MINUTES = 30
_AA_MINUTES = 60


def schedule_bot_monitoring(symbol: Symbol) -> None:
    scheduler = get_scheduler()
    hc_id = f"{_HC_PREFIX}{symbol.value}"
    aa_id = f"{_AA_PREFIX}{symbol.value}"

    scheduler.add_job(
        _run_single_health_check,
        trigger=IntervalTrigger(minutes=_HC_MINUTES),
        args=[get_health_monitor_service(), symbol],
        id=hc_id,
        replace_existing=True,
    )
    scheduler.add_job(
        _run_single_auto_adjust,
        trigger=IntervalTrigger(minutes=_AA_MINUTES),
        args=[get_auto_adjust_service(), symbol],
        id=aa_id,
        replace_existing=True,
    )
    logger.info("Scheduled per-bot monitoring", symbol=symbol.value, hc_id=hc_id, aa_id=aa_id)


def unschedule_bot_monitoring(symbol: Symbol) -> None:
    scheduler = get_scheduler()
    for prefix in (_HC_PREFIX, _AA_PREFIX):
        job_id = f"{prefix}{symbol.value}"
        try:
            scheduler.remove_job(job_id)
            logger.info("Removed per-bot job", job_id=job_id)
        except Exception:
            logger.debug("Job already removed or never existed", job_id=job_id)


async def _run_single_health_check(
    monitor_service: HealthMonitorService,
    symbol: Symbol,
) -> None:
    try:
        await monitor_service.check_single_bot_by_symbol(symbol)
    except Exception:
        logger.exception("Health check failed", symbol=symbol.value)


async def _run_single_auto_adjust(
    auto_adjust_service: AutoAdjustService,
    symbol: Symbol,
) -> None:
    try:
        await auto_adjust_service.evaluate_one(symbol)
    except Exception:
        logger.exception("Auto-adjust failed", symbol=symbol.value)

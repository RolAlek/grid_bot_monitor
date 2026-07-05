import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

import structlog

from source.application.ports import Notifier
from source.domain.entities.monitoring import Alert, Bot, ClassificationResult
from source.domain.value_objects import HealthStatus
from source.infrastructure.database.repositories.base import AbstractRepository
from source.settings import MonitoringSettings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AlertService:
    """Debounced health alerts: deduplicate, send via Notifier, persist Alert to DB."""

    def __init__(
        self,
        notifier: Notifier,
        alert_repo_factory: Callable[[], AbstractAsyncContextManager[AbstractRepository[Alert]]],
        monitoring_settings: MonitoringSettings,
    ) -> None:
        self._notifier = notifier
        self._alert_repo_factory = alert_repo_factory
        self._debounce_minutes = monitoring_settings.intervals.alert_debounce_minutes

        # In-memory debounce cache: {(bot_oid_hex, alert_type_value): monotonic_timestamp}
        self._sent: dict[tuple[str, str], float] = {}

    async def send_health_alert(
        self,
        bot: Bot,
        previous_status: HealthStatus,
        result: ClassificationResult,
    ) -> None:
        if bot.oid is None:
            logger.warning("Cannot send health alert — bot has no oid", symbol=str(bot.symbol))
            return

        # Check which alert types are NOT debounced
        now = time.monotonic()
        debounce_secs = self._debounce_minutes * 60
        bot_key = bot.oid.hex

        fresh_alerts = [at for at in result.alerts if now - self._sent.get((bot_key, at.value), 0.0) >= debounce_secs]

        if not fresh_alerts:
            logger.debug("All alert types debounced", bot_oid=bot_key, alerts=[a.value for a in result.alerts])
            return

        # Send one message with all fresh alert types (notifier handles formatting + keyboard)
        await self._notifier.send_health_alert(bot, previous_status, result)

        # Persist one Alert per fresh alert type
        for alert_type in fresh_alerts:
            alert = Alert(
                grid_launch_oid=bot.oid,
                symbol=bot.symbol,
                alert_type=alert_type,
                severity=result.status,
                message=f"Health status: {previous_status.value} → {result.status.value} "
                f"(score: {result.score:.0%}) — {alert_type.value}",
            )
            async with self._alert_repo_factory() as repo:
                await repo.add(alert)

            # Update debounce cache
            self._sent[bot_key, alert_type.value] = now

        logger.info(
            "Health alert sent",
            bot_oid=bot_key,
            symbol=str(bot.symbol),
            previous=previous_status.value,
            current=result.status.value,
            fired_alerts=[a.value for a in fresh_alerts],
        )

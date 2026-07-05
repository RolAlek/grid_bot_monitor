import time
from collections.abc import AsyncIterable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from source.application.ports import Notifier
from source.application.services.alert_service import AlertService
from source.domain.entities.monitoring import Alert, Bot, ClassificationResult
from source.domain.value_objects import AlertType, HealthStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.settings import MonitoringIntervals, MonitoringSettings


def _make_bot(oid: str | None = None) -> Bot:
    return Bot(
        symbol=Symbol.BTC,
        oid=oid or uuid4(),
        health_status=HealthStatus.GREEN,
    )


def _make_classification(
    status: HealthStatus = HealthStatus.YELLOW,
    alerts: tuple[AlertType, ...] = (AlertType.VOLATILITY_SPIKE,),
) -> ClassificationResult:
    return ClassificationResult(
        status=status,
        score=0.65,
        alerts=alerts,
        details={},
    )


def _make_settings(debounce_minutes: int = 5) -> MonitoringSettings:
    return MonitoringSettings(intervals=MonitoringIntervals(alert_debounce_minutes=debounce_minutes))


def _mock_notifier() -> MagicMock:
    n = MagicMock(spec=Notifier)
    n.send_health_alert = AsyncMock()
    return n


def _mock_alert_repo_factory() -> Callable[[], AbstractAsyncContextManager[AbstractRepository[Alert]]]:
    repo = MagicMock(spec=AbstractRepository)
    repo.add = AsyncMock()

    @asynccontextmanager
    async def factory() -> AsyncIterable[AbstractRepository[Alert]]:
        yield repo  # type: ignore[misc]

    return factory


def _make_service(
    notifier: MagicMock | None = None,
    debounce_minutes: int = 5,
) -> AlertService:
    settings = MonitoringSettings(intervals=MonitoringIntervals(alert_debounce_minutes=debounce_minutes))
    return AlertService(
        notifier=notifier or _mock_notifier(),
        alert_repo_factory=_mock_alert_repo_factory(),
        monitoring_settings=settings,
    )


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSendHealthAlert:
    async def test_sends_via_notifier(self) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier)

        bot = _make_bot()
        result = _make_classification()
        await svc.send_health_alert(bot, HealthStatus.GREEN, result)

        notifier.send_health_alert.assert_called_once_with(bot, HealthStatus.GREEN, result)

    async def test_persists_alert_to_repo(self) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier)

        bot = _make_bot()
        result = _make_classification(alerts=(AlertType.LIQUIDATION_RISK,))
        await svc.send_health_alert(bot, HealthStatus.GREEN, result)

        notifier.send_health_alert.assert_called_once()

    async def test_skips_when_bot_has_no_oid(self) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier)

        bot = _make_bot()
        bot.oid = None
        await svc.send_health_alert(bot, HealthStatus.GREEN, _make_classification())

        notifier.send_health_alert.assert_not_called()

    async def test_multiple_alert_types_one_notifier_call(self) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier)

        result = _make_classification(
            alerts=(AlertType.VOLATILITY_SPIKE, AlertType.GRID_DEPLETION),
        )
        await svc.send_health_alert(_make_bot(), HealthStatus.GREEN, result)
        notifier.send_health_alert.assert_called_once()


class TestDebounce:
    async def test_skips_within_window(self) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier, debounce_minutes=5)

        bot = _make_bot()
        result = _make_classification()

        await svc.send_health_alert(bot, HealthStatus.GREEN, result)
        assert notifier.send_health_alert.call_count == 1

        await svc.send_health_alert(bot, HealthStatus.GREEN, result)
        assert notifier.send_health_alert.call_count == 1  # debounced

    async def test_allows_after_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier, debounce_minutes=5)

        bot = _make_bot()
        result = _make_classification()

        await svc.send_health_alert(bot, HealthStatus.GREEN, result)
        assert notifier.send_health_alert.call_count == 1

        original = time.monotonic
        monkeypatch.setattr(time, "monotonic", lambda: original() + 6 * 60)
        await svc.send_health_alert(bot, HealthStatus.GREEN, result)
        assert notifier.send_health_alert.call_count == 2

    async def test_different_types_not_debounced(self) -> None:
        notifier = _mock_notifier()
        svc = _make_service(notifier=notifier, debounce_minutes=5)

        bot = _make_bot()
        await svc.send_health_alert(
            bot,
            HealthStatus.GREEN,
            _make_classification(alerts=(AlertType.VOLATILITY_SPIKE,)),
        )
        await svc.send_health_alert(
            bot,
            HealthStatus.GREEN,
            _make_classification(alerts=(AlertType.LIQUIDATION_RISK,)),
        )
        assert notifier.send_health_alert.call_count == 2

        # Different alert type — should NOT be debounced
        result2 = _make_classification(alerts=(AlertType.LIQUIDATION_RISK,))
        await svc.send_health_alert(bot, HealthStatus.GREEN, result2)
        assert notifier.send_health_alert.call_count == 2

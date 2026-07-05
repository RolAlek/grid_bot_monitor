from collections.abc import AsyncIterable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from source.application.ports import Notifier
from source.application.services.auto_adjust_service import AutoAdjustService
from source.application.services.bot_management_service import BotManagementService
from source.domain.entities.monitoring import Bot, HealthSnapshot
from source.domain.value_objects import ActionType, HealthStatus, Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.settings import MonitoringIntervals, MonitoringSettings


def _make_bot(
    health_status: HealthStatus = HealthStatus.GREEN,
    paused: bool = False,
) -> Bot:
    return Bot(
        symbol=Symbol.BTC,
        oid=uuid4(),
        health_status=health_status,
        paused_by_monitor=paused,
    )


def _mock_repo_factory(bot: Bot | None = None) -> Callable[[], AbstractAsyncContextManager[AbstractRepository[Bot]]]:
    repo = MagicMock(spec=AbstractRepository)
    repo.get_list = AsyncMock(return_value=[bot] if bot else [])
    repo.get_one = AsyncMock(return_value=bot)

    @asynccontextmanager
    async def factory() -> AsyncIterable[AbstractRepository[Bot]]:
        yield repo  # type: ignore[misc]

    return factory


def _mock_snapshot_repo_factory(
    snapshots: list[HealthSnapshot] | None = None,
) -> Callable[[], AbstractAsyncContextManager[AbstractRepository[HealthSnapshot]]]:
    repo = MagicMock(spec=AbstractRepository)
    repo.get_list = AsyncMock(return_value=snapshots or [])

    @asynccontextmanager
    async def factory() -> AsyncIterable[AbstractRepository[HealthSnapshot]]:
        yield repo  # type: ignore[misc]

    return factory


def _settings(**overrides: object) -> MonitoringSettings:
    return MonitoringSettings(
        intervals=MonitoringIntervals(),
        auto_adjust_enabled=overrides.get("auto_adjust_enabled", True),  # type: ignore[arg-type]
        auto_pause_on_red=overrides.get("auto_pause_on_red", True),  # type: ignore[arg-type]
        max_consecutive_yellow_before_action=overrides.get("max_consecutive_yellow_before_action", 4),  # type: ignore[arg-type]
    )


def _make_yellow_snapshot(health_status: HealthStatus = HealthStatus.YELLOW) -> HealthSnapshot:
    return HealthSnapshot(
        grid_launch_oid=uuid4(),
        symbol=Symbol.BTC,
        created_at=datetime.now(UTC),
        last_price=96_000.0,
        leverage=3,
        adx14=20.0,
        atr14=1_000.0,
        atr_pct_of_price=1.0,
        rsi14=55.0,
        realized_vol_1d=0.02,
        realized_vol_7d=0.015,
        unrealized_pnl=150.0,
        grid_fill_ratio=0.45,
        distance_to_liquidation_pct=25.0,
        funding_rate_annualized_pct=5.0,
        health_status=health_status,
        health_score=0.6,
    )


class TestRedAutoPause:
    async def test_red_triggers_auto_pause(self) -> None:
        bot_mgmt = MagicMock(spec=BotManagementService)
        bot_mgmt.pause_bot = AsyncMock(return_value=True)
        notifier = MagicMock(spec=Notifier)
        notifier.send_health_alert = AsyncMock()

        bot = _make_bot(health_status=HealthStatus.RED)
        svc = AutoAdjustService(
            settings=_settings(),
            bot_management=bot_mgmt,
            notifier=notifier,
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.PAUSE
        bot_mgmt.pause_bot.assert_called_once_with(Symbol.BTC)
        notifier.send_health_alert.assert_called_once()

    async def test_disabled_when_auto_adjust_off(self) -> None:
        bot_mgmt = MagicMock(spec=BotManagementService)
        notifier = MagicMock(spec=Notifier)

        bot = _make_bot(health_status=HealthStatus.RED)
        svc = AutoAdjustService(
            settings=_settings(auto_adjust_enabled=False),
            bot_management=bot_mgmt,
            notifier=notifier,
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.NONE
        bot_mgmt.pause_bot.assert_not_called()

    async def test_skips_already_paused(self) -> None:
        bot_mgmt = MagicMock(spec=BotManagementService)

        bot = _make_bot(health_status=HealthStatus.RED, paused=True)
        svc = AutoAdjustService(
            settings=_settings(),
            bot_management=bot_mgmt,
            notifier=MagicMock(spec=Notifier),
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.NONE
        bot_mgmt.pause_bot.assert_not_called()


class TestYellowConsecutive:
    async def test_yellow_consecutive_triggers_notification(self) -> None:
        notifier = MagicMock(spec=Notifier)
        notifier.send_health_alert = AsyncMock()

        bot = _make_bot(health_status=HealthStatus.YELLOW)
        yellow_snapshots = [_make_yellow_snapshot() for _ in range(4)]
        svc = AutoAdjustService(
            settings=_settings(),
            bot_management=MagicMock(spec=BotManagementService),
            notifier=notifier,
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(yellow_snapshots),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.RECONFIGURE
        notifier.send_health_alert.assert_called_once()

    async def test_yellow_below_threshold_no_action(self) -> None:
        notifier = MagicMock(spec=Notifier)

        bot = _make_bot(health_status=HealthStatus.YELLOW)
        yellow_snapshots = [_make_yellow_snapshot() for _ in range(2)]  # only 2
        svc = AutoAdjustService(
            settings=_settings(),
            bot_management=MagicMock(spec=BotManagementService),
            notifier=notifier,
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(yellow_snapshots),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.NONE

    async def test_consecutive_resets_on_non_yellow(self) -> None:
        notifier = MagicMock(spec=Notifier)

        bot = _make_bot(health_status=HealthStatus.YELLOW)
        snapshots = [
            _make_yellow_snapshot(HealthStatus.YELLOW),
            _make_yellow_snapshot(HealthStatus.GREEN),  # breaks chain
            _make_yellow_snapshot(HealthStatus.YELLOW),
        ]
        svc = AutoAdjustService(
            settings=_settings(),
            bot_management=MagicMock(spec=BotManagementService),
            notifier=notifier,
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(snapshots),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.NONE


class TestGreenNoAction:
    async def test_green_no_action(self) -> None:
        bot_mgmt = MagicMock(spec=BotManagementService)

        bot = _make_bot(health_status=HealthStatus.GREEN)
        svc = AutoAdjustService(
            settings=_settings(),
            bot_management=bot_mgmt,
            notifier=MagicMock(spec=Notifier),
            bot_repo_factory=_mock_repo_factory(),
            health_snapshot_repo_factory=_mock_snapshot_repo_factory(),
        )

        result = await svc.evaluate_and_act(bot)
        assert result == ActionType.NONE

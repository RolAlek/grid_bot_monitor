from unittest.mock import AsyncMock, MagicMock

import pytest

from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.application.services.run_daily_positioning_check import RunDailyPositioningCheck
from source.domain.entities import GateResult
from source.domain.value_objects import Gate, GateStatus, Symbol
from source.settings import DecisionEngineSettings, PionexSettings, Settings


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock(spec=Settings)
    settings.pionex = MagicMock(spec=PionexSettings)
    settings.pionex.symbol = Symbol.BTC
    settings.decision_engine = DecisionEngineSettings()
    return settings


@pytest.fixture
def pass_gate2() -> GateResult:
    return GateResult(
        gate=Gate.POSITIONING,
        status=GateStatus.PASS,
        reasons=(),
        raw_values={"funding_rate_annualized_pct": 5.0, "oi_pct_change_7d": 5.0},
    )


@pytest.fixture
def mock_gate2(pass_gate2: GateResult) -> AsyncMock:
    mock = AsyncMock(spec=AssessPositioningService)
    mock.execute.return_value = pass_gate2
    return mock


@pytest.fixture
def mock_decision_service() -> AsyncMock:
    mock = AsyncMock()
    mock.persist_verdict = AsyncMock()
    mock.get_last_decision = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_notifier() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def daily_runner(
    mock_gate2: AsyncMock,
    mock_decision_service: AsyncMock,
    mock_notifier: AsyncMock,
    mock_settings: MagicMock,
) -> RunDailyPositioningCheck:
    return RunDailyPositioningCheck(
        second_gate=mock_gate2,
        decision_service=mock_decision_service,
        notifier=mock_notifier,
        settings=mock_settings,
    )


async def test_daily_run_calls_gate2_only(daily_runner: RunDailyPositioningCheck, mock_gate2: AsyncMock) -> None:
    await daily_runner.run(Symbol.BTC)
    mock_gate2.execute.assert_called_once_with(Symbol.BTC)


async def test_daily_sends_alert_on_first_run(
    daily_runner: RunDailyPositioningCheck,
    mock_notifier: AsyncMock,
    mock_decision_service: AsyncMock,
) -> None:
    mock_decision_service.get_last_decision.return_value = None
    await daily_runner.run(Symbol.BTC)
    mock_notifier.send_alert.assert_called_once()


async def test_daily_no_alert_when_status_unchanged(
    daily_runner: RunDailyPositioningCheck,
    mock_notifier: AsyncMock,
    mock_gate2: AsyncMock,  # noqa: ARG001
    mock_decision_service: AsyncMock,
    pass_gate2: GateResult,
) -> None:

    prev_verdict = MagicMock()
    prev_verdict.gates = (pass_gate2,)
    mock_decision_service.get_last_decision.return_value = prev_verdict

    await daily_runner.run(Symbol.BTC)
    mock_notifier.send_alert.assert_not_called()


async def test_daily_persists_verdict(daily_runner: RunDailyPositioningCheck, mock_decision_service: AsyncMock) -> None:
    await daily_runner.run(Symbol.BTC)
    mock_decision_service.persist_verdict.assert_called_once()

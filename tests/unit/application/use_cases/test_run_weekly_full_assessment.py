from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.application.services.gates.assess_liquidation_safety_third_gate import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.entities import GateResult, ProposedGridParams
from source.domain.value_objects import Gate, GateStatus, GridType, Symbol, Trend
from source.settings import DecisionEngineSettings, PionexSettings, Settings


NOW = datetime(2026, 6, 19, tzinfo=UTC)

_PROPOSAL = ProposedGridParams(
    symbol=Symbol.BTC,
    top=100_000.0,
    bottom=88_000.0,
    grid_levels=50,
    leverage=1,
    quote_investment=1_000.0,
    trend=Trend.NEUTRAL,
    grid_type=GridType.GEOMETRIC,
)


def _gate_result(gate: Gate, status: GateStatus) -> GateResult:
    return GateResult(gate=gate, status=status, reasons=(), raw_values={})


def _runner() -> RunWeeklyFullAssessment:
    return RunWeeklyFullAssessment(
        decision_service=MagicMock(),
        gate1=MagicMock(),
        gate2=MagicMock(),
        gate3=MagicMock(),
        notifier=MagicMock(),
        settings=MagicMock(spec=Settings),
    )


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock(spec=Settings)
    settings.pionex = MagicMock(spec=PionexSettings)
    settings.pionex.symbol = Symbol.BTC
    settings.decision_engine = DecisionEngineSettings()
    return settings


@pytest.fixture
def proposal() -> ProposedGridParams:
    return ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=1,
        quote_investment=1_000.0,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
    )


@pytest.fixture
def pass_gate1(proposal: ProposedGridParams) -> tuple[GateResult, ProposedGridParams]:
    result = GateResult(gate=Gate.REGIME_RANGE_FIT, status=GateStatus.PASS, reasons=(), raw_values={})
    return result, proposal


@pytest.fixture
def pass_gate2() -> GateResult:
    return GateResult(
        gate=Gate.POSITIONING,
        status=GateStatus.PASS,
        reasons=(),
        raw_values={"funding_rate_annualized_pct": 5.0, "oi_pct_change_7d": 5.0},
    )


@pytest.fixture
def pass_gate3() -> GateResult:
    return GateResult(gate=Gate.LIQUIDATION_SAFETY, status=GateStatus.PASS, reasons=(), raw_values={})


@pytest.fixture
def mock_gate1(pass_gate1: tuple[GateResult, ProposedGridParams]) -> AsyncMock:
    mock = AsyncMock(spec=AssessMarketRegimeService)
    mock.execute.return_value = pass_gate1
    return mock


@pytest.fixture
def mock_gate2(pass_gate2: GateResult) -> AsyncMock:
    mock = AsyncMock(spec=AssessPositioningService)
    mock.execute.return_value = pass_gate2
    return mock


@pytest.fixture
def mock_gate3(pass_gate3: GateResult) -> AsyncMock:
    mock = AsyncMock(spec=AssessLiquidationSafetyService)
    mock.execute.return_value = pass_gate3
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
def weekly_runner(
    mock_gate1: AsyncMock,
    mock_gate2: AsyncMock,
    mock_gate3: AsyncMock,
    mock_decision_service: AsyncMock,
    mock_notifier: AsyncMock,
    mock_settings: MagicMock,
) -> RunWeeklyFullAssessment:
    return RunWeeklyFullAssessment(
        decision_service=mock_decision_service,
        gate1=mock_gate1,
        gate2=mock_gate2,
        gate3=mock_gate3,
        notifier=mock_notifier,
        settings=mock_settings,
    )


async def test_weekly_run_calls_all_three_gates(
    weekly_runner: RunWeeklyFullAssessment,
    mock_gate1: AsyncMock,
    mock_gate2: AsyncMock,
    mock_gate3: AsyncMock,
) -> None:
    await weekly_runner.run()
    mock_gate1.execute.assert_called_once_with(Symbol.BTC)
    mock_gate2.execute.assert_called_once_with(Symbol.BTC)
    mock_gate3.execute.assert_called_once()


async def test_weekly_always_sends_digest(
    weekly_runner: RunWeeklyFullAssessment,
    mock_notifier: AsyncMock,
) -> None:
    await weekly_runner.run()
    mock_notifier.send_digest.assert_called_once()


async def test_weekly_persists_verdict_exactly_once(
    weekly_runner: RunWeeklyFullAssessment,
    mock_decision_service: AsyncMock,
) -> None:
    await weekly_runner.run()
    mock_decision_service.persist_verdict.assert_called_once()


async def test_weekly_skips_gate2_and_gate3_when_gate1_fails(
    mock_gate1: AsyncMock,
    mock_gate2: AsyncMock,
    mock_gate3: AsyncMock,
    mock_decision_service: AsyncMock,
    mock_notifier: AsyncMock,
    mock_settings: MagicMock,
    proposal: ProposedGridParams,
) -> None:
    fail_result = GateResult(
        gate=Gate.REGIME_RANGE_FIT,
        status=GateStatus.FAIL,
        reasons=("adx too high",),
        raw_values={},
    )
    mock_gate1.execute.return_value = (fail_result, proposal)

    runner = RunWeeklyFullAssessment(
        decision_service=mock_decision_service,
        gate1=mock_gate1,
        gate2=mock_gate2,
        gate3=mock_gate3,
        notifier=mock_notifier,
        settings=mock_settings,
    )
    await runner.run()
    mock_gate2.execute.assert_not_called()
    mock_gate3.execute.assert_not_called()


async def test_weekly_digest_still_sent_on_hold(
    mock_gate1: AsyncMock,
    mock_gate2: AsyncMock,
    mock_gate3: AsyncMock,
    mock_decision_service: AsyncMock,
    mock_notifier: AsyncMock,
    mock_settings: MagicMock,
    pass_gate1: tuple[GateResult, ProposedGridParams],
) -> None:
    fail_gate2 = GateResult(
        gate=Gate.POSITIONING,
        status=GateStatus.FAIL,
        reasons=("funding high",),
        raw_values={"funding_rate_annualized_pct": 45.0, "oi_pct_change_7d": 5.0},
    )
    mock_gate1.execute.return_value = pass_gate1
    mock_gate2.execute.return_value = fail_gate2

    runner = RunWeeklyFullAssessment(
        decision_service=mock_decision_service,
        gate1=mock_gate1,
        gate2=mock_gate2,
        gate3=mock_gate3,
        notifier=mock_notifier,
        settings=mock_settings,
    )
    await runner.run()
    mock_notifier.send_digest.assert_called_once()

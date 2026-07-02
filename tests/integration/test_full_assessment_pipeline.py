from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.gates.assess_liquidation_safety_third_gate import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.application.services.grid_builder import GridProposalBuilder
from source.application.services.indicator_service import IndicatorService
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingOiSnapshot,
    FundingRate,
    GateResult,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
)
from source.domain.value_objects import Gate, GateStatus, Symbol, VerdictAction
from source.settings import DecisionEngineSettings
from tests.fixtures.factories import FIXED_NOW, make_proposed_grid_params
from tests.fixtures.fakes import FakeDecisionLogRepository


class FakeMarketData:
    def __init__(
        self,
        candles: list[Candle],
        funding_rate: float = 0.0001,
        open_interest: float = 5_000_000.0,
    ) -> None:
        self._candles = candles
        self._funding_rate = funding_rate
        self._open_interest = open_interest

    async def get_candles(self, symbol: Symbol, interval: str, limit: int) -> list[Candle]:  # noqa: ARG002
        return self._candles

    async def get_funding_rates(self, symbol: Symbol, limit: int) -> list[FundingRate]:  # noqa: ARG002
        return [FundingRate(rate=self._funding_rate, time=FIXED_NOW)]

    async def get_open_interest(self, symbol: Symbol) -> OpenInterest:
        return OpenInterest(symbol=symbol, open_interest=self._open_interest)


class FakeGridValidation:
    def __init__(self, estimate: LiquidationEstimate) -> None:
        self._estimate = estimate
        self.call_count = 0

    async def check_grid_params(self, params: ProposedGridParams) -> LiquidationEstimate:  # noqa: ARG002
        self.call_count += 1
        return self._estimate


class FakeNotifier:
    def __init__(self) -> None:
        self.sent_digests: list[DecisionVerdict] = []
        self.sent_alerts: list[GateResult] = []

    async def send_alert(self, result: GateResult, prev_status: GateStatus | None) -> None:  # noqa: ARG002
        self.sent_alerts.append(result)

    async def send_digest(self, verdict: DecisionVerdict) -> None:
        self.sent_digests.append(verdict)


class FakeSnapshotRepository:
    async def save_snapshot(self, snapshot: FundingOiSnapshot) -> None:
        pass

    async def get_oi_snapshots_last_7d(self, symbol: Symbol, as_of: datetime) -> list[FundingOiSnapshot]:  # noqa: ARG002
        return []  # return empty → OI change will be None (≤ 2 snapshots)


def _make_settings() -> MagicMock:  # type: ignore[type-arg]
    settings = MagicMock()
    settings.pionex.symbol = Symbol.BTC
    settings.pionex.kline_interval = "4H"
    settings.pionex.limit = 500
    settings.decision_engine = DecisionEngineSettings()
    return settings


def _make_decision_service() -> tuple[DecisionLogService, FakeDecisionLogRepository]:
    repo = FakeDecisionLogRepository()

    @asynccontextmanager
    async def provider() -> AsyncGenerator[FakeDecisionLogRepository, None]:
        yield repo

    return DecisionLogService(provider), repo


def _make_oi_service() -> OISnapshotService:
    repo = FakeSnapshotRepository()

    @asynccontextmanager
    async def provider() -> AsyncGenerator[FakeSnapshotRepository, None]:
        yield repo

    return OISnapshotService(provider)


def _make_pipeline(
    candles: list[Candle],
    funding_rate: float,
    open_interest: float,
    liquidation_estimate: LiquidationEstimate,
) -> tuple[RunWeeklyFullAssessment, FakeNotifier, FakeGridValidation, FakeDecisionLogRepository]:
    settings = _make_settings()
    decision_service, repo = _make_decision_service()
    oi_service = _make_oi_service()
    market_data = FakeMarketData(candles, funding_rate=funding_rate, open_interest=open_interest)
    grid_validation = FakeGridValidation(liquidation_estimate)
    notifier = FakeNotifier()

    indicator_service = IndicatorService()
    grid_builder = GridProposalBuilder(settings.decision_engine)

    gate1 = AssessMarketRegimeService(settings, market_data, indicator_service, grid_builder)
    gate2 = AssessPositioningService(settings.decision_engine, market_data, oi_service)
    gate3 = AssessLiquidationSafetyService(settings.decision_engine, grid_validation)

    runner = RunWeeklyFullAssessment(
        decision_service=decision_service,
        gate1=gate1,
        gate2=gate2,
        gate3=gate3,
        notifier=notifier,
        settings=settings,
    )
    return runner, notifier, grid_validation, repo


async def test_launch_path_all_gates_pass() -> None:
    settings = _make_settings()
    decision_service, repo = _make_decision_service()
    notifier = FakeNotifier()

    proposal = make_proposed_grid_params(top=100_000.0, bottom=88_000.0, leverage=1)
    gate1_pass = GateResult(gate=Gate.REGIME_RANGE_FIT, status=GateStatus.PASS, reasons=(), raw_values={})
    gate2_pass = GateResult(gate=Gate.POSITIONING, status=GateStatus.PASS, reasons=(), raw_values={})
    gate3_pass = GateResult(gate=Gate.LIQUIDATION_SAFETY, status=GateStatus.PASS, reasons=(), raw_values={})

    gate1 = MagicMock(spec=AssessMarketRegimeService)
    gate1.execute = AsyncMock(return_value=(gate1_pass, proposal))

    gate2 = MagicMock(spec=AssessPositioningService)
    gate2.execute = AsyncMock(return_value=gate2_pass)

    gate3 = MagicMock(spec=AssessLiquidationSafetyService)
    gate3.execute = AsyncMock(return_value=gate3_pass)

    runner = RunWeeklyFullAssessment(
        decision_service=decision_service,
        gate1=gate1,
        gate2=gate2,
        gate3=gate3,
        notifier=notifier,
        settings=settings,
    )
    verdict = await runner.run()

    assert verdict.action == VerdictAction.LAUNCH
    assert gate1.execute.call_count == 1
    assert gate2.execute.call_count == 1
    assert gate3.execute.call_count == 1
    assert len(notifier.sent_digests) == 1
    assert len(repo._saved) == 1  # noqa: SLF001
    assert repo._saved[0] is verdict  # noqa: SLF001
    assert len(verdict.gates) == 3


async def test_hold_path_gate1_fail_short_circuits() -> None:
    settings = _make_settings()
    decision_service, _repo = _make_decision_service()
    notifier = FakeNotifier()

    proposal = make_proposed_grid_params()
    liq_estimate = LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=None,
    )
    grid_validation = FakeGridValidation(liq_estimate)

    gate1_fail_result = GateResult(
        gate=Gate.REGIME_RANGE_FIT,
        status=GateStatus.FAIL,
        reasons=("ADX 35.0 exceeds caution max 30 — strong trend, grid unfavorable",),
        raw_values={"adx14": 35.0},
    )

    gate1 = MagicMock(spec=AssessMarketRegimeService)
    gate1.execute = AsyncMock(return_value=(gate1_fail_result, proposal))

    gate2 = MagicMock(spec=AssessPositioningService)
    gate2.execute = AsyncMock()  # must NOT be called

    gate3 = MagicMock(spec=AssessLiquidationSafetyService)
    gate3.execute = AsyncMock()  # must NOT be called

    runner = RunWeeklyFullAssessment(
        decision_service=decision_service,
        gate1=gate1,
        gate2=gate2,
        gate3=gate3,
        notifier=notifier,
        settings=settings,
    )
    verdict = await runner.run()

    assert verdict.action == VerdictAction.HOLD
    assert gate2.execute.call_count == 0, "Gate 2 must be skipped when Gate 1 FAILs"
    assert gate3.execute.call_count == 0, "Gate 3 must be skipped when Gate 1 FAILs"
    assert grid_validation.call_count == 0, "check_grid_params must not be called when Gate 1 FAILs"
    assert len(notifier.sent_digests) == 1
    assert len(verdict.gates) == 1  # only Gate 1 in the verdict

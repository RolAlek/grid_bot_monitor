from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from source.application.ports import GridPort
from source.application.services.bot_management_service import BotManagementService
from source.application.services.gates.assess_liquidation_safety_third_gate import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.application.services.grid_builder import GridProposalBuilder
from source.application.services.indicator_service import IndicatorService
from source.domain.entities import GateResult, ProposedGridParams
from source.domain.entities.monitoring import Bot
from source.domain.exceptions import BotIntegrityError, BotNotFoundError
from source.domain.value_objects import Gate, GateStatus, GridLaunchStatus, GridType, Symbol, Trend
from source.infrastructure.database.repositories.base import AbstractRepository
from source.settings import DecisionEngineSettings


def _make_bot(
    *,
    symbol: Symbol = Symbol.BTC,
    status: GridLaunchStatus = GridLaunchStatus.RUNNING,
    oid: str | None = None,
    external_id: str | None = "ext-123",
) -> Bot:
    return Bot(
        symbol=symbol,
        oid=oid or uuid4(),
        external_id=external_id,
        status=status,
    )


def _make_proposal(symbol: Symbol = Symbol.BTC) -> ProposedGridParams:
    return ProposedGridParams(
        symbol=symbol,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
        last_price=96_000.0,
    )


def _pass_gate(gate: Gate = Gate.REGIME_RANGE_FIT) -> GateResult:
    return GateResult(gate=gate, status=GateStatus.PASS, reasons=(), raw_values={})


def _fail_gate(gate: Gate = Gate.REGIME_RANGE_FIT) -> GateResult:
    return GateResult(gate=gate, status=GateStatus.FAIL, reasons=("fail reason",), raw_values={})


def _mock_repo_factory(bot: Bot | None = None) -> Callable[[], AbstractAsyncContextManager[AbstractRepository[Bot]]]:
    repo = MagicMock(spec=AbstractRepository)
    repo.get_one = AsyncMock(return_value=bot)
    repo.add = AsyncMock(return_value=bot)

    @asynccontextmanager
    async def factory() -> AsyncGenerator[AbstractRepository[Bot], None]:
        yield repo  # type: ignore[misc]

    return factory


@pytest.fixture
def grid_port() -> MagicMock:
    gp = MagicMock(spec=GridPort)
    gp.cancel_futures_grid = AsyncMock(return_value=True)
    return gp


@pytest.fixture
def settings() -> DecisionEngineSettings:
    return DecisionEngineSettings()


@pytest.fixture
def indicator_service() -> MagicMock:
    return MagicMock(spec=IndicatorService)


@pytest.fixture
def grid_builder(settings: DecisionEngineSettings) -> GridProposalBuilder:
    return GridProposalBuilder(settings)


@pytest.fixture
def gate1_mock() -> MagicMock:
    g = MagicMock(spec=AssessMarketRegimeService)
    g.execute = AsyncMock(return_value=(_pass_gate(Gate.REGIME_RANGE_FIT), _make_proposal()))
    return g


@pytest.fixture
def gate2_mock() -> MagicMock:
    g = MagicMock(spec=AssessPositioningService)
    g.execute = AsyncMock(return_value=_pass_gate(Gate.POSITIONING))
    return g


@pytest.fixture
def gate3_mock() -> MagicMock:
    g = MagicMock(spec=AssessLiquidationSafetyService)
    g.execute = AsyncMock(return_value=_pass_gate(Gate.LIQUIDATION_SAFETY))
    return g


def _make_service(
    grid_port: MagicMock,
    bot: Bot | None,
    indicator_service: MagicMock,
    grid_builder: GridProposalBuilder,
    gate1: MagicMock,
    gate2: MagicMock,
    gate3: MagicMock,
) -> BotManagementService:
    return BotManagementService(
        grid_port=grid_port,
        active_bot_repo_factory=_mock_repo_factory(bot),
        indicator_service=indicator_service,
        grid_builder=grid_builder,
        gate1=gate1,
        gate2=gate2,
        gate3=gate3,
    )


class TestPauseBot:
    async def test_pause_sets_flag_and_status(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        bot = _make_bot(status=GridLaunchStatus.RUNNING)
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        result = await svc.pause_bot(Symbol.BTC)
        assert result is True
        assert bot.paused_by_monitor is True
        assert bot.status == GridLaunchStatus.PAUSED

    async def test_pause_raises_when_no_bot(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        svc = _make_service(grid_port, None, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        with pytest.raises(BotNotFoundError):
            await svc.pause_bot(Symbol.BTC)


class TestResumeBot:
    async def test_resume_clears_flag(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        bot = _make_bot(status=GridLaunchStatus.PAUSED)
        bot.paused_by_monitor = True
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        result = await svc.resume_bot(Symbol.BTC)
        assert result is True
        assert bot.paused_by_monitor is False
        assert bot.status == GridLaunchStatus.RUNNING


class TestCloseBot:
    async def test_close_calls_api_and_updates_status(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        bot = _make_bot(status=GridLaunchStatus.RUNNING)
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        result = await svc.close_bot(Symbol.BTC, reason="manual close")
        assert result is True
        grid_port.cancel_futures_grid.assert_called_once_with("ext-123", close_note="manual close")
        assert bot.status == GridLaunchStatus.CLOSED
        assert bot.closed_at is not None

    async def test_close_raises_when_no_external_id(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        bot = _make_bot(status=GridLaunchStatus.RUNNING, external_id=None)
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        with pytest.raises(BotIntegrityError):
            await svc.close_bot(Symbol.BTC)
        grid_port.cancel_futures_grid.assert_not_called()


class TestReconfigureBot:
    async def test_all_gates_pass_returns_proposal(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        bot = _make_bot()
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        proposal = await svc.reconfigure_bot(Symbol.BTC)
        assert proposal is not None
        assert proposal.symbol == Symbol.BTC

    async def test_gate1_fails_returns_none(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate2_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        gate1_mock = MagicMock(spec=AssessMarketRegimeService)
        gate1_mock.execute = AsyncMock(return_value=(_fail_gate(Gate.REGIME_RANGE_FIT), _make_proposal()))

        bot = _make_bot()
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        proposal = await svc.reconfigure_bot(Symbol.BTC)
        assert proposal is None

    async def test_gate2_fails_returns_none(
        self,
        grid_port: MagicMock,
        indicator_service: MagicMock,
        grid_builder: GridProposalBuilder,
        gate1_mock: MagicMock,
        gate3_mock: MagicMock,
    ) -> None:
        gate2_mock = MagicMock(spec=AssessPositioningService)
        gate2_mock.execute = AsyncMock(return_value=_fail_gate(Gate.POSITIONING))

        bot = _make_bot()
        svc = _make_service(grid_port, bot, indicator_service, grid_builder, gate1_mock, gate2_mock, gate3_mock)

        proposal = await svc.reconfigure_bot(Symbol.BTC)
        assert proposal is None

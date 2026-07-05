from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from source.application.services.grid_service import GridBotService
from source.domain.entities import DecisionVerdict
from source.domain.entities.monitoring import Bot
from source.domain.exceptions import DecisionNotFoundError
from source.domain.value_objects import GateStatus, GridLaunchStatus, GridType, Symbol, Trend, VerdictAction
from source.infrastructure.database.repositories.filters import BaseQueryFilter
from tests.fixtures.factories import make_gate_result, make_proposed_grid_params


FIXED_OID = UUID("00000000-0000-0000-0000-000000000001")


class FakeLaunchedGridRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Bot] = {}

    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[Bot]:  # noqa: ARG002
        return list(self._storage.values())

    async def get_one(self, filters: BaseQueryFilter) -> Bot | None:
        for grid in self._storage.values():
            match = True
            for condition in filters.conditions:
                if (condition.field == "symbol" and grid.symbol.value != condition.value) or (
                    condition.field == "status" and grid.status.value != condition.value
                ):
                    match = False
            if match:
                return grid
        return None

    async def get_by_oid(self, oid: UUID) -> Bot | None:
        return self._storage.get(oid)

    async def add(self, data: Bot) -> Bot:
        if data.oid is None:
            data.oid = UUID(f"00000000-0000-0000-0000-{len(self._storage):012d}")
        self._storage[data.oid] = data
        return data


class FakeDecisionLogRepoWithOid:
    def __init__(self) -> None:
        self._storage: dict[UUID, DecisionVerdict] = {}

    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[DecisionVerdict]:  # noqa: ARG002
        return list(self._storage.values())

    async def get_one(self, filters: BaseQueryFilter) -> DecisionVerdict | None:  # noqa: ARG002
        return next(iter(self._storage.values()), None)

    async def get_by_oid(self, oid: UUID) -> DecisionVerdict | None:
        return self._storage.get(oid)

    async def add(self, data: DecisionVerdict) -> DecisionVerdict:
        key = data.oid or UUID(f"00000000-0000-0000-0000-{len(self._storage):012d}")
        self._storage[key] = data
        return data


def _make_verdict(**overrides: object) -> DecisionVerdict:
    defaults: dict[str, object] = {
        "symbol": Symbol.BTC,
        "action": VerdictAction.LAUNCH,
        "gates": (make_gate_result(status=GateStatus.PASS),),
        "oid": FIXED_OID,
        "notes": None,
        "suggested_parameters": make_proposed_grid_params(leverage=1, trend=Trend.NEUTRAL),
    }
    return DecisionVerdict(**(defaults | overrides))  # type: ignore[arg-type]


def _make_service(
    grid_repo: FakeLaunchedGridRepository | None = None,
    decision_repo: FakeDecisionLogRepoWithOid | None = None,
    grid_port: AsyncMock | None = None,
) -> GridBotService:
    grid_repo = grid_repo or FakeLaunchedGridRepository()
    decision_repo = decision_repo or FakeDecisionLogRepoWithOid()

    @asynccontextmanager
    async def grid_provider() -> AsyncGenerator[FakeLaunchedGridRepository, None]:
        yield grid_repo

    @asynccontextmanager
    async def decision_provider() -> AsyncGenerator[FakeDecisionLogRepoWithOid, None]:
        yield decision_repo

    return GridBotService(
        provider_bot_repository=grid_provider,  # type: ignore[arg-type]
        provider_decision_log_repository=decision_provider,  # type: ignore[arg-type]
        grid_port=grid_port or AsyncMock(),
    )


async def test_persist_grid_saves_and_returns_grid_with_oid() -> None:
    grid_repo = FakeLaunchedGridRepository()
    service = _make_service(grid_repo=grid_repo)
    grid = Bot(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        levels=50,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
        leverage=1,
        investment=1_000.0,
        status=GridLaunchStatus.RUNNING,
        decision_verdict_oid=FIXED_OID,
    )

    result = await service.persist_grid(grid)

    assert result is grid

    assert grid.oid is not None
    stored = await grid_repo.get_by_oid(grid.oid)
    assert stored is grid


async def test_get_grid_when_matching_grid_exists_returns_it() -> None:
    grid_repo = FakeLaunchedGridRepository()
    grid = Bot(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        levels=50,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
        leverage=1,
        investment=1_000.0,
        status=GridLaunchStatus.RUNNING,
        decision_verdict_oid=FIXED_OID,
    )
    await grid_repo.add(grid)
    service = _make_service(grid_repo=grid_repo)

    result = await service.get_grid(Symbol.BTC, GridLaunchStatus.RUNNING)

    assert result is not None
    assert result.symbol == Symbol.BTC
    assert result.status == GridLaunchStatus.RUNNING


async def test_get_grid_when_no_matching_grid_returns_none() -> None:
    service = _make_service()

    result = await service.get_grid(Symbol.BTC, GridLaunchStatus.RUNNING)

    assert result is None


async def test_launch_grid_with_api_calls_exchange_and_persists() -> None:
    verdict = _make_verdict(oid=FIXED_OID)
    decision_repo = FakeDecisionLogRepoWithOid()
    await decision_repo.add(verdict)

    grid_from_api = Bot(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        levels=50,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
        leverage=1,
        investment=1_000.0,
        status=GridLaunchStatus.RUNNING,
        decision_verdict_oid=FIXED_OID,
        oid="grid-ext-1",
    )

    grid_port = AsyncMock()
    grid_port.place_grid.return_value = grid_from_api

    grid_repo = FakeLaunchedGridRepository()
    service = _make_service(grid_repo=grid_repo, decision_repo=decision_repo, grid_port=grid_port)

    result = await service.launch_grid_with_api(FIXED_OID)

    grid_port.place_grid.assert_called_once_with(verdict)
    assert result is grid_from_api
    stored = await grid_repo.get_by_oid("grid-ext-1")
    assert stored is grid_from_api


async def test_launch_grid_with_api_when_verdict_not_found_raises() -> None:
    service = _make_service()

    with pytest.raises(DecisionNotFoundError, match="vdct-999"):
        await service.launch_grid_with_api("vdct-999")


async def test_launch_grid_manual_persists_grid_from_verdict_params() -> None:
    params = make_proposed_grid_params(
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=1,
        trend=Trend.NEUTRAL,
        quote_investment=1_000.0,
    )
    verdict = _make_verdict(oid=FIXED_OID, suggested_parameters=params)
    decision_repo = FakeDecisionLogRepoWithOid()
    await decision_repo.add(verdict)

    grid_repo = FakeLaunchedGridRepository()
    service = _make_service(grid_repo=grid_repo, decision_repo=decision_repo)

    result = await service.launch_grid_manual(FIXED_OID)

    assert result.symbol == Symbol.BTC
    assert result.top == 100_000.0
    assert result.bottom == 88_000.0
    assert result.status == GridLaunchStatus.RUNNING
    assert result.decision_verdict_oid == FIXED_OID


async def test_launch_grid_manual_when_verdict_missing_params_raises() -> None:
    verdict = _make_verdict(oid=FIXED_OID, suggested_parameters=None)
    decision_repo = FakeDecisionLogRepoWithOid()
    await decision_repo.add(verdict)
    service = _make_service(decision_repo=decision_repo)

    with pytest.raises(DecisionNotFoundError, match=str(FIXED_OID)):
        await service.launch_grid_manual(FIXED_OID)

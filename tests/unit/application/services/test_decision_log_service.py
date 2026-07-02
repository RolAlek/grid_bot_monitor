from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta

from source.application.services.decision_log_service import DecisionLogService
from source.domain.entities import GateResult
from source.domain.value_objects import Gate, GateStatus, Symbol, VerdictAction
from tests.fixtures.factories import FIXED_NOW, make_decision_verdict
from tests.fixtures.fakes import FakeDecisionLogRepository


def _make_decision_service() -> tuple[DecisionLogService, FakeDecisionLogRepository]:
    repo = FakeDecisionLogRepository()

    @asynccontextmanager
    async def provider() -> AsyncGenerator[FakeDecisionLogRepository, None]:
        yield repo

    return DecisionLogService(provider), repo


async def test_get_last_decision_empty_returns_none() -> None:
    service, _ = _make_decision_service()
    result = await service.get_last_decision(Symbol.BTC)
    assert result is None


async def test_persist_and_retrieve_round_trips() -> None:
    service, _ = _make_decision_service()
    gate = GateResult(
        gate=Gate.REGIME_RANGE_FIT,
        status=GateStatus.CAUTION,
        reasons=("adx high", "vol rising"),
        raw_values={"adx14": 27.5, "atr14": 1000.0},
    )
    verdict = make_decision_verdict(
        action=VerdictAction.REVIEW,
        gates=(gate,),
        notes="weekly check",
    )
    await service.persist_verdict(verdict)
    retrieved = await service.get_last_decision(Symbol.BTC)
    assert retrieved is not None
    assert retrieved.action == VerdictAction.REVIEW
    assert retrieved.notes == "weekly check"


async def test_get_last_decision_returns_most_recent() -> None:
    service, _ = _make_decision_service()
    older = make_decision_verdict(created_at=FIXED_NOW - timedelta(days=1), action=VerdictAction.HOLD)
    newer = make_decision_verdict(created_at=FIXED_NOW, action=VerdictAction.LAUNCH)

    # Insert older first, then newer
    await service.persist_verdict(older)
    await service.persist_verdict(newer)

    result = await service.get_last_decision(Symbol.BTC)
    assert result is not None
    assert result.action == VerdictAction.LAUNCH

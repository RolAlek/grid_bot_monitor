from collections.abc import AsyncGenerator
from dataclasses import asdict
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from source.domain.entities import GateResult
from source.domain.value_objects import Gate, GateStatus, Symbol, VerdictAction
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.models import DecisionLog
from source.infrastructure.database.repositories.decision_repository import SQLAlchemyDecisionLogRepository
from tests.fixtures.factories import FIXED_NOW, make_decision_verdict, make_gate_result


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session: AsyncSession) -> SQLAlchemyDecisionLogRepository:
    return SQLAlchemyDecisionLogRepository(db_session)


async def test_get_last_decision_empty_returns_none(
    repo: SQLAlchemyDecisionLogRepository,
) -> None:
    result = await repo.get_last_decision(Symbol.BTC)
    assert result is None


async def test_save_and_get_last_decision_round_trips(
    repo: SQLAlchemyDecisionLogRepository,
) -> None:
    gate = GateResult(
        gate=Gate.REGIME_RANGE_FIT,
        status=GateStatus.CAUTION,
        reasons=("adx above caution", "vol rising"),
        raw_values={"adx14": 27.5, "atr14": 1_000.0},
    )
    verdict = make_decision_verdict(
        action=VerdictAction.REVIEW,
        gates=(gate,),
        notes="weekly assessment",
    )
    await repo.save_decision(verdict)
    retrieved = await repo.get_last_decision(Symbol.BTC)

    assert retrieved is not None
    assert retrieved.action == VerdictAction.REVIEW
    assert retrieved.notes == "weekly assessment"
    assert len(retrieved.gates) == 1

    saved_gate = retrieved.gates[0]
    assert saved_gate.gate == Gate.REGIME_RANGE_FIT
    assert saved_gate.status == GateStatus.CAUTION
    assert "adx above caution" in saved_gate.reasons
    assert saved_gate.raw_values["adx14"] == pytest.approx(27.5)


async def test_save_preserves_multiple_gates(
    repo: SQLAlchemyDecisionLogRepository,
) -> None:
    gates = (
        make_gate_result(Gate.REGIME_RANGE_FIT, GateStatus.PASS),
        make_gate_result(Gate.POSITIONING, GateStatus.CAUTION, ("high funding",)),
        make_gate_result(Gate.LIQUIDATION_SAFETY, GateStatus.PASS),
    )
    verdict = make_decision_verdict(action=VerdictAction.REVIEW, gates=gates)
    await repo.save_decision(verdict)

    retrieved = await repo.get_last_decision(Symbol.BTC)
    assert retrieved is not None
    assert len(retrieved.gates) == 3
    gate_types = {g.gate for g in retrieved.gates}
    assert Gate.REGIME_RANGE_FIT in gate_types
    assert Gate.POSITIONING in gate_types


async def test_get_last_decision_returns_most_recent_by_created_at(
    db_session: AsyncSession,
    repo: SQLAlchemyDecisionLogRepository,
) -> None:
    make_gate_result(Gate.REGIME_RANGE_FIT, GateStatus.PASS)
    older = make_decision_verdict(action=VerdictAction.HOLD)
    newer = make_decision_verdict(action=VerdictAction.LAUNCH)

    older_row = DecisionLog(
        symbol=Symbol.BTC.value,
        action=VerdictAction.HOLD.value,
        gates_json=tuple(asdict(gate) for gate in older.gates),
        notes="older",
    )
    older_row.created_at = FIXED_NOW - timedelta(days=2)
    db_session.add(older_row)

    newer_row = DecisionLog(
        symbol=Symbol.BTC.value,
        action=VerdictAction.LAUNCH.value,
        gates_json=tuple(asdict(gate) for gate in newer.gates),
        notes="newer",
    )
    newer_row.created_at = FIXED_NOW
    db_session.add(newer_row)

    await db_session.commit()

    result = await repo.get_last_decision(Symbol.BTC)
    assert result is not None
    assert result.action == VerdictAction.LAUNCH
    assert result.notes == "newer"


async def test_get_last_decision_isolated_by_symbol(
    repo: SQLAlchemyDecisionLogRepository,
) -> None:
    verdict = make_decision_verdict(action=VerdictAction.HOLD)
    await repo.save_decision(verdict)

    stmt_result = await repo.get_last_decision(Symbol.BTC)
    assert stmt_result is not None  # BTC finds it

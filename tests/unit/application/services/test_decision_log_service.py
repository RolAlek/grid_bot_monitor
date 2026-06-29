from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.oi_snapshot_service import OISnapshotService
from source.domain.entities import DecisionVerdict, FundingOiSnapshot
from source.domain.value_objects import Gate, GateResult, GateStatus, Symbol, VerdictAction
from tests.fixtures.factories import FIXED_NOW, make_decision_verdict, make_funding_oi_snapshot


class FakeDecisionLogRepository:
    def __init__(self) -> None:
        self._saved: list[DecisionVerdict] = []

    async def save_decision(self, data: DecisionVerdict) -> None:
        self._saved.append(data)

    async def get_last_decision(self, symbol: Symbol) -> DecisionVerdict | None:
        matching = [verdict for verdict in self._saved if verdict.symbol == symbol]
        if not matching:
            return None
        return max(matching, key=lambda verdict: verdict.as_of)


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self._snapshots: list[FundingOiSnapshot] = []

    async def save_snapshot(self, snapshot_data: FundingOiSnapshot) -> None:
        self._snapshots.append(snapshot_data)

    async def get_oi_snapshots_last_7d(self, symbol: Symbol, as_of: datetime) -> list[FundingOiSnapshot]:
        cutoff = as_of - timedelta(days=7)
        return [
            snapshot
            for snapshot in self._snapshots
            if snapshot.symbol == symbol and snapshot.as_of.replace(tzinfo=UTC) >= cutoff.replace(tzinfo=UTC)
        ]


def _make_decision_service() -> tuple[DecisionLogService, FakeDecisionLogRepository]:
    repo = FakeDecisionLogRepository()

    @asynccontextmanager
    async def provider() -> AsyncGenerator[FakeDecisionLogRepository, None]:
        yield repo

    return DecisionLogService(provider), repo


def _make_oi_service() -> tuple[OISnapshotService, FakeSnapshotRepository]:
    repo = FakeSnapshotRepository()

    @asynccontextmanager
    async def provider() -> AsyncGenerator[FakeSnapshotRepository, None]:
        yield repo

    return OISnapshotService(provider), repo


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
    older = make_decision_verdict(as_of=FIXED_NOW - timedelta(days=1), action=VerdictAction.HOLD)
    newer = make_decision_verdict(as_of=FIXED_NOW, action=VerdictAction.LAUNCH)

    # Insert older first, then newer
    await service.persist_verdict(older)
    await service.persist_verdict(newer)

    result = await service.get_last_decision(Symbol.BTC)
    assert result is not None
    assert result.action == VerdictAction.LAUNCH


async def test_oi_pct_change_none_when_fewer_than_min_snapshots() -> None:
    service, repo = _make_oi_service()
    snap = make_funding_oi_snapshot(as_of=FIXED_NOW, open_interest=5_000_000.0)
    repo._snapshots.append(snap)  # noqa: SLF001

    result = await service.compute_oi_pct_change_7d(Symbol.BTC, FIXED_NOW, 5_500_000.0)
    assert result is None


async def test_oi_pct_change_computed_when_enough_snapshots() -> None:
    service, repo = _make_oi_service()
    oldest = make_funding_oi_snapshot(as_of=FIXED_NOW - timedelta(days=6), open_interest=4_000_000.0)
    mid = make_funding_oi_snapshot(as_of=FIXED_NOW - timedelta(days=3), open_interest=4_500_000.0)
    repo._snapshots.extend([oldest, mid])  # noqa: SLF001

    newest_oi = 5_000_000.0
    result = await service.compute_oi_pct_change_7d(Symbol.BTC, FIXED_NOW, newest_oi)

    expected = (newest_oi - 4_000_000.0) / 4_000_000.0 * 100
    assert result is not None
    assert abs(result - expected) < 0.001


async def test_persist_oi_snapshot_saves_to_repo() -> None:
    service, repo = _make_oi_service()
    snap = make_funding_oi_snapshot()
    await service.persist_oi_snapshot(snap)
    assert len(repo._snapshots) == 1  # noqa: SLF001
    assert repo._snapshots[0].open_interest == snap.open_interest  # noqa: SLF001

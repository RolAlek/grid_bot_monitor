from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun import freeze_time

from source.application.services.oi_snapshot_service import OISnapshotService
from source.domain.entities import FundingRate, OpenInterest
from source.domain.value_objects import Symbol
from tests.fixtures.factories import FIXED_NOW, make_funding_oi_snapshot
from tests.fixtures.fakes import FakeSnapshotRepository


def _make_oi_service(open_interest_value: float = 5_000_000.0) -> tuple[OISnapshotService, FakeSnapshotRepository]:
    repo = FakeSnapshotRepository()

    @asynccontextmanager
    async def provider() -> AsyncGenerator[FakeSnapshotRepository, None]:
        yield repo

    market_data = AsyncMock()
    market_data.get_funding_rates.return_value = [FundingRate(rate=0.0001, time=FIXED_NOW)]
    market_data.get_open_interest.return_value = OpenInterest(symbol=Symbol.BTC, open_interest=open_interest_value)
    return OISnapshotService(provider, market_data_client=market_data), repo


@freeze_time(FIXED_NOW)
async def test_oi_pct_change_none_when_fewer_than_min_snapshots() -> None:
    service, repo = _make_oi_service()
    snap = make_funding_oi_snapshot(created_at=FIXED_NOW, open_interest=5_000_000.0)
    await repo.add(snap)

    result = await service.create_snapshot(Symbol.BTC)
    assert result is not None
    assert result.oi_pct_change_7d is None  # insufficient history


@freeze_time(FIXED_NOW)
async def test_oi_pct_change_computed_when_enough_snapshots() -> None:
    service, repo = _make_oi_service(open_interest_value=5_000_000.0)
    oldest = make_funding_oi_snapshot(created_at=FIXED_NOW - timedelta(days=6), open_interest=4_000_000.0)
    mid = make_funding_oi_snapshot(created_at=FIXED_NOW - timedelta(days=3), open_interest=4_500_000.0)
    await repo.add(oldest)
    await repo.add(mid)

    result = await service.create_snapshot(Symbol.BTC)

    expected = (5_000_000.0 - 4_000_000.0) / 4_000_000.0 * 100
    assert result is not None
    assert result.oi_pct_change_7d is not None
    assert abs(result.oi_pct_change_7d - expected) < 0.001


@freeze_time(FIXED_NOW)
async def test_persist_oi_snapshot_saves_to_repo() -> None:
    service, repo = _make_oi_service()
    snap = make_funding_oi_snapshot()
    await service.persist_oi_snapshot(snap)
    all_snapshots = await repo.get_list()
    assert len(all_snapshots) == 1
    assert all_snapshots[0].open_interest == snap.open_interest

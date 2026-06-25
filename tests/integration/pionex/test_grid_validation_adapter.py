import dataclasses
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from freezegun import freeze_time

from source.domain.entities import LiquidationEstimate, ProposedGridParams
from source.domain.value_objects import GridType, Symbol, Trend
from source.infrastructure.http.pionex.staleness_guard_adapter import StalenessGuardAdapter


@pytest.fixture
def proposal() -> ProposedGridParams:
    return ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.LONG,
        grid_type=GridType.GEOMETRIC,
    )


def _estimate(proposal: ProposedGridParams) -> LiquidationEstimate:
    return LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=115_000.0,
        estimate_liquidation_price_down=75_000.0,
    )


@pytest.fixture
def mock_delegate(proposal: ProposedGridParams) -> AsyncMock:
    mock = AsyncMock()
    mock.check_grid_params.return_value = _estimate(proposal)
    return mock


@pytest.fixture
def guard(mock_delegate: AsyncMock) -> StalenessGuardAdapter:
    return StalenessGuardAdapter(delegate=mock_delegate, ttl_seconds=120)


async def test_first_call_hits_delegate(
    guard: StalenessGuardAdapter, mock_delegate: AsyncMock, proposal: ProposedGridParams
) -> None:
    await guard.check_grid_params(proposal)
    mock_delegate.check_grid_params.assert_called_once_with(proposal)


async def test_fresh_cache_is_reused(
    guard: StalenessGuardAdapter, mock_delegate: AsyncMock, proposal: ProposedGridParams
) -> None:
    t0 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)

    with freeze_time(t0) as frozen_time:
        await guard.check_grid_params(proposal)
        frozen_time.tick(delta=60)  # 60s — still within 120s TTL
        await guard.check_grid_params(proposal)
    assert mock_delegate.check_grid_params.call_count == 1


async def test_stale_cache_forces_fresh_call(
    guard: StalenessGuardAdapter, mock_delegate: AsyncMock, proposal: ProposedGridParams
) -> None:
    t0 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)

    with freeze_time(t0) as frozen_time:
        await guard.check_grid_params(proposal)
        frozen_time.tick(delta=121)  # 121s — past 120s TTL
        await guard.check_grid_params(proposal)
    assert mock_delegate.check_grid_params.call_count == 2


async def test_exactly_at_ttl_is_stale(
    guard: StalenessGuardAdapter, mock_delegate: AsyncMock, proposal: ProposedGridParams
) -> None:
    t0 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)

    with freeze_time(t0) as frozen_time:
        await guard.check_grid_params(proposal)
        frozen_time.tick(delta=120)  # exactly at boundary — should be stale (strict <)
        await guard.check_grid_params(proposal)

    assert mock_delegate.check_grid_params.call_count == 2


async def test_different_proposals_cached_independently(guard: StalenessGuardAdapter, mock_delegate: AsyncMock) -> None:
    proposal_a = ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.LONG,
        grid_type=GridType.GEOMETRIC,
    )
    proposal_b = dataclasses.replace(proposal_a, top=95_000.0, bottom=85_000.0)

    mock_delegate.check_grid_params.side_effect = [_estimate(proposal_a), _estimate(proposal_b)]

    await guard.check_grid_params(proposal_a)
    await guard.check_grid_params(proposal_b)
    assert mock_delegate.check_grid_params.call_count == 2


async def test_cache_reused_per_proposal(guard: StalenessGuardAdapter, mock_delegate: AsyncMock) -> None:
    proposal_a = ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.LONG,
        grid_type=GridType.GEOMETRIC,
    )
    proposal_b = dataclasses.replace(proposal_a, top=95_000.0, bottom=85_000.0)

    mock_delegate.check_grid_params.side_effect = [_estimate(proposal_a), _estimate(proposal_b)]

    t0 = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)

    with freeze_time(t0) as frozen_time:
        await guard.check_grid_params(proposal_a)
        await guard.check_grid_params(proposal_b)
        frozen_time.tick(delta=60)  # still within TTL
        await guard.check_grid_params(proposal_a)  # should hit cache
    assert mock_delegate.check_grid_params.call_count == 2

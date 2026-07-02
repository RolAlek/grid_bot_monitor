from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from source.domain.exceptions import DuplicateOISnapshotError
from source.domain.value_objects import Symbol
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.models import OISnapshot
from source.infrastructure.database.repositories.alchemy.snapshot_repository import SQLAlchemySnapshotRepository
from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter, Operator
from tests.fixtures.factories import make_funding_oi_snapshot


# Naive datetime matching FIXED_NOW's date — SQLite stores datetimes without timezone info.
_NAIVE_NOW = datetime(2026, 6, 1, 0, 0, 0)  # noqa: DTZ001


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()

    await engine.dispose()


@pytest.fixture
def repo(db_session: AsyncSession) -> SQLAlchemySnapshotRepository:
    return SQLAlchemySnapshotRepository(db_session)


@pytest.fixture
def filters() -> BaseQueryFilter:
    return BaseQueryFilter(
        conditions=(
            BaseFieldCondition(field="symbol", operator=Operator.EQUALS, value=Symbol.BTC.value),
            BaseFieldCondition(
                field="created_at",
                operator=Operator.GREATER_OR_EQUALS,
                value=_NAIVE_NOW - timedelta(days=7),
            ),
        )
    )


async def test_save_snapshot_persists_all_fields(
    repo: SQLAlchemySnapshotRepository,
    db_session: AsyncSession,
    filters: BaseQueryFilter,
) -> None:
    snapshot = make_funding_oi_snapshot()
    await repo.add(snapshot)
    await db_session.commit()

    rows = await repo.get_list(filters)
    assert len(rows) == 1
    assert rows[0].symbol == snapshot.symbol
    assert rows[0].open_interest == snapshot.open_interest
    assert rows[0].funding_rate_last == snapshot.funding_rate_last
    assert rows[0].oi_pct_change_7d == snapshot.oi_pct_change_7d


async def test_get_oi_snapshots_returns_empty_when_no_data(
    filters: BaseQueryFilter,
    repo: SQLAlchemySnapshotRepository,
) -> None:
    result = await repo.get_list(filters)
    assert result == []


async def test_get_oi_snapshots_last_7d_excludes_rows_older_than_window(
    repo: SQLAlchemySnapshotRepository,
    db_session: AsyncSession,
    filters: BaseQueryFilter,
) -> None:
    db_session.add(_make_row(created_at=_NAIVE_NOW - timedelta(days=8)))
    await db_session.commit()

    result = await repo.get_list(filters)
    assert result == []


async def test_get_oi_snapshots_last_7d_includes_row_at_boundary(
    repo: SQLAlchemySnapshotRepository,
    db_session: AsyncSession,
    filters: BaseQueryFilter,
) -> None:
    # The query uses >=, so a row exactly 7 days back is included.
    db_session.add(_make_row(created_at=_NAIVE_NOW - timedelta(days=7)))
    await db_session.commit()

    result = await repo.get_list(filters)
    assert len(result) == 1


async def test_get_oi_snapshots_last_7d_returns_rows_ascending(
    repo: SQLAlchemySnapshotRepository,
    db_session: AsyncSession,
    filters: BaseQueryFilter,
) -> None:
    for days_ago in (5, 1, 3):
        db_session.add(_make_row(created_at=_NAIVE_NOW - timedelta(days=days_ago)))
    await db_session.commit()

    result = await repo.get_list(filters)
    assert len(result) == 3
    assert result[0].created_at < result[1].created_at < result[2].created_at


async def test_duplicate_snapshot_same_symbol_date_raises_integrity_error(
    repo: SQLAlchemySnapshotRepository,
    db_session: AsyncSession,
) -> None:
    await repo.add(make_funding_oi_snapshot())
    await db_session.commit()

    with pytest.raises(DuplicateOISnapshotError):
        await repo.add(make_funding_oi_snapshot())


def _make_row(
    symbol: Symbol = Symbol.BTC,
    created_at: datetime | None = None,
) -> OISnapshot:
    return OISnapshot(
        symbol=symbol.value,
        funding_rate_last=0.0001,
        funding_rate_annualized_pct=10.95,
        open_interest=5_000_000.0,
        oi_pct_change_7d=None,
        created_at=created_at or _NAIVE_NOW,
    )

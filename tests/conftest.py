import dataclasses
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from source.domain.entities import FundingOiSnapshot, IndicatorSet, LiquidationEstimate, ProposedGridParams
from source.domain.value_objects import GridType, Symbol, Trend
from source.infrastructure.database.models.base import Base
from source.settings import DecisionEngineSettings


FIXED_NOW = datetime(2026, 6, 19, 0, 0, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self) -> None:
        self._now = FIXED_NOW

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


def replace(entity: object, **changes: object) -> object:
    return dataclasses.replace(entity, **changes)  # type: ignore[arg-type, type-var]


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def settings() -> DecisionEngineSettings:
    return DecisionEngineSettings()


@pytest.fixture
def base_indicators() -> IndicatorSet:
    return IndicatorSet(
        interval="4H",
        as_of=FIXED_NOW,
        adx14=20.0,
        atr14=1_000.0,
        atr_pct_of_price=1.0,
        sma50=95_000.0,
        macd=200.0,
        macd_signal=150.0,
        rsi14=55.0,
        last_price=96_000.0,
        swing_high_14d=100_000.0,
        swing_low_14d=88_000.0,
        realized_vol_1d=0.02,
        realized_vol_7d=0.015,  # flat/falling — no rising-vol CAUTION
        realized_vol_30d=0.01,
    )


@pytest.fixture
def base_proposal() -> ProposedGridParams:
    return ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
        last_price=96_000.0,
    )


@pytest.fixture
def base_snapshot() -> FundingOiSnapshot:
    return FundingOiSnapshot(
        symbol=Symbol.BTC,
        created_at=FIXED_NOW,
        funding_rate_last=0.0001,
        open_interest=5_000_000.0,
        oi_pct_change_7d=5.0,
    )


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.fixture
async def db_session(postgres_url: str) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(postgres_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    await engine.dispose()


@pytest.fixture
def base_liq_estimate(base_proposal: ProposedGridParams) -> LiquidationEstimate:
    return LiquidationEstimate(
        proposal=base_proposal,
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=None,
    )

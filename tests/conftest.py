import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from source.domain.entities import FundingOiSnapshot, IndicatorSet, LiquidationEstimate, ProposedGridParams
from source.domain.value_objects import GridType, Symbol, Trend
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
    )


@pytest.fixture
def base_snapshot() -> FundingOiSnapshot:
    return FundingOiSnapshot(
        symbol=Symbol.BTC,
        as_of=FIXED_NOW,
        funding_rate_last=0.0001,
        open_interest=5_000_000.0,
        oi_pct_change_7d=5.0,
    )


@pytest.fixture
def base_liq_estimate(base_proposal: ProposedGridParams) -> LiquidationEstimate:
    return LiquidationEstimate(
        proposal=base_proposal,
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=None,
    )

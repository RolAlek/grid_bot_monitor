import pytest

from source.application.services.grid_builder import GridProposalBuilder
from source.domain.value_objects import Symbol, Trend
from source.settings import DecisionEngineSettings
from tests.fixtures.factories import make_indicator_set


@pytest.fixture
def builder(settings: DecisionEngineSettings) -> GridProposalBuilder:
    return GridProposalBuilder(settings)


@pytest.mark.parametrize(
    ("last_price", "sma50", "macd", "macd_signal", "expected_trend"),
    [
        # Both price and MACD biases agree long
        (96_000.0, 95_000.0, 200.0, 150.0, Trend.LONG),
        # Both agree short
        (94_000.0, 95_000.0, 100.0, 150.0, Trend.SHORT),
        # Price above SMA, MACD below signal — disagreement → NEUTRAL
        (96_000.0, 95_000.0, 100.0, 150.0, Trend.NEUTRAL),
        # Price below SMA, MACD above signal — disagreement → NEUTRAL
        (94_000.0, 95_000.0, 200.0, 150.0, Trend.NEUTRAL),
    ],
)
def test_trend_derivation(
    builder: GridProposalBuilder,
    last_price: float,
    sma50: float,
    macd: float,
    macd_signal: float,
    expected_trend: Trend,
) -> None:
    indicators = make_indicator_set(last_price=last_price, sma50=sma50, macd=macd, macd_signal=macd_signal)
    proposal = builder.build(Symbol.BTC, indicators)
    assert proposal.trend == expected_trend


def test_grid_levels_scales_with_range(builder: GridProposalBuilder) -> None:
    ind_narrow = make_indicator_set(swing_high_14d=100_000.0, swing_low_14d=88_000.0, atr14=1_000.0)
    ind_wide = make_indicator_set(swing_high_14d=110_000.0, swing_low_14d=88_000.0, atr14=1_000.0)

    result_narrow = builder.build(Symbol.BTC, ind_narrow)
    result_wide = builder.build(Symbol.BTC, ind_wide)

    assert result_narrow.grid_levels != result_wide.grid_levels
    assert result_wide.grid_levels > result_narrow.grid_levels


def test_grid_levels_clamped_to_max(settings: DecisionEngineSettings) -> None:
    builder = GridProposalBuilder(settings)
    ind = make_indicator_set(atr14=1.0, swing_high_14d=100_000.0, swing_low_14d=88_000.0)
    proposal = builder.build(Symbol.BTC, ind)
    assert proposal.grid_levels == settings.max_grid_rows


def test_grid_levels_clamped_to_min(settings: DecisionEngineSettings) -> None:
    builder = GridProposalBuilder(settings)
    ind = make_indicator_set(atr14=100_000.0, swing_high_14d=100_000.0, swing_low_14d=88_000.0)
    proposal = builder.build(Symbol.BTC, ind)
    assert proposal.grid_levels == settings.min_grid_rows

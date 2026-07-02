import pytest

from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.entities import FundingOiSnapshot, LiquidationEstimate
from source.domain.exceptions import InvalidGridParamsError
from source.domain.value_objects import Symbol, Trend
from tests.fixtures.factories import make_proposed_grid_params


def test_neutral_grid_without_stop_loss_is_valid() -> None:
    params = make_proposed_grid_params(trend=Trend.NEUTRAL, stop_loss=None, take_profit=None)
    assert params.trend == Trend.NEUTRAL


@pytest.mark.parametrize("trend", [Trend.LONG, Trend.SHORT])
def test_directional_grid_without_stop_loss_raises(trend: Trend) -> None:
    with pytest.raises(InvalidGridParamsError, match="Stop-loss and take-profit must be set"):
        make_proposed_grid_params(trend=trend, stop_loss=None, take_profit=None)


def test_directional_grid_with_stop_loss_is_valid() -> None:
    params = make_proposed_grid_params(trend=Trend.LONG, stop_loss=80_000.0, take_profit=110_000.0)
    assert params.stop_loss == 80_000.0
    assert params.take_profit == 110_000.0


def test_grid_range_is_top_minus_bottom() -> None:
    params = make_proposed_grid_params(top=100_000.0, bottom=88_000.0)
    assert params.grid_range == 12_000.0


def test_buffer_multiplier_up_when_liquidation_above_top() -> None:
    proposal = make_proposed_grid_params(top=100_000.0, bottom=88_000.0)
    estimate = LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=136_000.0,  # 36k above top
        estimate_liquidation_price_down=None,
    )
    # (136k - 100k) / 12k = 3.0
    assert estimate.buffer_multiplier_up == pytest.approx(3.0)


def test_buffer_multiplier_down_when_liquidation_below_bottom() -> None:
    proposal = make_proposed_grid_params(top=100_000.0, bottom=88_000.0)
    estimate = LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=52_000.0,  # 36k below bottom
    )
    # (88k - 52k) / 12k = 3.0
    assert estimate.buffer_multiplier_down == pytest.approx(3.0)


def test_buffer_multiplier_up_is_none_when_liquidation_is_zero() -> None:
    proposal = make_proposed_grid_params()
    estimate = LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=0.0,  # zero means no risk
        estimate_liquidation_price_down=None,
    )
    assert estimate.buffer_multiplier_up is None


def test_buffer_multiplier_returns_none_when_liquidation_is_none() -> None:
    proposal = make_proposed_grid_params()
    estimate = LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=None,
    )
    assert estimate.buffer_multiplier_up is None
    assert estimate.buffer_multiplier_down is None


def test_funding_rate_annualized_pct_is_correct() -> None:
    snapshot = FundingOiSnapshot(
        symbol=Symbol.BTC,
        created_at=None,  # type: ignore[arg-type]
        funding_rate_last=0.0001,
        open_interest=5_000_000.0,
        oi_pct_change_7d=None,
    )
    expected = 0.0001 * FUNDING_ANNUALIZATION_FACTOR
    assert snapshot.funding_rate_annualized_pct == pytest.approx(expected)


def test_funding_rate_annualized_pct_with_negative_rate() -> None:
    snapshot = FundingOiSnapshot(
        symbol=Symbol.BTC,
        created_at=None,  # type: ignore[arg-type]
        funding_rate_last=-0.0002,
        open_interest=5_000_000.0,
        oi_pct_change_7d=None,
    )
    expected = -0.0002 * FUNDING_ANNUALIZATION_FACTOR
    assert snapshot.funding_rate_annualized_pct == pytest.approx(expected)

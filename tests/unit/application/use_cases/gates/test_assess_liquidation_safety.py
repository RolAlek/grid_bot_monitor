import dataclasses

from source.application.use_cases.liquidation_safety_checks import build_liquidation_safety_checks
from source.application.utils import evaluate_checks
from source.domain.entities import LiquidationEstimate, ProposedGridParams
from source.domain.value_objects import GateStatus, Trend
from source.settings import DecisionEngineSettings
from tests.fixtures.factories import make_liquidation_estimate_with_buffers, make_proposed_grid_params


def _status(estimate: LiquidationEstimate, settings: DecisionEngineSettings) -> GateStatus:
    return evaluate_checks(build_liquidation_safety_checks(estimate, settings))[0]


def _reasons(estimate: LiquidationEstimate, settings: DecisionEngineSettings) -> tuple[str, ...]:
    return evaluate_checks(build_liquidation_safety_checks(estimate, settings))[1]


def _long_proposal() -> ProposedGridParams:
    return make_proposed_grid_params(
        leverage=3,
        trend=Trend.LONG,
        last_price=95_000.0,
        stop_loss=80_000.0,
        take_profit=110_000.0,
    )


def _short_proposal() -> ProposedGridParams:
    return make_proposed_grid_params(
        leverage=3,
        trend=Trend.SHORT,
        last_price=95_000.0,
        stop_loss=105_000.0,
        take_profit=85_000.0,
    )


def test_leverage_within_cap_passes(settings: DecisionEngineSettings) -> None:
    proposal = dataclasses.replace(_long_proposal(), leverage=5)
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=3.0, proposal=proposal)
    assert _status(estimate, settings) == GateStatus.PASS


def test_leverage_exceeds_cap_fails(settings: DecisionEngineSettings) -> None:
    proposal = dataclasses.replace(_long_proposal(), leverage=6)
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=3.0, proposal=proposal)
    result = _status(estimate, settings)
    assert result == GateStatus.FAIL
    reasons = _reasons(estimate, settings)
    assert any("cap" in reason.lower() or "hard" in reason.lower() for reason in reasons)


def test_both_buffers_exactly_at_minimum_passes(settings: DecisionEngineSettings) -> None:
    estimate = make_liquidation_estimate_with_buffers(buf_up=2.5, buf_down=2.5, proposal=_long_proposal())
    assert _status(estimate, settings) == GateStatus.PASS


def test_upper_buffer_irrelevant_for_long_passes(settings: DecisionEngineSettings) -> None:
    estimate = make_liquidation_estimate_with_buffers(buf_up=2.49, buf_down=3.0, proposal=_long_proposal())
    assert _status(estimate, settings) == GateStatus.PASS


def test_lower_buffer_below_minimum_with_stop_loss_protection_passes(settings: DecisionEngineSettings) -> None:
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=2.49, proposal=_long_proposal())
    assert _status(estimate, settings) == GateStatus.PASS


def test_lower_buffer_below_minimum_stop_loss_cant_protect_fails(settings: DecisionEngineSettings) -> None:
    proposal = make_proposed_grid_params(
        leverage=3,
        trend=Trend.LONG,
        last_price=95_000.0,
        stop_loss=60_000.0,
        take_profit=110_000.0,
    )
    make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=2.49, proposal=proposal)
    estimate2 = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=2.0, proposal=proposal)
    result = _status(estimate2, settings)
    assert result == GateStatus.FAIL


def test_both_buffers_above_minimum_passes(settings: DecisionEngineSettings) -> None:
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=3.0, proposal=_long_proposal())
    assert _status(estimate, settings) == GateStatus.PASS


def test_neutral_grid_with_none_buffers_fails(
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    # base_proposal has Trend.NEUTRAL; both liq prices=None → None buffers
    estimate = LiquidationEstimate(
        proposal=base_proposal,
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=None,
    )
    assert _status(estimate, settings) == GateStatus.FAIL


def test_directional_grid_both_none_fails(settings: DecisionEngineSettings) -> None:
    estimate = LiquidationEstimate(
        proposal=_long_proposal(),
        estimate_liquidation_price_up=None,
        estimate_liquidation_price_down=None,
    )
    assert _status(estimate, settings) == GateStatus.FAIL


def test_short_stop_loss_above_liquidation_fails(settings: DecisionEngineSettings) -> None:
    proposal = _short_proposal()
    # stop_loss=105_000, liq_up=top + 3*grid_range = 100_000 + 36_000 = 136_000 → stop < liq → OK
    # Let's set a tight buffer so liq_up drops below stop_loss
    estimate = make_liquidation_estimate_with_buffers(buf_up=0.1, buf_down=3.0, proposal=proposal)
    # liq_up = 100_000 + 0.1*12_000 = 101_200; stop_loss=105_000 → stop >= liq → FAIL
    result = _status(estimate, settings)
    assert result == GateStatus.FAIL
    reasons = _reasons(estimate, settings)
    assert any("Stop-loss" in reason for reason in reasons)


def test_short_stop_loss_too_close_to_price_is_caution(settings: DecisionEngineSettings) -> None:
    proposal = make_proposed_grid_params(
        leverage=3,
        trend=Trend.SHORT,
        last_price=95_000.0,
        stop_loss=95_500.0,  # only 500 away = ~0.53% < 1%
        take_profit=85_000.0,
    )
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=3.0, proposal=proposal)
    result = _status(estimate, settings)
    reasons = _reasons(estimate, settings)
    assert result == GateStatus.CAUTION
    assert any("too close" in reason.lower() for reason in reasons)


def test_short_take_profit_above_bottom_is_caution(settings: DecisionEngineSettings) -> None:
    proposal = make_proposed_grid_params(
        leverage=3,
        trend=Trend.SHORT,
        last_price=95_000.0,
        stop_loss=105_000.0,
        take_profit=89_000.0,  # > bottom (88_000) → CAUTION
    )
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=3.0, proposal=proposal)
    result = _status(estimate, settings)
    reasons = _reasons(estimate, settings)
    assert result == GateStatus.CAUTION
    assert any("Take-profit" in reason for reason in reasons)


def test_short_grid_all_checks_pass(settings: DecisionEngineSettings) -> None:
    proposal = _short_proposal()  # stop=105k, tp=85k, price=95k
    estimate = make_liquidation_estimate_with_buffers(buf_up=3.0, buf_down=3.0, proposal=proposal)
    assert _status(estimate, settings) == GateStatus.PASS

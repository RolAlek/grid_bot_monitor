import dataclasses

from source.application.use_cases.liquidation_safety_checks import build_liquidation_safety_checks
from source.application.utils import evaluate_checks
from source.domain.entities import LiquidationEstimate, ProposedGridParams
from source.domain.value_objects import GateStatus, GridType, Symbol, Trend
from source.settings import DecisionEngineSettings


def _status(estimate: LiquidationEstimate, settings: DecisionEngineSettings) -> GateStatus:
    return evaluate_checks(build_liquidation_safety_checks(estimate, settings))[0]


def _reasons(estimate: LiquidationEstimate, settings: DecisionEngineSettings) -> tuple[str, ...]:
    return evaluate_checks(build_liquidation_safety_checks(estimate, settings))[1]


def _long_proposal() -> ProposedGridParams:
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


def _estimate_with_buffers(proposal: ProposedGridParams, buf_up: float, buf_down: float) -> LiquidationEstimate:
    grid_range = proposal.top - proposal.bottom
    liq_up = proposal.top + buf_up * grid_range if buf_up is not None else None
    liq_down = proposal.bottom - buf_down * grid_range if buf_down is not None else None
    return LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=liq_up,
        estimate_liquidation_price_down=liq_down,
    )


def test_leverage_within_cap_passes(settings: DecisionEngineSettings) -> None:
    proposal = dataclasses.replace(_long_proposal(), leverage=5)
    estimate = _estimate_with_buffers(proposal, buf_up=3.0, buf_down=3.0)
    assert _status(estimate, settings) == GateStatus.PASS


def test_leverage_exceeds_cap_fails(settings: DecisionEngineSettings) -> None:
    proposal = dataclasses.replace(_long_proposal(), leverage=6)
    estimate = _estimate_with_buffers(proposal, buf_up=3.0, buf_down=3.0)
    result = _status(estimate, settings)
    assert result == GateStatus.FAIL
    reasons = _reasons(estimate, settings)
    assert any("cap" in reason.lower() or "hard" in reason.lower() for reason in reasons)


def test_both_buffers_exactly_at_minimum_passes(settings: DecisionEngineSettings) -> None:
    estimate = _estimate_with_buffers(_long_proposal(), buf_up=2.5, buf_down=2.5)
    assert _status(estimate, settings) == GateStatus.PASS


def test_upper_buffer_below_minimum_fails(settings: DecisionEngineSettings) -> None:
    estimate = _estimate_with_buffers(_long_proposal(), buf_up=2.49, buf_down=2.5)
    result = _status(estimate, settings)
    assert result == GateStatus.FAIL
    reasons = _reasons(estimate, settings)
    assert any("upper" in reason.lower() or "Up" in reason for reason in reasons)


def test_lower_buffer_below_minimum_fails(settings: DecisionEngineSettings) -> None:
    estimate = _estimate_with_buffers(_long_proposal(), buf_up=2.5, buf_down=2.49)
    result = _status(estimate, settings)
    assert result == GateStatus.FAIL
    reasons = _reasons(estimate, settings)
    assert any("lower" in reason.lower() or "Down" in reason for reason in reasons)


def test_both_buffers_above_minimum_passes(settings: DecisionEngineSettings) -> None:
    estimate = _estimate_with_buffers(_long_proposal(), buf_up=3.0, buf_down=3.0)
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

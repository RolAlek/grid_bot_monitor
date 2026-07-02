from hypothesis import given, settings as hyp_settings, strategies as st

from source.application.use_cases.check_positioning_rules import build_positioning_checks
from source.application.use_cases.check_regime_rules import build_market_regime_checks
from source.application.use_cases.liquidation_safety_checks import build_liquidation_safety_checks
from source.application.utils import evaluate_checks
from source.domain.entities import GateRule, LiquidationEstimate
from source.domain.value_objects import GateStatus, Trend
from source.settings import DecisionEngineSettings
from tests.fixtures.factories import (
    make_funding_oi_snapshot,
    make_indicator_set,
    make_liquidation_estimate_with_buffers,
    make_proposed_grid_params,
)


# Always use a clean settings instance with defaults
SETTINGS = DecisionEngineSettings()

# Valid status values for assertion
_VALID_STATUSES = frozenset(GateStatus)

_FLOATS = st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False)
_SMALL_FLOATS = st.floats(min_value=0.01, max_value=10_000.0, allow_nan=False, allow_infinity=False)


@given(
    adx14=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    atr14=_SMALL_FLOATS,
    swing_high=st.floats(min_value=50_000.0, max_value=200_000.0, allow_nan=False, allow_infinity=False),
    swing_low=st.floats(min_value=30_000.0, max_value=90_000.0, allow_nan=False, allow_infinity=False),
)
@hyp_settings(max_examples=200)
def test_gate1_never_raises_for_valid_inputs(adx14: float, atr14: float, swing_high: float, swing_low: float) -> None:
    if swing_high <= swing_low:
        swing_high = swing_low + 1_000.0

    indicators = make_indicator_set(
        adx14=adx14,
        atr14=atr14,
        swing_high_14d=swing_high,
        swing_low_14d=swing_low,
        last_price=(swing_high + swing_low) / 2,
    )
    proposal = make_proposed_grid_params(top=swing_high, bottom=swing_low)
    checks = build_market_regime_checks(indicators, proposal, SETTINGS)
    status, reasons = evaluate_checks(checks)
    assert status in _VALID_STATUSES
    assert isinstance(reasons, tuple)


@given(
    funding_rate_last=st.floats(min_value=-0.01, max_value=0.01, allow_nan=False, allow_infinity=False),
    oi_pct_change_7d=st.one_of(
        st.none(),
        st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    ),
    open_interest=st.floats(min_value=1_000.0, max_value=1e9, allow_nan=False, allow_infinity=False),
)
@hyp_settings(max_examples=200)
def test_gate2_never_raises_for_valid_inputs(
    funding_rate_last: float,
    oi_pct_change_7d: float | None,
    open_interest: float,
) -> None:
    snapshot = make_funding_oi_snapshot(
        funding_rate_last=funding_rate_last,
        open_interest=open_interest,
        oi_pct_change_7d=oi_pct_change_7d,
    )
    checks = build_positioning_checks(snapshot, SETTINGS)
    status, reasons = evaluate_checks(checks)
    assert status in _VALID_STATUSES
    assert isinstance(reasons, tuple)


@given(
    buf_up=st.one_of(
        st.none(),
        st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
    ),
    buf_down=st.one_of(
        st.none(),
        st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
    ),
    leverage=st.integers(min_value=1, max_value=10),
    trend=st.sampled_from(list(Trend)),
)
@hyp_settings(max_examples=200)
def test_gate3_never_raises_for_valid_inputs(
    buf_up: float | None,
    buf_down: float | None,
    leverage: int,
    trend: Trend,
) -> None:
    overrides: dict[str, object] = {"leverage": leverage, "trend": trend}
    if trend in {Trend.LONG, Trend.SHORT}:
        overrides["stop_loss"] = 80_000.0
        overrides["take_profit"] = 110_000.0
    proposal = make_proposed_grid_params(**overrides)
    if buf_up is not None or buf_down is not None:
        estimate = make_liquidation_estimate_with_buffers(buf_up, buf_down)
    else:
        estimate = LiquidationEstimate(
            proposal=proposal,
            estimate_liquidation_price_up=None,
            estimate_liquidation_price_down=None,
        )
    checks = build_liquidation_safety_checks(estimate, SETTINGS)
    status, reasons = evaluate_checks(checks)
    assert status in _VALID_STATUSES
    assert isinstance(reasons, tuple)


@given(
    statuses=st.lists(
        st.sampled_from(list(GateStatus)),
        min_size=1,
        max_size=10,
    )
)
@hyp_settings(max_examples=300)
def test_evaluate_checks_returns_max_status(statuses: list[GateStatus]) -> None:
    rules = [GateRule(triggered=True, status=s, message=f"check {i}") for i, s in enumerate(statuses)]
    result_status, _ = evaluate_checks(rules)
    assert result_status == max(statuses)

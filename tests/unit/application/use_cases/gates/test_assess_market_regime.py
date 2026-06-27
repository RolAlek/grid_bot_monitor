import dataclasses

import pytest

from source.application.use_cases.check_regime_rules import build_market_regime_checks
from source.application.utils import evaluate_checks
from source.domain.entities import IndicatorSet, ProposedGridParams
from source.domain.value_objects import GateStatus, GridType, Symbol, Trend
from source.settings import DecisionEngineSettings


def _status(indicators: IndicatorSet, proposal: ProposedGridParams, settings: DecisionEngineSettings) -> GateStatus:
    return evaluate_checks(build_market_regime_checks(indicators, proposal, settings))[0]


def _reasons(
    indicators: IndicatorSet,
    proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> tuple[str, ...]:
    return evaluate_checks(build_market_regime_checks(indicators, proposal, settings))[1]


@pytest.mark.parametrize(
    ("adx", "expected"),
    [
        (24.9, GateStatus.PASS),
        (25.0, GateStatus.PASS),
        (25.1, GateStatus.CAUTION),
        (30.0, GateStatus.CAUTION),
        (30.1, GateStatus.FAIL),
    ],
)
def test_adx_boundaries(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
    adx: float,
    expected: GateStatus,
) -> None:
    indicators = dataclasses.replace(base_indicators, adx14=adx)
    assert _status(indicators, base_proposal, settings) == expected


def test_atr_range_too_narrow_fails(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    # grid_range=12_000; ATR=5_000 → min=15_000 → FAIL
    indicators = dataclasses.replace(base_indicators, atr14=5_000.0)
    result = _status(indicators, base_proposal, settings)
    assert result == GateStatus.FAIL
    reasons = _reasons(indicators, base_proposal, settings)
    assert any("tight" in r or "ATR" in r for r in reasons)


def test_atr_range_exactly_at_minimum_passes(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    # grid_range=12_000; ATR=4_000 → min=12_000 → not < 12_000 → PASS
    indicators = dataclasses.replace(base_indicators, atr14=4_000.0)
    assert _status(indicators, base_proposal, settings) == GateStatus.PASS


def test_price_above_swing_high_is_caution(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    indicators = dataclasses.replace(base_indicators, last_price=101_000.0)
    assert _status(indicators, base_proposal, settings) == GateStatus.CAUTION


def test_price_below_swing_low_is_caution(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    indicators = dataclasses.replace(base_indicators, last_price=87_000.0)
    assert _status(indicators, base_proposal, settings) == GateStatus.CAUTION


def test_rising_vol_term_structure_is_caution(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    # 1d < 7d < 30d and each step > 1.05x — upward-sloping term structure
    indicators = dataclasses.replace(base_indicators, realized_vol_1d=0.01, realized_vol_7d=0.02, realized_vol_30d=0.03)
    assert _status(indicators, base_proposal, settings) == GateStatus.CAUTION
    reasons = _reasons(indicators, base_proposal, settings)
    assert any("volatility" in r.lower() or "vol" in r.lower() for r in reasons)


def test_flat_vol_does_not_trigger_caution(
    base_indicators: IndicatorSet,
    base_proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> None:
    indicators = dataclasses.replace(base_indicators, realized_vol_1d=0.02, realized_vol_7d=0.02, realized_vol_30d=0.02)
    assert _status(indicators, base_proposal, settings) == GateStatus.PASS


def test_fail_overrides_caution(
    base_indicators: IndicatorSet,
    settings: DecisionEngineSettings,
) -> None:
    # ADX > 30 (FAIL) + price outside range (CAUTION) → FAIL wins
    indicators = dataclasses.replace(base_indicators, adx14=31.0, last_price=101_000.0)
    dataclasses.replace(base_indicators)  # re-use proposal from base
    # just build a proposal inline

    proposal = ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
    )
    result_status = _status(indicators, proposal, settings)
    assert result_status == GateStatus.FAIL

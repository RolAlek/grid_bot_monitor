from source.domain.entities import IndicatorSet, ProposedGridParams
from source.domain.value_objects import GateRule, GateStatus
from source.settings import DecisionEngineSettings


def build_market_regime_checks(
    indicators: IndicatorSet,
    proposal: ProposedGridParams,
    settings: DecisionEngineSettings,
) -> list[GateRule]:
    grid_range = proposal.top - proposal.bottom
    min_range = settings.atr_range_multiplier_min * indicators.atr14

    return [
        GateRule(
            triggered=indicators.adx14 > settings.adx_caution_max,
            status=GateStatus.FAIL,
            message=(
                f"ADX {indicators.adx14:.1f} exceeds caution max "
                f"{settings.adx_caution_max} — strong trend, grid unfavorable"
            ),
        ),
        GateRule(
            triggered=settings.adx_pass_max < indicators.adx14 <= settings.adx_caution_max,
            status=GateStatus.CAUTION,
            message=(
                f"ADX {indicators.adx14:.1f} in caution zone ({settings.adx_pass_max}-{settings.adx_caution_max})"
            ),
        ),
        GateRule(
            triggered=grid_range < min_range,
            status=GateStatus.FAIL,
            message=(
                f"Grid range {grid_range:.2f} < {settings.atr_range_multiplier_min} * "
                f"ATR14 ({min_range:.2f}) — range too tight"
            ),
        ),
        GateRule(
            triggered=not (indicators.swing_low_14d <= indicators.last_price <= indicators.swing_high_14d),
            status=GateStatus.CAUTION,
            message=(
                f"Price {indicators.last_price:.2f} outside 14d swing range "
                f"[{indicators.swing_low_14d:.2f}, {indicators.swing_high_14d:.2f}]"
            ),
        ),
        GateRule(
            triggered=(
                (indicators.realized_vol_7d > indicators.realized_vol_1d * settings.vol_term_structure_min_ratio)
                and (indicators.realized_vol_30d > indicators.realized_vol_7d * settings.vol_term_structure_min_ratio)
            ),
            status=GateStatus.CAUTION,
            message=(
                f"Rising forward volatility: 1d {indicators.realized_vol_1d:.4f} "
                f"< 7d {indicators.realized_vol_7d:.4f} < 30d {indicators.realized_vol_30d:.4f}"
            ),
        ),
    ]

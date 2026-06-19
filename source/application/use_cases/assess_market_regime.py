from source.domain.value_objects import (
    Gate,
    GateResult,
    GateStatus,
    IndicatorSet,
    ProposedGridParams,
)
from source.settings import DecisionEngineSettings


class AssessMarketRegime:
    def __init__(self, settings: DecisionEngineSettings) -> None:
        self._settings = settings

    def assess(
        self,
        indicators: IndicatorSet,
        proposal: ProposedGridParams,
    ) -> GateResult:
        reasons: list[str] = []
        statuses: list[GateStatus] = [GateStatus.PASS]

        # ADX trend-strength check
        if indicators.adx14 > self._settings.adx_caution_max:
            statuses.append(GateStatus.FAIL)
            reasons.append(
                f"ADX {indicators.adx14:.1f} exceeds caution max {self._settings.adx_caution_max} — strong trend, grid unfavourable"
            )
        elif indicators.adx14 > self._settings.adx_pass_max:
            statuses.append(GateStatus.CAUTION)
            reasons.append(
                f"ADX {indicators.adx14:.1f} in caution zone ({self._settings.adx_pass_max}–{self._settings.adx_caution_max})"
            )

        # Grid range vs ATR check
        grid_range = proposal.top - proposal.bottom
        min_range = self._settings.atr_range_multiplier_min * indicators.atr14
        if grid_range < min_range:
            statuses.append(GateStatus.FAIL)
            reasons.append(
                f"Grid range {grid_range:.2f} < {self._settings.atr_range_multiplier_min} * ATR14 ({min_range:.2f}) — range too tight"
            )

        # Price outside 14-day swing range
        if not (
            indicators.swing_low_14d
            <= indicators.last_price
            <= indicators.swing_high_14d
        ):
            statuses.append(GateStatus.CAUTION)
            reasons.append(
                f"Price {indicators.last_price:.2f} outside 14d swing range "
                f"[{indicators.swing_low_14d:.2f}, {indicators.swing_high_14d:.2f}] — range not yet re-anchored"
            )

        # Rising forward volatility term structure
        if (
            indicators.realized_vol_7d
            > indicators.realized_vol_1d * self._settings.vol_term_structure_min_ratio
        ) and (
            indicators.realized_vol_30d
            > indicators.realized_vol_7d * self._settings.vol_term_structure_min_ratio
        ):
            statuses.append(GateStatus.CAUTION)
            reasons.append(
                f"Rising forward volatility: 1d {indicators.realized_vol_1d:.4f} "
                f"< 7d {indicators.realized_vol_7d:.4f} < 30d {indicators.realized_vol_30d:.4f}"
            )

        return GateResult(
            gate=Gate.REGIME_RANGE_FIT,
            status=max(statuses),
            reasons=tuple(reasons),
            raw_values={
                "adx14": indicators.adx14,
                "atr14": indicators.atr14,
                "grid_range": grid_range,
                "last_price": indicators.last_price,
                "swing_high_14d": indicators.swing_high_14d,
                "swing_low_14d": indicators.swing_low_14d,
                "realized_vol_1d": indicators.realized_vol_1d,
                "realized_vol_7d": indicators.realized_vol_7d,
                "realized_vol_30d": indicators.realized_vol_30d,
            },
        )

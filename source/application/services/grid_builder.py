from source.domain.entities import IndicatorSet, ProposedGridParams
from source.domain.value_objects import Symbol, Trend
from source.settings import DecisionEngineSettings


class GridProposalBuilder:
    def __init__(self, settings: DecisionEngineSettings) -> None:
        self._settings = settings

    def build(self, symbol: Symbol, indicators: IndicatorSet) -> ProposedGridParams:
        return ProposedGridParams(
            symbol=symbol,
            trend=self._determine_trend(indicators),
            grid_type=self._settings.default_grid_type,
            top=indicators.swing_high_14d,
            bottom=indicators.swing_low_14d,
            grid_levels=self._compute_grid_levels(indicators),
            leverage=self._settings.default_leverage,
            quote_investment=self._settings.default_quote_investment,
        )

    def _determine_trend(self, indicators: IndicatorSet) -> Trend:
        bias = 0
        bias += 1 if indicators.last_price > indicators.sma50 else -1
        bias += 1 if indicators.macd > indicators.macd_signal else -1

        if bias >= self._settings.trend_bias_long_threshold:
            return Trend.LONG

        if bias <= self._settings.trend_bias_short_threshold:
            return Trend.SHORT

        return Trend.NEUTRAL

    def _compute_grid_levels(self, indicators: IndicatorSet) -> int:
        target_cell_width = self._settings.target_cell_atr_fraction * indicators.atr14

        return max(
            self._settings.min_grid_rows,
            min(
                self._settings.max_grid_rows,
                round((indicators.swing_high_14d - indicators.swing_low_14d) / target_cell_width),
            ),
        )

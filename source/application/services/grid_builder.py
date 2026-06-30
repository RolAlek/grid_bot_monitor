from typing import ClassVar

from source.domain.entities import IndicatorSet, ProposedGridParams
from source.domain.value_objects import Symbol, Trend
from source.settings import DecisionEngineSettings


class GridProposalBuilder:
    STOP_LOSS_BUFFER: ClassVar[dict[Symbol, float]] = {
        Symbol.XAUT: 2.5,
        Symbol.XRP: 2.0,
    }

    def __init__(self, settings: DecisionEngineSettings) -> None:
        self._settings = settings

    def build(self, symbol: Symbol, indicators: IndicatorSet) -> ProposedGridParams:
        trend = self._determine_trend(indicators)

        stop_loss, take_profit = self._compute_stop_and_take(
            symbol=symbol,
            trend=trend,
            top=indicators.swing_high_14d,
            bottom=indicators.swing_low_14d,
            indicators=indicators,
        )

        return ProposedGridParams(
            symbol=symbol,
            top=indicators.swing_high_14d,
            bottom=indicators.swing_low_14d,
            grid_levels=self._compute_grid_levels(indicators),
            trend=trend,
            grid_type=symbol.regime,
            leverage=self._settings.default_leverage,
            quote_investment=self._settings.default_quote_investment,
            stop_loss=stop_loss,
            take_profit=take_profit,
            last_price=indicators.last_price,
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

    def _compute_stop_and_take(
        self,
        symbol: Symbol,
        trend: Trend,
        top: float,
        bottom: float,
        indicators: IndicatorSet,
    ) -> tuple[float | None, float | None]:
        stop_buffer = self.STOP_LOSS_BUFFER.get(symbol, 1.5) * indicators.atr14
        take_buffer = self._settings.take_profit_buffer_atr * indicators.atr14
        min_distance = (0.005 if symbol == Symbol.XAUT else 0.01) * indicators.last_price

        stop_loss, take_profit = None, None
        match trend:
            case Trend.NEUTRAL:
                return stop_loss, take_profit

            case Trend.LONG:
                stop_loss = bottom - stop_buffer
                take_profit = top + take_buffer

                if (indicators.last_price - stop_loss) < min_distance:
                    stop_loss = indicators.last_price - min_distance

            case Trend.SHORT:
                stop_loss = top + stop_buffer
                take_profit = bottom - take_buffer

                if (stop_loss - indicators.last_price) < min_distance:
                    stop_loss = indicators.last_price + min_distance

        max_distance = 0.30 * indicators.last_price
        if abs(stop_loss - indicators.last_price) > max_distance:
            if trend == Trend.LONG:
                stop_loss = indicators.last_price - max_distance
            else:
                stop_loss = indicators.last_price + max_distance

        return stop_loss, take_profit

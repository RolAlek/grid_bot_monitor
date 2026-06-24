import logging

from source.application.ports import MarketDataPort
from source.application.services.grid_builder import GridProposalBuilder
from source.application.services.indicator_service import IndicatorService
from source.domain.check_regime_rules import build_market_regime_checks
from source.domain.entities import Candle, GateResult, IndicatorSet
from source.domain.value_objects import Gate, GateRule, GateStatus, Symbol
from source.settings import Settings


logger = logging.getLogger(__name__)


class AssessMarketRegimeService:
    def __init__(
        self,
        settings: Settings,
        market_data: MarketDataPort,
        indicator_service: IndicatorService,
        grid_builder: GridProposalBuilder,
    ) -> None:
        self._settings = settings
        self._market_data = market_data
        self._indicator_service = indicator_service
        self._grid_builder = grid_builder

    async def execute(self, symbol: Symbol) -> GateResult:
        candles = await self._fetch_candles(symbol)
        indicators = self._build_indicators_with_candles(candles)
        proposal = self._grid_builder.build(symbol, indicators)
        checks = build_market_regime_checks(
            indicators=indicators,
            proposal=proposal,
            settings=self._settings.decision_engine,
        )
        statuses, reasons = self._evaluate_checks(checks)

        return GateResult(
            gate=Gate.REGIME_RANGE_FIT,
            status=max(statuses),
            reasons=tuple(reasons),
            raw_values={
                "adx14": indicators.adx14,
                "atr14": indicators.atr14,
                "grid_range": proposal.top - proposal.bottom,
                "last_price": indicators.last_price,
                "swing_high_14d": indicators.swing_high_14d,
                "swing_low_14d": indicators.swing_low_14d,
                "realized_vol_1d": indicators.realized_vol_1d,
                "realized_vol_7d": indicators.realized_vol_7d,
                "realized_vol_30d": indicators.realized_vol_30d,
            },
        )

    async def _fetch_candles(self, symbol: Symbol) -> list[Candle]:
        try:
            return await self._market_data.get_candles(
                symbol,
                interval=self._settings.pionex.kline_interval,
                limit=self._settings.pionex.limit,
            )
        except Exception as exc:
            logger.critical("Fetched market data was failed", exc_info=exc)
            raise

    def _build_indicators_with_candles(self, candles: list[Candle]) -> IndicatorSet:
        interval = self._settings.pionex.kline_interval

        try:
            return self._indicator_service.compute(candles, interval)
        except Exception as exc:
            logger.critical(
                "An error occurred while trying to build indicators",
                exc_info=exc,
                extra={"candles": candles, "interval": interval},
            )
            raise

    @staticmethod
    def _evaluate_checks(checks: list[GateRule]) -> tuple[list[GateStatus], list[str]]:
        statuses = [GateStatus.PASS] + [check.status for check in checks if check.triggered]
        reasons = [check.message for check in checks if check.triggered]

        return statuses, reasons

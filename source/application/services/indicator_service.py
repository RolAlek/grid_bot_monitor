import math
from dataclasses import asdict
from math import sqrt
from typing import ClassVar

import numpy as np
import pandas as pd
import pandas_ta as ta
import structlog

from source.application.exceptions import InsufficientKlineDataError, UnsupportedIntervalError
from source.application.ports import MarketDataPort
from source.domain.entities import Candle, IndicatorSet
from source.domain.value_objects import Symbol
from source.settings import PionexSettings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class IndicatorService:
    _INTERVAL_CANDLES_PER_DAY: ClassVar[dict[str, int]] = {
        "1H": 24,
        "2H": 12,
        "4H": 6,
        "6H": 4,
        "8H": 3,
        "12H": 2,
        "1D": 1,
    }
    _MIN_LOOKBACK_DAYS = 31

    def __init__(self, settings: PionexSettings, market_data: MarketDataPort) -> None:
        self._settings = settings
        self._market_data = market_data

    async def compute(self, symbol: Symbol) -> IndicatorSet:
        interval = self._settings.kline_interval

        if interval not in self._INTERVAL_CANDLES_PER_DAY:
            raise UnsupportedIntervalError(f"No candles-per-day mapping for interval={interval!r}")

        candles: list[Candle] = await self._pull_candles(symbol)

        candles_pd = self._INTERVAL_CANDLES_PER_DAY[interval]
        if len(candles) < (min_candles := self._MIN_LOOKBACK_DAYS * candles_pd):
            raise InsufficientKlineDataError(
                f"Need >= {min_candles} candles for interval={interval!r}, got {len(candles)}"
            )

        dataframe = self._convert_to_dataframe(candles)

        adx14 = float(
            ta.adx(
                dataframe["high"],
                dataframe["low"],
                dataframe["close"],
                length=14,
            )["ADX_14"].iloc[-1]
        )
        atr14 = float(
            ta.atr(
                dataframe["high"],
                dataframe["low"],
                dataframe["close"],
                length=14,
            ).iloc[-1]
        )
        macd_val, macd_signal = self._get_macd(dataframe)

        last_price = float(dataframe["close"].iloc[-1])

        result = IndicatorSet(
            interval=interval,
            as_of=dataframe["time"].iloc[-1],
            adx14=adx14,
            atr14=atr14,
            atr_pct_of_price=atr14 / last_price * 100,
            sma50=float(ta.sma(dataframe["close"], length=50).iloc[-1]),
            macd=macd_val,
            macd_signal=macd_signal,
            rsi14=float(ta.rsi(dataframe["close"], length=14).iloc[-1]),
            last_price=last_price,
            swing_high_14d=float(dataframe["high"].tail(14 * candles_pd).max()),
            swing_low_14d=float(dataframe["low"].tail(14 * candles_pd).min()),
            realized_vol_1d=self._calculate_volatilities(dataframe, candles_pd, 1),
            realized_vol_7d=self._calculate_volatilities(dataframe, candles_pd, 7),
            realized_vol_30d=self._calculate_volatilities(dataframe, candles_pd, 30),
        )

        self._validate_no_nan(result)
        return result

    async def _pull_candles(self, symbol: Symbol) -> list[Candle]:
        try:
            return await self._market_data.get_candles(
                symbol,
                interval=self._settings.kline_interval,
                limit=self._settings.limit,
            )
        except Exception:
            logger.exception("Failed to fetch market data", symbol=symbol.value)
            raise

    @staticmethod
    def _convert_to_dataframe(klines: list[Candle]) -> pd.DataFrame:
        dataframe = pd.DataFrame([asdict(kline) for kline in klines])
        dataframe = dataframe.sort_values("time").reset_index(drop=True)

        for col in ("open", "high", "low", "close", "volume"):
            dataframe[col] = pd.to_numeric(dataframe[col])

        return dataframe

    @staticmethod
    def _get_macd(dataframe: pd.DataFrame) -> tuple[float, float]:
        macd_df = ta.macd(dataframe["close"])
        macd_val = float(macd_df["MACD_12_26_9"].iloc[-1])
        macd_signal = float(macd_df["MACDs_12_26_9"].iloc[-1])

        return macd_val, macd_signal

    @staticmethod
    def _calculate_volatilities(dataframe: pd.DataFrame, candles_pd: int, period: int) -> float:
        log_returns = np.log(dataframe["close"].to_numpy() / dataframe["close"].shift(1).to_numpy())[1:]
        ann = sqrt(365 * candles_pd)
        return float(np.std(log_returns[-(period * candles_pd) :]) * ann)

    @staticmethod
    def _validate_no_nan(obj: IndicatorSet) -> None:
        for field_name, value in asdict(obj).items():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                raise InsufficientKlineDataError(f"{field_name} is {value}")

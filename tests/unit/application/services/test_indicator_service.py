import random
from unittest.mock import AsyncMock, MagicMock

import pytest

from source.application.exceptions import InsufficientKlineDataError, UnsupportedIntervalError
from source.application.services.indicator_service import IndicatorService
from source.domain.value_objects import Symbol
from source.settings import PionexSettings
from tests.fixtures.factories import make_candles


@pytest.fixture
def indicator_service() -> IndicatorService:
    settings = MagicMock(spec=PionexSettings)
    settings.kline_interval = "4H"
    settings.limit = 500
    market_data = AsyncMock()
    return IndicatorService(settings=settings, market_data=market_data)


async def test_unsupported_interval_raises(indicator_service: IndicatorService) -> None:
    indicator_service._settings.kline_interval = "5M"  # noqa: SLF001
    with pytest.raises(UnsupportedIntervalError):
        await indicator_service.compute(Symbol.BTC)


async def test_insufficient_candles_raises(indicator_service: IndicatorService) -> None:
    indicator_service._market_data.get_candles.return_value = []  # type: ignore[attr-defined]  # noqa: SLF001
    with pytest.raises(InsufficientKlineDataError):
        await indicator_service.compute(Symbol.BTC)


async def test_timestamp_ms_gives_correct_year(indicator_service: IndicatorService) -> None:
    candles = make_candles(200, interval_minutes=240, base_time_ms=1_748_995_200_000)
    indicator_service._market_data.get_candles.return_value = candles  # type: ignore[attr-defined]  # noqa: SLF001
    result = await indicator_service.compute(Symbol.BTC)
    assert result.as_of.tzinfo is not None
    assert result.as_of.year == 2025


async def test_out_of_order_candles_produce_same_result(indicator_service: IndicatorService) -> None:
    candles = make_candles(200, interval_minutes=240)
    shuffled = candles[:]
    random.shuffle(shuffled)

    indicator_service._market_data.get_candles.return_value = candles  # type: ignore[attr-defined]  # noqa: SLF001
    result_sorted = await indicator_service.compute(Symbol.BTC)

    indicator_service._market_data.get_candles.return_value = shuffled  # type: ignore[attr-defined]  # noqa: SLF001
    result_shuffled = await indicator_service.compute(Symbol.BTC)

    assert result_sorted.adx14 == pytest.approx(result_shuffled.adx14, rel=1e-9)
    assert result_sorted.sma50 == pytest.approx(result_shuffled.sma50, rel=1e-9)
    assert result_sorted.as_of == result_shuffled.as_of


async def test_nan_raises_insufficient_not_silently_passes(indicator_service: IndicatorService) -> None:
    candles = make_candles(50, interval_minutes=240)
    indicator_service._market_data.get_candles.return_value = candles  # type: ignore[attr-defined]  # noqa: SLF001
    with pytest.raises(InsufficientKlineDataError):
        await indicator_service.compute(Symbol.BTC)


async def test_volatility_shape_no_raise_at_minimum(indicator_service: IndicatorService) -> None:
    candles = make_candles(186, interval_minutes=240)
    indicator_service._market_data.get_candles.return_value = candles  # type: ignore[attr-defined]  # noqa: SLF001
    result = await indicator_service.compute(Symbol.BTC)
    assert result.realized_vol_1d >= 0.0
    assert result.realized_vol_7d >= 0.0
    assert result.realized_vol_30d >= 0.0

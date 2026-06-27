import random

import pytest

from source.application.exceptions import InsufficientKlineDataError, UnsupportedIntervalError
from source.application.services.indicator_service import IndicatorService
from tests.fixtures.factories import make_candles


def test_indicator_service_importable() -> None:
    svc = IndicatorService()
    assert hasattr(svc, "compute")


def test_unsupported_interval_raises() -> None:
    svc = IndicatorService()
    with pytest.raises(UnsupportedIntervalError):
        svc.compute([], "5M")


def test_insufficient_candles_raises() -> None:
    svc = IndicatorService()
    with pytest.raises(InsufficientKlineDataError):
        svc.compute([], "4H")


def test_timestamp_ms_gives_correct_year() -> None:
    svc = IndicatorService()
    candles = make_candles(200, interval_minutes=240, base_time_ms=1_748_995_200_000)
    result = svc.compute(candles, "4H")
    assert result.as_of.tzinfo is not None
    assert result.as_of.year == 2025


def test_out_of_order_candles_produce_same_result() -> None:
    svc = IndicatorService()
    candles = make_candles(200, interval_minutes=240)
    shuffled = candles[:]
    random.shuffle(shuffled)

    result_sorted = svc.compute(candles, "4H")
    result_shuffled = svc.compute(shuffled, "4H")

    assert result_sorted.adx14 == pytest.approx(result_shuffled.adx14, rel=1e-9)
    assert result_sorted.sma50 == pytest.approx(result_shuffled.sma50, rel=1e-9)
    assert result_sorted.as_of == result_shuffled.as_of


def test_nan_raises_insufficient_not_silently_passes() -> None:
    svc = IndicatorService()
    candles = make_candles(50, interval_minutes=240)
    with pytest.raises(InsufficientKlineDataError):
        svc.compute(candles, "4H")


def test_volatility_shape_no_raise_at_minimum() -> None:
    svc = IndicatorService()
    candles = make_candles(186, interval_minutes=240)
    result = svc.compute(candles, "4H")
    assert result.realized_vol_1d >= 0.0
    assert result.realized_vol_7d >= 0.0
    assert result.realized_vol_30d >= 0.0

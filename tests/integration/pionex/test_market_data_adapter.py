from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from source.domain.entities import Candle, FundingRate, LiquidationEstimate, OpenInterest, ProposedGridParams
from source.domain.exceptions import InvalidCandleDataError, InvalidFundingRateDataError, InvalidOpenInterestDataError
from source.domain.value_objects import GridType, Symbol, Trend
from source.infrastructure.exceptions import HttpRequestError
from source.infrastructure.http.pionex.models.models import (
    CandleDataObject,
    CandleItem,
    CheckFuturesGridParametersDataObject,
    CheckFuturesGridParametersResponseSchema,
    ErrorResponse,
    FundingRateObject,
    GetCandlesResponseSchema,
    GetFundingRatesResponseSchema,
    GetOpenInterestsResponseSchema,
    OpenInterestItem,
    OpenInterestsDataObject,
    RateItem,
)
from source.infrastructure.http.pionex.pionex_http_client import PionexHTTPClient
from tests.fixtures.factories import load_fixture


PIONEX_BASE = "https://api.pionex.com"


@pytest.fixture
def client() -> PionexHTTPClient:
    return PionexHTTPClient(base_url=PIONEX_BASE)


@pytest.fixture
def proposal() -> ProposedGridParams:
    return ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.LONG,
        grid_type=GridType.GEOMETRIC,
    )


async def test_check_grid_params_returns_estimate(client: PionexHTTPClient, proposal: ProposedGridParams) -> None:
    response = CheckFuturesGridParametersResponseSchema(
        result=True,
        timestamp=1000,
        data=CheckFuturesGridParametersDataObject(
            estimate_liquidation_price_up=110_000.0,
            estimate_liquidation_price_down=80_000.0,
        ),
    )
    with patch.object(client, "post", new=AsyncMock(return_value=response)):
        est = await client.check_grid_params(proposal)

    assert isinstance(est, LiquidationEstimate)
    assert est.estimate_liquidation_price_up == pytest.approx(110_000.0)
    assert est.estimate_liquidation_price_down == pytest.approx(80_000.0)


async def test_check_grid_params_zero_up_means_no_risk(client: PionexHTTPClient, proposal: ProposedGridParams) -> None:
    response = CheckFuturesGridParametersResponseSchema(
        result=True,
        timestamp=1000,
        data=CheckFuturesGridParametersDataObject(
            estimate_liquidation_price_up=0.0,
            estimate_liquidation_price_down=80_000.0,
        ),
    )

    with patch.object(client, "post", new=AsyncMock(return_value=response)):
        est = await client.check_grid_params(proposal)

    assert est.estimate_liquidation_price_up == 0.0
    assert est.buffer_multiplier_up is None


async def test_check_grid_params_api_error_raises(client: PionexHTTPClient, proposal: ProposedGridParams) -> None:
    response = ErrorResponse(result=False, timestamp=1000, code="E001", message="less than min investment")

    with patch.object(client, "post", new=AsyncMock(return_value=response)), pytest.raises(HttpRequestError):
        await client.check_grid_params(proposal)


async def test_get_candles_returns_list(client: PionexHTTPClient) -> None:
    response = GetCandlesResponseSchema(
        result=True,
        timestamp=1000,
        data=CandleDataObject(
            candles=[
                CandleItem(time=1700000000000, open=96000.0, high=97000.0, low=95000.0, close=96500.0, volume=100.0)
            ]
        ),
    )

    with patch.object(client, "get", new=AsyncMock(return_value=response)):
        result = await client.get_candles(Symbol.BTC, interval="4H", limit=1)

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Candle)
    assert result[0].open == pytest.approx(96_000.0)


async def test_get_funding_rates_returns_list(client: PionexHTTPClient) -> None:
    response = GetFundingRatesResponseSchema(
        result=True,
        timestamp=1000,
        data=FundingRateObject(
            symbol="USDT_BTC_REPR",
            rates=[
                RateItem(funding_rate=0.0001, funding_time=1700000000000),
                RateItem(funding_rate=-0.0002, funding_time=1700028800000),
            ],
        ),
    )

    with patch.object(client, "get", new=AsyncMock(return_value=response)):
        result = await client.get_funding_rates(Symbol.BTC, limit=2)

    assert len(result) == 2
    assert isinstance(result[0], FundingRate)
    assert result[0].rate == pytest.approx(0.0001)


async def test_get_open_interest_returns_open_interest(client: PionexHTTPClient) -> None:
    response = GetOpenInterestsResponseSchema(
        result=True,
        timestamp=1000,
        data=OpenInterestsDataObject(
            open_interests=[
                OpenInterestItem(symbol=Symbol.BTC.value, open_interest=500_000_000.0),
            ]
        ),
    )

    with patch.object(client, "get", new=AsyncMock(return_value=response)):
        result = await client.get_open_interest(Symbol.BTC)

    assert isinstance(result, OpenInterest)
    assert result.open_interest == pytest.approx(500_000_000.0)


async def test_get_open_interest_symbol_not_found_raises(client: PionexHTTPClient) -> None:
    response = GetOpenInterestsResponseSchema(
        result=True,
        timestamp=1000,
        data=OpenInterestsDataObject(
            open_interests=[
                OpenInterestItem(symbol="ETH_PERP", open_interest=100.0),
            ]
        ),
    )

    with patch.object(client, "get", new=AsyncMock(return_value=response)), pytest.raises(InvalidOpenInterestDataError):
        await client.get_open_interest(Symbol.BTC)


@respx.mock
async def test_get_candles_parses_real_response_shape(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/klines").mock(
        return_value=httpx.Response(200, json=load_fixture("klines_btc_4h.json"))
    )
    candles = await client.get_candles(Symbol.BTC, interval="4H", limit=200)
    assert len(candles) > 0
    assert all(isinstance(c, Candle) for c in candles)
    assert candles[0].time.tzinfo is not None
    assert all(c.high >= c.low for c in candles)
    assert all(c.open > 0 for c in candles)


@respx.mock
async def test_get_candles_raises_on_result_false(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/klines").mock(
        return_value=httpx.Response(
            200, json={"result": False, "code": "RATE_LIMIT", "message": "rate limited", "timestamp": 0}
        )
    )

    with pytest.raises((HttpRequestError, InvalidCandleDataError)):
        await client.get_candles(Symbol.BTC, interval="4H", limit=200)


@respx.mock
async def test_get_candles_raises_on_missing_field(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/klines").mock(
        return_value=httpx.Response(200, json={"result": True, "timestamp": 0, "data": {"klines": [{"time": 123}]}})
    )

    with pytest.raises(InvalidCandleDataError):
        await client.get_candles(Symbol.BTC, interval="4H", limit=200)


@respx.mock
async def test_get_candles_empty_list_returns_empty(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/klines").mock(
        return_value=httpx.Response(200, json={"result": True, "timestamp": 0, "data": {"klines": []}})
    )
    result = await client.get_candles(Symbol.BTC, interval="4H", limit=200)
    assert result == []


@respx.mock
async def test_get_funding_rates_parses_real_response_shape(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/fundingRates").mock(
        return_value=httpx.Response(200, json=load_fixture("funding_rates_btc.json"))
    )
    rates = await client.get_funding_rates(Symbol.BTC, limit=20)
    assert len(rates) > 0
    assert all(isinstance(r, FundingRate) for r in rates)
    assert rates[0].time.tzinfo is not None


@respx.mock
async def test_get_funding_rates_raises_on_result_false(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/fundingRates").mock(
        return_value=httpx.Response(200, json={"result": False, "code": "ERROR", "message": "fail", "timestamp": 0})
    )

    with pytest.raises((HttpRequestError, InvalidFundingRateDataError)):
        await client.get_funding_rates(Symbol.BTC, limit=20)


@respx.mock
async def test_get_funding_rates_raises_on_empty_list(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/fundingRates").mock(
        return_value=httpx.Response(
            200, json={"result": True, "timestamp": 0, "data": {"symbol": "USDT_BTC_REPR", "rates": []}}
        )
    )

    with pytest.raises(InvalidFundingRateDataError):
        await client.get_funding_rates(Symbol.BTC, limit=20)


@respx.mock
async def test_get_open_interest_parses_real_response_shape(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/openInterests").mock(
        return_value=httpx.Response(200, json=load_fixture("open_interest_btc.json"))
    )
    oi = await client.get_open_interest(Symbol.BTC)
    assert isinstance(oi, OpenInterest)
    assert oi.open_interest > 0


@respx.mock
async def test_get_open_interest_raises_on_result_false(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/openInterests").mock(
        return_value=httpx.Response(200, json={"result": False, "code": "ERROR", "message": "fail", "timestamp": 0})
    )

    with pytest.raises((HttpRequestError, InvalidOpenInterestDataError)):
        await client.get_open_interest(Symbol.BTC)


@respx.mock
async def test_get_open_interest_raises_when_symbol_not_found(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/openInterests").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": True,
                "timestamp": 0,
                "data": {"openInterests": [{"symbol": "ETH_PERP", "openInterest": 100.0}]},
            },
        )
    )

    with pytest.raises(InvalidOpenInterestDataError):
        await client.get_open_interest(Symbol.BTC)


@respx.mock
async def test_get_open_interest_raises_on_empty_list(client: PionexHTTPClient) -> None:
    respx.get(f"{PIONEX_BASE}/api/v1/market/openInterests").mock(
        return_value=httpx.Response(200, json={"result": True, "timestamp": 0, "data": {"openInterests": []}})
    )

    with pytest.raises(InvalidOpenInterestDataError):
        await client.get_open_interest(Symbol.BTC)

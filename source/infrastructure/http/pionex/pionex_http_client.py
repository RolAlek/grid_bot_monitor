import time
from datetime import UTC, datetime

from httpx import Auth

from source.domain.entities import Candle, FundingRate, LiquidationEstimate, OpenInterest, ProposedGridParams
from source.domain.exceptions import (
    InvalidCandleDataError,
    InvalidFundingRateDataError,
    InvalidLiquidationEstimateDataError,
    InvalidOpenInterestDataError,
)
from source.domain.value_objects import Symbol
from source.infrastructure.exceptions import HttpRequestError, HttpValidationError
from source.infrastructure.http.base import BaseHTTPClient
from source.infrastructure.http.pionex.models.models import (
    CheckFuturesGridParametersRequestSchema,
    CheckFuturesGridParametersResponseSchema,
    DataObject,
    ErrorResponse,
    GetCandlesResponseSchema,
    GetFundingRatesResponseSchema,
    GetOpenInterestsResponseSchema,
)


class PionexHTTPClient(BaseHTTPClient):
    def __init__(
        self,
        base_url: str,
        timeout: float | None = None,
        auth: Auth | None = None,
    ) -> None:
        super().__init__(base_url, timeout, auth)

    async def check_grid_params(self, parameters: ProposedGridParams) -> LiquidationEstimate:
        payload = CheckFuturesGridParametersRequestSchema(
            base=f"{parameters.symbol.get_base}.{parameters.symbol.get_type}",
            quote=parameters.symbol.get_quote,
            bu_order_data=DataObject(
                top=str(parameters.top),
                bottom=str(parameters.bottom),
                row=parameters.grid_levels,
                grid_type=parameters.grid_type,
                trend=parameters.trend,
                leverage=parameters.leverage,
                quote_investment=str(parameters.quote_investment),
            ),
        )

        response = await self.post(
            path="/api/v1/bot/orders/futuresGrid/checkParams",
            payload=payload,
            params={"timestamp": str(int(time.time() * 1000))},
            request_model=CheckFuturesGridParametersRequestSchema,
            response_model=CheckFuturesGridParametersResponseSchema,
            error_model=ErrorResponse,
            by_alias=True,
        )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result or not response.data:
            raise InvalidLiquidationEstimateDataError("Invalid check grid parameters response from Pionex.")

        data = response.data

        return LiquidationEstimate(
            proposal=parameters,
            estimate_liquidation_price_up=data.estimate_liquidation_price_up,
            estimate_liquidation_price_down=data.estimate_liquidation_price_down,
        )

    async def get_candles(self, symbol: Symbol, interval: str, limit: int) -> list[Candle]:
        try:
            response = await self.get(
                path="/api/v1/market/klines",
                response_model=GetCandlesResponseSchema,
                error_model=ErrorResponse,
                params={"symbol": symbol, "interval": interval, "limit": limit},
            )
        except HttpValidationError as error:
            raise InvalidCandleDataError(f"Malformed candle data from Pionex: {error}", error) from error

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.data:
            raise InvalidCandleDataError("Empty candles response from Pionex")

        return [
            Candle(
                time=datetime.fromtimestamp(candle.time / 1_000, UTC),
                open=candle.open,
                close=candle.close,
                high=candle.high,
                low=candle.low,
                volume=candle.volume,
            )
            for candle in response.data.candles
        ]

    async def get_funding_rates(self, symbol: Symbol, limit: int) -> list[FundingRate]:
        try:
            response = await self.get(
                path="/api/v1/market/fundingRates",
                response_model=GetFundingRatesResponseSchema,
                error_model=ErrorResponse,
                params={"symbol": symbol, "limit": limit},
            )
        except HttpValidationError as error:
            raise InvalidFundingRateDataError(f"Malformed funding rate data from Pionex: {error}", error) from error

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.data or not response.data.rates:
            raise InvalidFundingRateDataError("Empty funding rates response from Pionex")

        return [
            FundingRate(rate=rate.funding_rate, time=datetime.fromtimestamp(rate.funding_time / 1_000, UTC))
            for rate in response.data.rates
        ]

    async def get_open_interest(self, symbol: Symbol) -> OpenInterest:
        response = await self.get(
            path="/api/v1/market/openInterests",
            response_model=GetOpenInterestsResponseSchema,
            error_model=ErrorResponse,
        )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.data or not response.data.open_interests:
            raise InvalidOpenInterestDataError("Empty open interest data response from Pionex")

        for oi in response.data.open_interests:
            if oi.symbol == symbol.value:
                if not oi.open_interest:
                    raise InvalidOpenInterestDataError("Empty open interest value from Pionex response")

                return OpenInterest(
                    symbol=Symbol(oi.symbol) if oi.symbol else symbol,
                    open_interest=oi.open_interest,
                )

        raise InvalidOpenInterestDataError(f"No data matching the {symbol.value}")

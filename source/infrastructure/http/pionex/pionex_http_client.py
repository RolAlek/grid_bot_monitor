import time
from datetime import UTC, datetime

from httpx import Auth

from source.constants import CHECK_GRID_URL, CREATE_GRID_URL
from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingRate,
    Grid,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
)
from source.domain.exceptions import (
    InvalidCandleDataError,
    InvalidFundingRateDataError,
    InvalidGridParamsError,
    InvalidLiquidationEstimateDataError,
    InvalidOpenInterestDataError,
)
from source.domain.value_objects import GridLaunchStatus, GridType, Symbol, Trend
from source.infrastructure.exceptions import HttpRequestError, HttpValidationError
from source.infrastructure.http.base import BaseHTTPClient
from source.infrastructure.http.pionex.models.models import (
    BuOrderDataObject,
    CheckFuturesGridParametersRequestSchema,
    CheckFuturesGridParametersResponseSchema,
    CreateGridBotRequestSchema,
    CreateGridBotResponseSchema,
    DataObject,
    ErrorResponse,
    GetCandlesResponseSchema,
    GetFundingRatesResponseSchema,
    GetOpenInterestsResponseSchema,
    SLTPType,
)
from source.utils.ensure import ensure


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
            base=f"{parameters.symbol.base}.{parameters.symbol.type_}",
            quote=parameters.symbol.quote,
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
            path=CHECK_GRID_URL,
            payload=payload,
            params={"timestamp": self._calculate_timestamp()},
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

    async def place_grid(self, verdict: DecisionVerdict) -> Grid:
        params = verdict.suggested_parameters

        if not params:
            raise InvalidGridParamsError("Invalid decision verdict. No parameters provided.")

        payload = CreateGridBotRequestSchema(
            base=params.symbol.base,
            quote=params.symbol.quote,
            bu_order_data=BuOrderDataObject(
                top=params.top,
                bottom=params.bottom,
                row=params.grid_levels,
                grid_type=params.grid_type,
                trend=params.trend,
                leverage=params.leverage,
                quote_investment=params.quote_investment,
                loss_stop_type=SLTPType.PRICE,
                loss_stop=params.stop_loss,
                profit_stop_type=SLTPType.PRICE,
                profit_stop=params.take_profit,
            ),
        )

        response = await self.post(
            path=CREATE_GRID_URL,
            payload=payload,
            params={"timestamp": self._calculate_timestamp()},
            request_model=CreateGridBotRequestSchema,
            response_model=CreateGridBotResponseSchema,
            error_model=ErrorResponse,
            by_alias=True,
            exclude_none=True,
        )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result or not response.data:
            raise InvalidLiquidationEstimateDataError("Invalid check grid parameters response from Pionex.")

        return Grid(
            symbol=params.symbol,
            top=response.data.top,
            bottom=response.data.bottom,
            levels=response.data.row,
            trend=Trend(response.data.trend),
            grid_type=GridType(response.data.grid_type),
            leverage=response.data.leverage,
            investment=response.data.leverage,
            status=GridLaunchStatus.RUNNING,
            created_at=datetime.now(UTC),
            decision_verdict_oid=ensure(verdict.oid),
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

    async def get_funding_rates(self, symbol: Symbol, limit: int = 1) -> list[FundingRate]:
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

    @staticmethod
    def _calculate_timestamp() -> str:
        return str(int(time.time() * 1000))

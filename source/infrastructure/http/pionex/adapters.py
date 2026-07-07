import asyncio
import time
from datetime import UTC, datetime
from logging import WARNING
from typing import Any

import structlog
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from source.application.ports import GridPort, MarketDataPort
from source.constants import (
    BOT_ORDERS_LIST_URL,
    CHECK_GRID_URL,
    CREATE_GRID_URL,
    FUTURES_GRID_CANCEL_URL,
    FUTURES_GRID_ORDER_URL,
)
from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingRate,
    LiquidationEstimate,
    OpenInterest,
    ProposedGridParams,
)
from source.domain.entities.monitoring import Bot, BotOrderSnapshot
from source.domain.exceptions import (
    CandleDataUnavailableError,
    FundingRateDataUnavailableError,
    GridOrderDataUnavailableError,
    InvalidGridParamsError,
    LiquidationEstimateDataUnavailableError,
    OpenInterestDataUnavailableError,
)
from source.domain.value_objects import GridLaunchStatus, GridType, Symbol, Trend
from source.infrastructure.exceptions import HttpRequestError, HttpValidationError, RetryableHttpError
from source.infrastructure.http.pionex.models import (
    BaseResponse,
    BotOrderItem,
    BotOrderListResponseSchema,
    BuOrderDataObject,
    CancelFuturesGridRequestSchema,
    CheckFuturesGridParametersRequestSchema,
    CheckFuturesGridParametersResponseSchema,
    CreateGridBotRequestSchema,
    CreateGridBotResponseSchema,
    DataObject,
    ErrorResponse,
    FuturesGridOrderResponseSchema,
    GetCandlesResponseSchema,
    GetFundingRatesResponseSchema,
    GetOpenInterestsResponseSchema,
    SLTPType,
)
from source.infrastructure.http.pionex.pionex_http_client import PionexHTTPClient, pionex_timestamp_ms
from source.utils.ensure import ensure


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

API_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(RetryableHttpError),
    before_sleep=before_sleep_log(logger, WARNING),
    reraise=True,
)

_API_SEMAPHORE = asyncio.Semaphore(5)


class PionexGridAdapter(GridPort):
    def __init__(self, client: PionexHTTPClient) -> None:
        self._client = client

    @API_RETRY
    async def get_futures_grid_order(self, bu_order_id: str) -> BotOrderSnapshot:
        async with _API_SEMAPHORE:
            response = await self._client.get(
                path=FUTURES_GRID_ORDER_URL,
                response_model=FuturesGridOrderResponseSchema,
                error_model=ErrorResponse,
                params={"buOrderId": bu_order_id, "timestamp": pionex_timestamp_ms()},
            )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result or not response.data:
            raise GridOrderDataUnavailableError(f"Empty response for futures grid order {bu_order_id}")

        data = response.data.bu_order_data
        return BotOrderSnapshot(
            profit_reduce=data.profit_reduce or 0.0,
            funding_fee_payment=data.funding_fee_payment or 0.0,
            quote_investment=data.quote_investment,
            position=data.position,
            row=data.row,
            per_volume=data.per_volume,
            trend=Trend(data.trend),
            leverage=data.leverage,
            estimate_liquidation_price_up=data.estimate_liquidation_price_up,
            estimate_liquidation_price_down=data.estimate_liquidation_price_down,
        )

    @API_RETRY
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

        async with _API_SEMAPHORE:
            response = await self._client.post(
                path=CHECK_GRID_URL,
                payload=payload,
                params={"timestamp": pionex_timestamp_ms()},
                request_model=CheckFuturesGridParametersRequestSchema,
                response_model=CheckFuturesGridParametersResponseSchema,
                error_model=ErrorResponse,
                by_alias=True,
            )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result or not response.data:
            raise LiquidationEstimateDataUnavailableError("Invalid check grid parameters response from Pionex.")

        data = response.data
        return LiquidationEstimate(
            proposal=parameters,
            estimate_liquidation_price_up=data.estimate_liquidation_price_up,
            estimate_liquidation_price_down=data.estimate_liquidation_price_down,
        )

    @API_RETRY
    async def place_grid(self, verdict: DecisionVerdict) -> Bot:
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

        async with _API_SEMAPHORE:
            response = await self._client.post(
                path=CREATE_GRID_URL,
                payload=payload,
                params={"timestamp": pionex_timestamp_ms()},
                request_model=CreateGridBotRequestSchema,
                response_model=CreateGridBotResponseSchema,
                error_model=ErrorResponse,
                by_alias=True,
                exclude_none=True,
            )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result or not response.data:
            raise LiquidationEstimateDataUnavailableError("Invalid create grid response from Pionex.")

        return Bot(
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

    @API_RETRY
    async def get_running_bots(
        self,
        status: str = "running",
        bu_order_types: list[str] | None = None,
    ) -> list[BotOrderItem]:
        if bu_order_types is None:
            bu_order_types = ["futures_grid"]

        params: dict[str, Any] = {"status": status, "timestamp": pionex_timestamp_ms()}
        for bot_type in bu_order_types:
            params.setdefault("buOrderTypes", []).append(bot_type)  # type: ignore[union-attr]

        async with _API_SEMAPHORE:
            response = await self._client.get(
                path=BOT_ORDERS_LIST_URL,
                response_model=BotOrderListResponseSchema,
                error_model=ErrorResponse,
                params=params,
            )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result or not response.data:
            return []
        return response.data.results

    @API_RETRY
    async def cancel_futures_grid(
        self,
        bu_order_id: str,
        close_note: str | None = None,
    ) -> bool:
        payload = CancelFuturesGridRequestSchema(
            bu_order_id=bu_order_id,
            close_note=close_note,
        )

        async with _API_SEMAPHORE:
            response = await self._client.post(
                path=FUTURES_GRID_CANCEL_URL,
                payload=payload,
                params={"timestamp": pionex_timestamp_ms()},
                request_model=CancelFuturesGridRequestSchema,
                response_model=BaseResponse,
                error_model=ErrorResponse,
                by_alias=True,
            )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.result:
            raise HttpRequestError(message=f"Pionex API returned result=false for cancel {bu_order_id}")

        return response.result


class PionexMarketDataAdapter(MarketDataPort):
    _OI_CACHE_TTL: float = 60.0  # seconds — one batch of symbols completes in << 60s

    def __init__(self, client: PionexHTTPClient) -> None:
        self._client = client
        self._oi_cache: tuple[float, dict[Symbol, OpenInterest]] | None = None

    @API_RETRY
    async def get_candles(self, symbol: Symbol, interval: str, limit: int) -> list[Candle]:
        async with _API_SEMAPHORE:
            try:
                response = await self._client.get(
                    path="/api/v1/market/klines",
                    response_model=GetCandlesResponseSchema,
                    error_model=ErrorResponse,
                    params={"symbol": symbol, "interval": interval, "limit": limit},
                )
            except HttpValidationError as error:
                raise CandleDataUnavailableError(
                    f"Malformed candle data from Pionex: {error}", original_error=error
                ) from error

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.data:
            raise CandleDataUnavailableError("Empty candles response from Pionex")

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
        async with _API_SEMAPHORE:
            try:
                response = await self._client.get(
                    path="/api/v1/market/fundingRates",
                    response_model=GetFundingRatesResponseSchema,
                    error_model=ErrorResponse,
                    params={"symbol": symbol, "limit": limit},
                )
            except HttpValidationError as error:
                raise FundingRateDataUnavailableError(
                    f"Malformed funding rate data from Pionex: {error}", original_error=error
                ) from error

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.data or not response.data.rates:
            raise FundingRateDataUnavailableError("Empty funding rates response from Pionex")

        return [
            FundingRate(rate=rate.funding_rate, time=datetime.fromtimestamp(rate.funding_time / 1_000, UTC))
            for rate in response.data.rates
        ]

    @API_RETRY
    async def get_open_interest(self, symbol: Symbol) -> OpenInterest:
        now = time.monotonic()
        if self._oi_cache and (now - self._oi_cache[0]) < self._OI_CACHE_TTL:
            cached = self._oi_cache[1].get(symbol)
            if cached is not None:
                return cached

        async with _API_SEMAPHORE:
            response = await self._client.get(
                path="/api/v1/market/openInterests",
                response_model=GetOpenInterestsResponseSchema,
                error_model=ErrorResponse,
            )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message or response.code)

        if not response.data or not response.data.open_interests:
            raise OpenInterestDataUnavailableError("Empty open interest data response from Pionex")

        parsed: dict[Symbol, OpenInterest] = {}
        for oi in response.data.open_interests:
            if not oi.open_interest:
                continue
            try:
                parsed_key = Symbol(oi.symbol) if oi.symbol else None
            except ValueError:
                logger.warning("Unknown symbol in OI response", raw_symbol=oi.symbol)
                continue

            if parsed_key is None:
                continue

            parsed[parsed_key] = OpenInterest(
                symbol=parsed_key,
                open_interest=oi.open_interest,
            )
        self._oi_cache = (now, parsed)

        if (result := parsed.get(symbol)) is None:
            raise OpenInterestDataUnavailableError(f"No data matching the {symbol.value}")

        return result

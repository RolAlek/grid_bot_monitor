from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from source.domain.value_objects import GridType, Trend
from source.infrastructure.http.pionex.models.types import StringFloat


class SLTPType(StrEnum):
    PRICE = "price"
    PROFIT_AMOUNT = "profit_amount"
    PROFIT_RATIO = "profit_ratio"
    PRICE_LIMIT = "price_limit"


class CateType(StrEnum):
    FULLY_HEDGING = "FULLY_HEDGING"
    LOAN_GRID = "LOAN_GRID"
    LEVERAGE_GRID = "LEVERAGE_GRID"
    FUTURE_GRID_COIN_MARGINED = "FUTURE_GRID_COIN_MARGINED"


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class BaseResponse(BaseSchema):
    result: bool
    timestamp: int


class SuccessResponse[TData: BaseModel](BaseResponse):
    data: TData | None = None


class ErrorResponse(BaseResponse):
    code: str
    message: str | None = None


class DataObject(BaseSchema):
    top: str
    bottom: str
    row: int = Field(ge=2, le=500)
    grid_type: GridType
    trend: Trend
    leverage: int = Field(ge=1, le=3)
    quote_investment: str

    @model_validator(mode="after")
    def validate_top_and_bottom(self) -> Self:
        if float(self.top) <= float(self.bottom):
            raise ValueError("Top must be greater then bottom")

        return self


class CheckFuturesGridParametersRequestSchema(BaseSchema):
    model_config = ConfigDict(populate_by_name=True)

    base: str
    quote: str
    bu_order_data: DataObject = Field(alias="buOrderData")


class CheckFuturesGridParametersDataObject(BaseSchema):
    min_investment: str | None = None
    max_investment: str | None = None
    slippage: str | None = None
    estimate_per_volume: str | None = None
    estimate_investment: str | None = None
    estimate_extra_margin: str | None = None
    estimate_fee: str | None = None
    estimate_position_occupy_margin: str | None = None
    estimate_order_occupy_margin: str | None = None
    estimate_position: str | None = None

    estimate_liquidation_price_up: StringFloat
    estimate_liquidation_price_down: StringFloat


class CheckFuturesGridParametersResponseSchema(SuccessResponse[CheckFuturesGridParametersDataObject]): ...


class CandleItem(BaseSchema):
    time: int
    open: float
    close: float
    high: float
    low: float
    volume: float


class CandleDataObject(BaseSchema):
    candles: list[CandleItem] = Field(alias="klines")


class GetCandlesResponseSchema(SuccessResponse[CandleDataObject]): ...


class RateItem(BaseSchema):
    funding_rate: float = Field(alias="fundingRate")
    funding_time: int = Field(alias="fundingTime")


class FundingRateObject(BaseSchema):
    symbol: str
    rates: list[RateItem]


class GetFundingRatesResponseSchema(SuccessResponse[FundingRateObject]): ...


class OpenInterestItem(BaseSchema):
    symbol: str | None = None
    open_interest: float | None = Field(None, alias="openInterest")


class OpenInterestsDataObject(BaseSchema):
    open_interests: list[OpenInterestItem] = Field(default_factory=list, alias="openInterests")


class GetOpenInterestsResponseSchema(SuccessResponse[OpenInterestsDataObject]): ...


class BuOrderDataObject(CamelSchema):
    top: float = Field(description="Grid upper price")
    bottom: float = Field(description="Grid lower price")
    row: int = Field(description="Number of grid levels")
    grid_type: GridType
    trend: Trend
    leverage: int
    extra_margin: str | None = None
    quote_investment: float
    condition: float | None = None
    condition_direction: Literal["1", "-1"] | None = None

    loss_stop_type: SLTPType | None = None
    loss_stop: float | None = None
    loss_stop_delay: int | None = None
    loss_stop_high: str | None = None
    loss_stop_limit_price: str | None = None
    loss_stop_limit_high_price: str | None = None

    profit_stop_type: SLTPType | None = None
    profit_stop: float | None = None
    profit_stor_delay: int | None = None
    profit_stop_limit_price: str | None = None

    share_ratio: str | None = None
    invest_coin: str | None = None
    investment_from: Literal["USER", "FUTURE_GRID_BONUS"] = "USER"
    ui_invest_coin: str | None = None
    ui_extra_data: str | None = None
    slippage: str | None = None
    bonus_id: UUID | None = None
    cate_type: CateType | None = None

    moving_indicator_type: str | None = None
    moving_indicator_interval: str | None = None
    moving_indicator_param: str | None = None
    moving_trailing_up_param: str | None = None
    moving_top: str | None = None
    moving_bottom: str | None = None
    enable_follow_closed: str | None = None


class CreateGridBotRequestSchema(CamelSchema):
    base: str = Field(description="Base currency", examples=["BTC", "ETH"])
    quote: str = Field(description="Quote currency", examples=["USDT"])

    copy_from: str | None = None
    copy_type: str | None = None
    copy_bot_order_id: str | None = None

    bu_order_data: BuOrderDataObject


class CreateGridBotResponseSchema(SuccessResponse[BuOrderDataObject]): ...

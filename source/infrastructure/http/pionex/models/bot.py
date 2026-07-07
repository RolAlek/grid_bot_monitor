from typing import Literal, Self
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from source.domain.exceptions import InvalidGridParamsError
from source.domain.value_objects import GridType, Trend
from source.infrastructure.http.pionex.models.base import BaseSchema, CamelSchema, CateType, SLTPType, SuccessResponse
from source.infrastructure.http.pionex.models.types import StringFloat


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
            raise InvalidGridParamsError("Top must be greater than bottom")
        return self


class CheckFuturesGridParametersRequestSchema(BaseSchema):
    model_config = ConfigDict(populate_by_name=True)
    base: str
    quote: str
    bu_order_data: DataObject = Field(alias="buOrderData")


class CheckFuturesGridParametersDataObject(CamelSchema):
    estimate_extra_margin: str | None = None
    estimate_fee: str | None = None
    estimate_position: str | None = None
    slippage: str | None = None
    estimate_investment: str | None = None
    estimate_position_occupy_margin: str | None = None
    estimate_liquidation_price_down: StringFloat
    min_investment: str | None = None
    estimate_liquidation_price_up: StringFloat
    max_investment: str | None = None
    estimate_order_occupy_margin: str | None = None
    estimate_per_volume: str | None = None


class CheckFuturesGridParametersResponseSchema(SuccessResponse[CheckFuturesGridParametersDataObject]): ...


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


class BotOrderItem(CamelSchema):
    bu_order_type: str
    bu_order_id: str
    base: str
    quote: str
    status: str
    create_time: int
    close_time: int | None = None


class BotOrderListData(CamelSchema):
    next_page_token: str | None = None
    previous_page_token: str | None = None
    results: list[BotOrderItem] = Field(default_factory=list)


class BotOrderListResponseSchema(SuccessResponse[BotOrderListData]): ...


class FuturesGridOrderDataSchema(CamelSchema):
    status: str
    reason_by: str | None = None
    top: str
    bottom: str
    row: int
    grid_type: str
    open_price: str | None = None
    trend: str
    leverage: int
    extra_margin: str | None = None
    quote_investment: float | None = None
    per_volume: float | None = None
    position: float | None = None
    position_open_price: str | None = None
    margin_balance: str | None = None
    extra_balance: str | None = None
    liquidation_triggered: bool | None = None
    liquidation_price: str | None = None
    estimate_liquidation_price_up: float | None = None
    estimate_liquidation_price_down: float | None = None
    loss_stop_type: str | None = None
    loss_stop: str | None = None
    profit_stop_type: str | None = None
    profit_stop: str | None = None
    risk_status: str = "TRADING"
    profit_reduce: float | None = None
    funding_fee_payment: float | None = None


class FuturesGridOrderSchema(CamelSchema):
    bu_order_id: str
    base: str
    quote: str
    status: str
    create_time: int
    bu_order_data: FuturesGridOrderDataSchema


class FuturesGridOrderResponseSchema(SuccessResponse[FuturesGridOrderSchema]): ...


class CancelFuturesGridRequestSchema(CamelSchema):
    bu_order_id: str
    close_note: str | None = None
    close_sell_model: str | None = None
    immediate: bool | None = None
    close_slippage: str | None = None

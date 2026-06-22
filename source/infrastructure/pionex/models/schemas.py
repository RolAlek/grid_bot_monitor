from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from source.domain.value_objects import GridType, Trend
from source.infrastructure.pionex.models.types import StringFloat


class BaseResponse(BaseModel):
    result: bool
    timestamp: int


class SuccessResponse[TData: BaseModel](BaseResponse):
    data: TData


class ErrorResponse(BaseResponse):
    code: str
    message: str | None = None


class DataObject(BaseModel):
    top: str
    bottom: str
    row: int = Field(ge=2, le=500)
    grid_type: GridType
    trend: Trend
    leverage: int = Field(ge=1, le=3)
    quote_investment: str = Field(gt=0)

    @model_validator(mode="after")
    def validate_top_and_bottom(self) -> Self:
        if self.top <= self.bottom:
            raise ValueError("Top must be greater then bottom")

        return self


class CheckFuturesGridParametersRequestSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base: str
    bu_order_data: DataObject = Field(alias="buOrderData")


class CheckFuturesGridParametersData(BaseModel):
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


class CheckFuturesGridParametersResponseSchema(SuccessResponse[CheckFuturesGridParametersData]): ...

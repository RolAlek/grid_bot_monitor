from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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

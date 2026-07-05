from pydantic import Field

from source.infrastructure.http.pionex.models.base import BaseSchema, CamelSchema, SuccessResponse


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


class RateItem(CamelSchema):
    funding_rate: float
    funding_time: int


class FundingRateObject(BaseSchema):
    symbol: str
    rates: list[RateItem]


class GetFundingRatesResponseSchema(SuccessResponse[FundingRateObject]): ...


class OpenInterestItem(CamelSchema):
    symbol: str | None = None
    open_interest: float | None = None


class OpenInterestsDataObject(CamelSchema):
    open_interests: list[OpenInterestItem] = Field(default_factory=list)


class GetOpenInterestsResponseSchema(SuccessResponse[OpenInterestsDataObject]): ...

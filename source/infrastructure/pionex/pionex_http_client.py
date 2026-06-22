import time

from httpx import Auth

from source.domain.entities import LiquidationEstimate, ProposedGridParams
from source.infrastructure.exceptions import HttpRequestError
from source.infrastructure.http.base import BaseHTTPClient
from source.infrastructure.pionex.models.schemas import (
    CheckFuturesGridParametersRequestSchema,
    CheckFuturesGridParametersResponseSchema,
    DataObject,
    ErrorResponse,
)
from source.settings import PionexSettings


class PionexHttpClient(BaseHTTPClient):
    def __init__(
        self,
        base_url: str,
        timeout: float | None = None,
        auth: Auth | None = None,
        *,
        settings: PionexSettings,
    ) -> None:
        super().__init__(base_url, timeout, auth)
        self._settings = settings

    async def check_grid_params(self, parameters: ProposedGridParams) -> None:
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

        response: CheckFuturesGridParametersResponseSchema | ErrorResponse = await self.post(
            path="/api/v1/bot/orders/futuresGrid/checkParams",
            payload=payload,
            params={"timestamp": str(int(time.time() * 1000))},
            request_model=CheckFuturesGridParametersRequestSchema,
            response_model=CheckFuturesGridParametersResponseSchema,
            error_model=ErrorResponse,
            by_alias=True,
        )

        if isinstance(response, ErrorResponse):
            raise HttpRequestError(message=response.message)

        if not response.result:
            raise HttpRequestError(message="Data is empty")

        data = response.data

        return LiquidationEstimate(
            proposal=parameters,
            estimate_liquidation_price_up=data.estimate_liquidation_price_up,
            estimate_liquidation_price_down=data.estimate_liquidation_price_down,
        )

import httpx
import pytest
import respx

from source.infrastructure.exceptions import (
    HttpRequestError,
    NonRetryableHttpError,
    RetryableHttpError,
    http_error_factory,
)
from source.infrastructure.http.pionex.adapters import PionexGridAdapter
from source.infrastructure.http.pionex.pionex_http_client import PionexHTTPClient


PIONEX_BASE = "https://api.pionex.com"


@pytest.fixture
def adapter() -> PionexGridAdapter:
    return PionexGridAdapter(PionexHTTPClient(base_url=PIONEX_BASE, timeout=5))


class TestGetRunningBots:
    async def test_returns_list(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/api/v1/bot/orders").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": True,
                    "timestamp": 1700000000000,
                    "data": {
                        "nextPageToken": None,
                        "previousPageToken": None,
                        "results": [
                            {
                                "buOrderType": "futures_grid",
                                "buOrderId": "abc-123",
                                "base": "BTC",
                                "quote": "USDT",
                                "status": "running",
                                "createTime": 1700000000000,
                                "closeTime": None,
                            }
                        ],
                    },
                },
            )
        )

        bots = await adapter.get_running_bots()
        assert len(bots) == 1
        assert bots[0].bu_order_id == "abc-123"

    async def test_empty_response(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/api/v1/bot/orders").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": True,
                    "timestamp": 1700000000000,
                    "data": {"nextPageToken": None, "previousPageToken": None, "results": []},
                },
            )
        )

        bots = await adapter.get_running_bots()
        assert bots == []


class TestGetFuturesGridOrder:
    async def test_returns_order(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/api/v1/bot/orders/futuresGrid/order").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": True,
                    "timestamp": 1700000000000,
                    "data": {
                        "buOrderId": "bot-456",
                        "base": "ETH",
                        "quote": "USDT",
                        "status": "running",
                        "createTime": 1700000000000,
                        "buOrderData": {
                            "status": "running",
                            "top": "3000",
                            "bottom": "2000",
                            "row": 30,
                            "gridType": "geometric",
                            "trend": "long",
                            "leverage": 2,
                            "quoteInvestment": "500",
                        },
                    },
                },
            )
        )

        order = await adapter.get_futures_grid_order("bot-456")
        assert order.leverage == 2
        assert order.trend == "long"


class TestCancelFuturesGrid:
    async def test_success(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/api/v1/bot/orders/futuresGrid/cancel").mock(
            return_value=httpx.Response(200, json={"result": True, "timestamp": 1700000000000})
        )

        result = await adapter.cancel_futures_grid("bot-123", close_note="test")
        assert result is True

    async def test_api_error(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/api/v1/bot/orders/futuresGrid/cancel").mock(
            return_value=httpx.Response(
                200,
                json={"result": False, "code": "ORDER_NOT_FOUND", "message": "Bot not found", "timestamp": 1},
            )
        )

        with pytest.raises(HttpRequestError, match="result=false"):
            await adapter.cancel_futures_grid("bot-999")


class TestRetryBehaviour:
    async def test_retry_on_429(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        calls: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
            calls.append(1)
            if len(calls) < 3:
                return httpx.Response(429)

            return httpx.Response(
                200,
                json={
                    "result": True,
                    "timestamp": 1700000000000,
                    "data": {"nextPageToken": None, "previousPageToken": None, "results": []},
                },
            )

        respx_mock.get("/api/v1/bot/orders").mock(side_effect=handler)

        bots = await adapter.get_running_bots()
        assert bots == []
        assert len(calls) == 3  # 2 failures + 1 success

    async def test_no_retry_on_400(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        calls: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
            calls.append(1)
            return httpx.Response(400)

        respx_mock.get("/api/v1/bot/orders").mock(side_effect=handler)

        with pytest.raises(HttpRequestError):
            await adapter.get_running_bots()
        assert len(calls) == 1  # только одна попытка, без повторов

    async def test_no_retry_on_401(self, adapter: PionexGridAdapter, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/api/v1/bot/orders").mock(return_value=httpx.Response(401))

        with pytest.raises(HttpRequestError):
            await adapter.get_running_bots()


class TestHttpErrorFactory:
    async def test_429_is_retryable(self) -> None:
        exc = http_error_factory("rate limit", status_code=429)
        assert isinstance(exc, RetryableHttpError)
        assert isinstance(exc, HttpRequestError)

    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    async def test_5xx_is_retryable(self, status_code: int) -> None:
        exc = http_error_factory("server error", status_code=status_code)
        assert isinstance(exc, RetryableHttpError)

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
    async def test_4xx_client_errors_are_not_retryable(self, status_code: int) -> None:
        exc = http_error_factory("client error", status_code=status_code)
        assert isinstance(exc, NonRetryableHttpError)

    async def test_no_status_code_is_non_retryable(self) -> None:
        exc = http_error_factory("api error without status")
        assert isinstance(exc, NonRetryableHttpError)

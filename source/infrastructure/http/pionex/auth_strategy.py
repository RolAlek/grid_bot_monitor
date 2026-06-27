import hashlib
import hmac
from collections.abc import AsyncGenerator

from httpx import Auth, Request
from httpx._models import Response

from source.settings import PionexSettings


class CustomPionexAuth(Auth):
    def __init__(self, settings: PionexSettings) -> None:
        self._settings = settings

    async def async_auth_flow(self, request: Request) -> AsyncGenerator[Request, Response]:
        if request.url.path == "/api/v1/bot/orders/futuresGrid/checkParams":
            request.headers["PIONEX-KEY"] = self._settings.api_key.get_secret_value()
            request.headers["PIONEX-SIGNATURE"] = self._generate_signature(request)

        yield request

    def _generate_signature(self, request: Request) -> str:
        prehash = request.method.upper().encode("utf-8") + request.content + request.url.raw_path

        return hmac.new(
            key=self._settings.api_secret.get_secret_value().encode("utf-8"),
            msg=prehash,
            digestmod=hashlib.sha256,
        ).hexdigest()

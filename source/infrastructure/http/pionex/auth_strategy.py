import hashlib
import hmac
from collections.abc import AsyncGenerator

from httpx import Auth, Request
from httpx._models import Response

from source.constants import CHECK_GRID_URL, CREATE_GRID_URL
from source.settings import PionexSettings


class CustomPionexAuth(Auth):
    def __init__(self, settings: PionexSettings) -> None:
        self._settings = settings

    async def async_auth_flow(self, request: Request) -> AsyncGenerator[Request, Response]:
        if request.url.path in {CHECK_GRID_URL, CREATE_GRID_URL}:
            request.headers["PIONEX-KEY"] = self._settings.api_key.get_secret_value()
            request.headers["PIONEX-SIGNATURE"] = self._generate_signature(request)

        yield request

    def _generate_signature(self, request: Request) -> str:
        method = request.method.upper().encode("utf-8")
        body = request.content or b""

        # raw_path includes path + query, e.g. b"/api/v1/checkParams?timestamp=123"
        raw = request.url.raw_path
        if b"?" in raw:
            path_bytes, query_bytes = raw.split(b"?", 1)
        else:
            path_bytes, query_bytes = raw, b""

        # Extract timestamp value for the standalone TIMESTAMP component
        timestamp = b""
        if query_bytes:
            for part in query_bytes.split(b"&"):
                if part.startswith(b"timestamp="):
                    timestamp = part[len(b"timestamp=") :]
                    break

        # Per Pionex docs: METHOD + PATH_URL + QUERY + TIMESTAMP + body
        prehash = method + path_bytes + query_bytes + timestamp + body

        return hmac.new(
            key=self._settings.api_secret.get_secret_value().encode("utf-8"),
            msg=prehash,
            digestmod=hashlib.sha256,
        ).hexdigest()

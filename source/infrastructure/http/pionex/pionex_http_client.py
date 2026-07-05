import time

from httpx import Auth

from source.infrastructure.http.base import BaseHTTPClient


def pionex_timestamp_ms() -> str:

    return str(int(time.time() * 1000))


class PionexHTTPClient(BaseHTTPClient):
    def __init__(
        self,
        base_url: str,
        timeout: float | None = None,
        auth: Auth | None = None,
    ) -> None:
        super().__init__(base_url, timeout, auth)

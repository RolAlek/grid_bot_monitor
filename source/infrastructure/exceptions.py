from collections.abc import Sequence
from http import HTTPStatus
from typing import Any


class BaseInfrastructureError(Exception):
    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.original_error = original_error


class HttpSerializationError(BaseInfrastructureError):
    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message, original_error)
        self.model_name = model_name


class HttpRequestError(BaseInfrastructureError):
    def __init__(
        self,
        message: str,
        status_code: HTTPStatus | None = None,
        response_content: Any = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message, original_error)
        self.status_code = status_code
        self.response_content = response_content


class RetryableHttpError(HttpRequestError): ...


class NonRetryableHttpError(HttpRequestError): ...


class HttpValidationError(NonRetryableHttpError):
    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        validation_errors: Sequence[dict[str, Any]] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message, original_error=original_error)
        self.model_name = model_name
        self.validation_errors = list(validation_errors) if validation_errors else []


def http_error_factory(
    message: str,
    status_code: HTTPStatus | None = None,
    response_content: Any = None,
    original_error: Exception | None = None,
) -> HttpRequestError:
    if status_code is not None and (status_code.is_server_error or status_code == HTTPStatus.TOO_MANY_REQUESTS):
        return RetryableHttpError(
            message=message,
            status_code=status_code,
            response_content=response_content,
            original_error=original_error,
        )
    return NonRetryableHttpError(
        message=message,
        status_code=status_code,
        response_content=response_content,
        original_error=original_error,
    )

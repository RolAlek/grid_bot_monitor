from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

from source.core.exceptions import AppError


class InfrastructureError(AppError):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        user_message: str | None = None,
        detail: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code or "ERR_INFRA_UNKNOWN",
            user_message=user_message or "Internal infrastructure error",
            detail=detail,
            original_error=original_error,
        )


class HttpSerializationError(InfrastructureError):
    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_INFRA_HTTP_SERIALIZATION",
            user_message="Error preparing request to external API",
            **kwargs,
        )
        self.model_name = model_name


class HttpRequestError(InfrastructureError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_content: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", "ERR_INFRA_HTTP_REQUEST"),
            user_message=kwargs.pop(
                "user_message",
                "There was an error accessing the external API. Please try again later",
            ),
            **kwargs,
        )
        self.status_code = status_code
        self.response_content = response_content


class RetryableHttpError(HttpRequestError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_content: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            response_content=response_content,
            error_code=kwargs.pop("error_code", "ERR_INFRA_HTTP_RETRYABLE"),
            **kwargs,
        )


class RateLimitError(RetryableHttpError):
    def __init__(
        self,
        message: str = "Rate limit exceeded (HTTP 429)",
        status_code: int | None = 429,
        response_content: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            response_content=response_content,
            error_code=kwargs.pop("error_code", "ERR_INFRA_HTTP_429"),
            user_message=kwargs.pop("user_message", "Too many requests to external API. Wait please."),
            **kwargs,
        )


class NonRetryableHttpError(HttpRequestError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_content: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            response_content=response_content,
            error_code=kwargs.pop("error_code", "ERR_INFRA_HTTP_NONRETRYABLE"),
            **kwargs,
        )


class HttpValidationError(NonRetryableHttpError):
    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        validation_errors: Sequence[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", "ERR_INFRA_HTTP_VALIDATION"),
            user_message=kwargs.pop("user_message", "Unexpected response format from an external API"),
            **kwargs,
        )
        self.model_name = model_name
        self.validation_errors = list(validation_errors) if validation_errors else []


class DatabaseError(InfrastructureError):
    def __init__(
        self,
        message: str = "Database error",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_INFRA_DB_ERROR",
            user_message="A storage-level error occurred",
            **kwargs,
        )


class RepositoryError(InfrastructureError):
    def __init__(
        self,
        message: str = "Repository operation failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_INFRA_REPOSITORY",
            user_message="Error processing data. Try again later",
            **kwargs,
        )


class UnsupportedFilterOperatorError(InfrastructureError):
    def __init__(
        self,
        message: str = "Unsupported filter operator",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_INFRA_UNSUPPORTED_FILTER",
            user_message="Internal error constructing query",
            **kwargs,
        )


def http_error_factory(
    message: str,
    status_code: int | None = None,
    response_content: Any = None,
    original_error: Exception | None = None,
) -> HttpRequestError:
    if status_code is not None:
        code = HTTPStatus(status_code)
        if code.is_server_error:
            return RetryableHttpError(
                message=message,
                status_code=status_code,
                response_content=response_content,
                original_error=original_error,
                error_code="ERR_INFRA_HTTP_5XX",
            )
        if code == HTTPStatus.TOO_MANY_REQUESTS:
            return RateLimitError(
                message=message,
                status_code=status_code,
                response_content=response_content,
                original_error=original_error,
            )
    return NonRetryableHttpError(
        message=message,
        status_code=status_code,
        response_content=response_content,
        error_code="ERR_INFRA_HTTP_4XX",
        original_error=original_error,
    )

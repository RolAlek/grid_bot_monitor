from collections.abc import Sequence
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
        status_code: int | None = None,
        response_content: Any = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message, original_error)
        self.status_code = status_code
        self.response_content = response_content


class HttpValidationError(HttpRequestError):
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

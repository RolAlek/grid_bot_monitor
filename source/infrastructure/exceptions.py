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

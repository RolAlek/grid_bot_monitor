class BaseApplicationError(Exception):
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class UnsupportedIntervalError(BaseApplicationError): ...


class InsufficientKlineDataError(BaseApplicationError): ...

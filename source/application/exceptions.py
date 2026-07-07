from typing import Any

from source.core.exceptions import AppError, ErrorCode


class ApplicationError(AppError):
    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode | str | None = None,
        detail: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code or ErrorCode.ERR_APP_UNKNOWN,
            detail=detail,
            original_error=original_error,
        )


class UnsupportedIntervalError(ApplicationError):
    def __init__(self, message: str = "Unsupported kline interval", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_UNSUPPORTED_INTERVAL, **kwargs)


class InsufficientKlineDataError(ApplicationError):
    def __init__(self, message: str = "Insufficient kline data for indicators", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_INSUFFICIENT_KLINES, **kwargs)


class HealthCheckFailedError(ApplicationError):
    def __init__(self, message: str = "Health check failed", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_HEALTH_CHECK_FAILED, **kwargs)


class ClassifierMisconfigurationError(ApplicationError):
    def __init__(self, message: str = "Health classifier misconfiguration", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_CLASSIFIER_CONFIG, **kwargs)


class BotManagementError(ApplicationError):
    def __init__(self, message: str = "Bot management operation failed", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_BOT_MANAGEMENT, **kwargs)


class ReconfigureBlockedError(ApplicationError):
    def __init__(self, message: str = "Reconfiguration blocked — gates failed", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_RECONFIGURE_BLOCKED, **kwargs)


class AssessmentFailedError(ApplicationError):
    def __init__(self, message: str = "Assessment failed", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_ASSESSMENT_FAILED, **kwargs)


class SnapshotSaveError(ApplicationError):
    def __init__(self, message: str = "Failed to save snapshot", **kwargs: Any) -> None:
        super().__init__(message, error_code=ErrorCode.ERR_APP_SNAPSHOT_SAVE, **kwargs)

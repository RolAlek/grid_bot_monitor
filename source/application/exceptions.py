from typing import Any

from source.core.exceptions import AppError


class ApplicationError(AppError):
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
            error_code=error_code or "ERR_APP_UNKNOWN",
            user_message=user_message or "Internal application layer error",
            detail=detail,
            original_error=original_error,
        )


class UnsupportedIntervalError(ApplicationError):
    def __init__(
        self,
        message: str = "Unsupported kline interval",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_UNSUPPORTED_INTERVAL",
            user_message="Unsupported candle interval",
            **kwargs,
        )


class InsufficientKlineDataError(ApplicationError):
    def __init__(
        self,
        message: str = "Insufficient kline data for indicators",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_INSUFFICIENT_KLINES",
            user_message="Not enough candles available to compute indicators",
            **kwargs,
        )


class HealthCheckFailedError(ApplicationError):
    """A health-check cycle could not be completed for a specific bot."""

    def __init__(
        self,
        message: str = "Health check failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_HEALTH_CHECK_FAILED",
            user_message="Bot health check failed",
            **kwargs,
        )


class ClassifierMisconfigurationError(ApplicationError):
    def __init__(
        self,
        message: str = "Health classifier misconfiguration",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_CLASSIFIER_CONFIG",
            user_message="Health classifier configuration error",
            **kwargs,
        )


class BotManagementError(ApplicationError):
    def __init__(
        self,
        message: str = "Bot management operation failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_BOT_MANAGEMENT",
            user_message="Bot control operation failed",
            **kwargs,
        )


class ReconfigureBlockedError(ApplicationError):
    def __init__(
        self,
        message: str = "Reconfiguration blocked — gates failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_RECONFIGURE_BLOCKED",
            user_message="Bot reconfiguration was blocked because one or more assessment gates returned a FAIL status",
            **kwargs,
        )


class AssessmentFailedError(ApplicationError):
    def __init__(
        self,
        message: str = "Assessment failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_ASSESSMENT_FAILED",
            user_message="Market conditions assessment ended in error",
            **kwargs,
        )


class SnapshotSaveError(ApplicationError):
    def __init__(
        self,
        message: str = "Failed to save snapshot",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_APP_SNAPSHOT_SAVE",
            user_message="Failed to persist a health snapshot",
            **kwargs,
        )

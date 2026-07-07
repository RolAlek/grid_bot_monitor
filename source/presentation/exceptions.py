from typing import Any

from source.core.exceptions import AppError


class PresentationError(AppError):
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
            error_code=error_code or "ERR_PRES_UNKNOWN",
            user_message=user_message or "Internal presentation layer error",
            detail=detail,
            original_error=original_error,
        )


class TelegramDeliveryError(PresentationError):
    def __init__(
        self,
        message: str = "Failed to deliver Telegram message",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_PRES_TELEGRAM_DELIVERY",
            user_message="Failed to deliver a message to the Telegram chat",
            **kwargs,
        )

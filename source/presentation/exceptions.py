from typing import Any

from source.core.exceptions import AppError, ErrorCode


class PresentationError(AppError):
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
            error_code=error_code or ErrorCode.ERR_PRES_UNKNOWN,
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
            error_code=ErrorCode.ERR_PRES_TELEGRAM_DELIVERY,
            **kwargs,
        )

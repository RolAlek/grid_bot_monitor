from typing import Any, Final

from source.core.exceptions import AppError, ErrorCode


FALLBACK_USER_MESSAGE: Final[str] = "An internal error occurred. Administrator notified."
PARTS: Final[int] = 3


class ErrorPresenter:
    def format_user_error(self, error: AppError) -> str:
        try:
            return ErrorCode(error.error_code).user_message
        except ValueError:
            pass
        try:
            return ErrorCode.ERR_UNKNOWN.user_message
        except Exception:
            return FALLBACK_USER_MESSAGE

    @staticmethod
    def format_unknown_error() -> str:
        return FALLBACK_USER_MESSAGE

    @staticmethod
    def extract_error_context(error: Exception) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "error_type": type(error).__name__,
        }

        if isinstance(error, AppError):
            ctx["error_code"] = error.error_code
            ctx["user_message"] = error.user_message

            parts = error.error_code.split("_", 2)
            if len(parts) >= PARTS:
                ctx["error_layer"] = parts[1].lower()

        return ctx

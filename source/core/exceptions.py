from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        user_message: str | None = None,
        detail: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code or "ERR_UNKNOWN"
        self.user_message = user_message or message
        self.detail = detail or {}
        self.original_error = original_error

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.args[0] if self.args else "",
            "user_message": self.user_message,
        }

        if self.detail:
            result["detail"] = self.detail

        if self.original_error is not None:
            result["original_error"] = repr(self.original_error)
        return result

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.error_code!r}, message={self.args[0]!r})"

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # ── Domain: data unavailability ──
    ERR_DOMAIN_CANDLE_DATA_UNAVAILABLE = "ERR_DOMAIN_CANDLE_DATA_UNAVAILABLE"
    ERR_DOMAIN_LIQ_ESTIMATE_UNAVAILABLE = "ERR_DOMAIN_LIQ_ESTIMATE_UNAVAILABLE"
    ERR_DOMAIN_FUNDING_RATE_UNAVAILABLE = "ERR_DOMAIN_FUNDING_RATE_UNAVAILABLE"
    ERR_DOMAIN_OI_DATA_UNAVAILABLE = "ERR_DOMAIN_OI_DATA_UNAVAILABLE"
    ERR_DOMAIN_GRID_ORDER_UNAVAILABLE = "ERR_DOMAIN_GRID_ORDER_UNAVAILABLE"
    ERR_DOMAIN_INVALID_GRID_PARAMS = "ERR_DOMAIN_INVALID_GRID_PARAMS"
    ERR_DOMAIN_INVALID_SYMBOL_FORMAT = "ERR_DOMAIN_INVALID_SYMBOL_FORMAT"
    ERR_DOMAIN_INVALID_SYMBOL = "ERR_DOMAIN_INVALID_SYMBOL"
    ERR_DOMAIN_DECISION_NOT_FOUND = "ERR_DOMAIN_DECISION_NOT_FOUND"
    ERR_DOMAIN_DUPLICATE_OI_SNAPSHOT = "ERR_DOMAIN_DUPLICATE_OI_SNAPSHOT"
    ERR_DOMAIN_OI_SNAPSHOT_PERSIST = "ERR_DOMAIN_OI_SNAPSHOT_PERSIST"
    ERR_DOMAIN_BOT_INTEGRITY = "ERR_DOMAIN_BOT_INTEGRITY"
    ERR_DOMAIN_BOT_NOT_FOUND = "ERR_DOMAIN_BOT_NOT_FOUND"
    ERR_DOMAIN_INVALID_HEALTH_METRIC = "ERR_DOMAIN_INVALID_HEALTH_METRIC"
    ERR_DOMAIN_UNKNOWN = "ERR_DOMAIN_UNKNOWN"
    ERR_APP_UNSUPPORTED_INTERVAL = "ERR_APP_UNSUPPORTED_INTERVAL"
    ERR_APP_INSUFFICIENT_KLINES = "ERR_APP_INSUFFICIENT_KLINES"
    ERR_APP_HEALTH_CHECK_FAILED = "ERR_APP_HEALTH_CHECK_FAILED"
    ERR_APP_CLASSIFIER_CONFIG = "ERR_APP_CLASSIFIER_CONFIG"
    ERR_APP_BOT_MANAGEMENT = "ERR_APP_BOT_MANAGEMENT"
    ERR_APP_RECONFIGURE_BLOCKED = "ERR_APP_RECONFIGURE_BLOCKED"
    ERR_APP_ASSESSMENT_FAILED = "ERR_APP_ASSESSMENT_FAILED"
    ERR_APP_SNAPSHOT_SAVE = "ERR_APP_SNAPSHOT_SAVE"
    ERR_APP_UNKNOWN = "ERR_APP_UNKNOWN"
    ERR_INFRA_HTTP_REQUEST = "ERR_INFRA_HTTP_REQUEST"
    ERR_INFRA_HTTP_SERIALIZATION = "ERR_INFRA_HTTP_SERIALIZATION"
    ERR_INFRA_HTTP_RETRYABLE = "ERR_INFRA_HTTP_RETRYABLE"
    ERR_INFRA_HTTP_5XX = "ERR_INFRA_HTTP_5XX"
    ERR_INFRA_HTTP_429 = "ERR_INFRA_HTTP_429"
    ERR_INFRA_HTTP_NONRETRYABLE = "ERR_INFRA_HTTP_NONRETRYABLE"
    ERR_INFRA_HTTP_4XX = "ERR_INFRA_HTTP_4XX"
    ERR_INFRA_HTTP_VALIDATION = "ERR_INFRA_HTTP_VALIDATION"
    ERR_INFRA_DB_ERROR = "ERR_INFRA_DB_ERROR"
    ERR_INFRA_REPOSITORY = "ERR_INFRA_REPOSITORY"
    ERR_INFRA_UNSUPPORTED_FILTER = "ERR_INFRA_UNSUPPORTED_FILTER"
    ERR_INFRA_UNKNOWN = "ERR_INFRA_UNKNOWN"
    ERR_PRES_TELEGRAM_DELIVERY = "ERR_PRES_TELEGRAM_DELIVERY"
    ERR_PRES_UNKNOWN = "ERR_PRES_UNKNOWN"
    ERR_UNKNOWN = "ERR_UNKNOWN"

    @property
    def user_message(self) -> str:
        return _ERROR_MESSAGES[self]


_ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.ERR_DOMAIN_CANDLE_DATA_UNAVAILABLE: "Could not retrieve candle data from the exchange.",
    ErrorCode.ERR_DOMAIN_LIQ_ESTIMATE_UNAVAILABLE: "Could not retrieve liquidation estimate from the exchange.",
    ErrorCode.ERR_DOMAIN_FUNDING_RATE_UNAVAILABLE: "Could not retrieve funding rate data.",
    ErrorCode.ERR_DOMAIN_OI_DATA_UNAVAILABLE: "Could not retrieve open interest data.",
    ErrorCode.ERR_DOMAIN_GRID_ORDER_UNAVAILABLE: "Could not retrieve grid order status from the exchange.",
    ErrorCode.ERR_DOMAIN_INVALID_GRID_PARAMS: "Invalid grid parameters. Check the price range and leverage.",
    ErrorCode.ERR_DOMAIN_INVALID_SYMBOL_FORMAT: "Invalid symbol format.",
    ErrorCode.ERR_DOMAIN_INVALID_SYMBOL: "Unknown trading symbol. Use e.g. BTC_USDT_PERP.",
    ErrorCode.ERR_DOMAIN_DECISION_NOT_FOUND: "Verdict not found. Run the assessment again.",
    ErrorCode.ERR_DOMAIN_DUPLICATE_OI_SNAPSHOT: "An open interest snapshot for this date already exists.",
    ErrorCode.ERR_DOMAIN_OI_SNAPSHOT_PERSIST: "Failed to save open interest snapshot.",
    ErrorCode.ERR_DOMAIN_BOT_INTEGRITY: "Bot data inconsistency detected. Contact the administrator.",
    ErrorCode.ERR_DOMAIN_BOT_NOT_FOUND: "Bot not found. It may have been closed or not started yet.",
    ErrorCode.ERR_DOMAIN_INVALID_HEALTH_METRIC: "Invalid bot health metric value.",
    ErrorCode.ERR_DOMAIN_UNKNOWN: "Internal error. Please try again later.",
    ErrorCode.ERR_APP_UNSUPPORTED_INTERVAL: "Unsupported candle interval.",
    ErrorCode.ERR_APP_INSUFFICIENT_KLINES: "Insufficient candle data to compute indicators.",
    ErrorCode.ERR_APP_HEALTH_CHECK_FAILED: "Bot health check failed.",
    ErrorCode.ERR_APP_CLASSIFIER_CONFIG: "Health classifier configuration error.",
    ErrorCode.ERR_APP_BOT_MANAGEMENT: "Bot management operation failed. Try again later.",
    ErrorCode.ERR_APP_RECONFIGURE_BLOCKED: "Grid reconfiguration blocked — one or more assessment gates failed.",
    ErrorCode.ERR_APP_ASSESSMENT_FAILED: "Market assessment failed. Try again later.",
    ErrorCode.ERR_APP_SNAPSHOT_SAVE: "Failed to save bot health snapshot.",
    ErrorCode.ERR_APP_UNKNOWN: "Internal application error. Try again later.",
    ErrorCode.ERR_INFRA_HTTP_REQUEST: "Error contacting the exchange. Try again later.",
    ErrorCode.ERR_INFRA_HTTP_SERIALIZATION: "Error preparing request to the exchange.",
    ErrorCode.ERR_INFRA_HTTP_RETRYABLE: "Temporary exchange error. The system will retry automatically.",
    ErrorCode.ERR_INFRA_HTTP_5XX: "Exchange server temporarily unavailable. Try again later.",
    ErrorCode.ERR_INFRA_HTTP_429: "Too many requests to the exchange. Please wait.",
    ErrorCode.ERR_INFRA_HTTP_NONRETRYABLE: "Exchange request error. Check parameters.",
    ErrorCode.ERR_INFRA_HTTP_4XX: "Exchange request error. Check parameters.",
    ErrorCode.ERR_INFRA_HTTP_VALIDATION: "Unexpected response format from the exchange.",
    ErrorCode.ERR_INFRA_DB_ERROR: "Database error. Administrator notified.",
    ErrorCode.ERR_INFRA_REPOSITORY: "Data operation error. Try again later.",
    ErrorCode.ERR_INFRA_UNSUPPORTED_FILTER: "Internal query construction error.",
    ErrorCode.ERR_INFRA_UNKNOWN: "Internal infrastructure error. Try again later.",
    ErrorCode.ERR_PRES_TELEGRAM_DELIVERY: "Failed to deliver message. Try again later.",
    ErrorCode.ERR_PRES_UNKNOWN: "Internal interface error.",
    ErrorCode.ERR_UNKNOWN: "An internal error occurred. Administrator notified.",
}


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode | str | None = None,
        detail: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code: str = str(error_code) if error_code else "ERR_UNKNOWN"
        self.detail = detail or {}
        self.original_error = original_error

    @property
    def user_message(self) -> str:
        try:
            return ErrorCode(self.error_code).user_message
        except ValueError:
            return ErrorCode.ERR_UNKNOWN.user_message

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

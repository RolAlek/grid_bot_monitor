from typing import Any

from source.core.exceptions import AppError


class DomainError(AppError):
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
            error_code=error_code or "ERR_DOMAIN_UNKNOWN",
            user_message=user_message or "Internal domain layer error",
            detail=detail,
            original_error=original_error,
        )


class CandleDataUnavailableError(DomainError):
    def __init__(
        self,
        message: str = "Candle data unavailable from exchange",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_CANDLE_DATA_UNAVAILABLE",
            user_message="Failed to retrieve candlestick data from the exchange",
            **kwargs,
        )


class LiquidationEstimateDataUnavailableError(DomainError):
    def __init__(
        self,
        message: str = "Liquidation estimate data unavailable from exchange",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_LIQ_ESTIMATE_UNAVAILABLE",
            user_message="Unable to obtain liquidation estimate from exchange",
            **kwargs,
        )


class FundingRateDataUnavailableError(DomainError):
    def __init__(
        self,
        message: str = "Funding rate data unavailable from exchange",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_FUNDING_RATE_UNAVAILABLE",
            user_message="Unable to retrieve funding rate data",
            **kwargs,
        )


class OpenInterestDataUnavailableError(DomainError):
    def __init__(
        self,
        message: str = "Open interest data unavailable from exchange",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_OI_DATA_UNAVAILABLE",
            user_message="Unable to retrieve open interest data",
            **kwargs,
        )


class GridOrderDataUnavailableError(DomainError):
    def __init__(
        self,
        message: str = "Grid order data unavailable from exchange",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_GRID_ORDER_UNAVAILABLE",
            user_message="Failed to retrieve grid order status data",
            **kwargs,
        )


class InvalidGridParamsError(DomainError):
    def __init__(
        self,
        message: str = "Invalid grid parameters",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_INVALID_GRID_PARAMS",
            user_message="Incorrect grid parameters",
            **kwargs,
        )


class InvalidSymbolFormatError(DomainError):
    def __init__(
        self,
        message: str = "Invalid symbol format",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_INVALID_SYMBOL_FORMAT",
            user_message="Incorrect market symbol format",
            **kwargs,
        )


class DecisionNotFoundError(DomainError):
    def __init__(
        self,
        message: str = "Decision verdict not found",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_DECISION_NOT_FOUND",
            user_message="Decision verdict not found",
            **kwargs,
        )


class DuplicateOISnapshotError(DomainError):
    def __init__(
        self,
        message: str = "OI snapshot already exists for this symbol and date",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_DUPLICATE_OI_SNAPSHOT",
            user_message="A snapshot of open interest for this date already exists",
            **kwargs,
        )


class OISnapshotPersistenceError(DomainError):
    def __init__(
        self,
        message: str = "Failed to persist OI snapshot",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_OI_SNAPSHOT_PERSIST",
            user_message="Error saving snapshot of open interest",
            **kwargs,
        )


class BotIntegrityError(DomainError):
    def __init__(
        self,
        message: str = "Bot data integrity violation",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_BOT_INTEGRITY",
            user_message="Inconsistency in mesh bot data detected",
            **kwargs,
        )


class BotNotFoundError(DomainError):
    def __init__(
        self,
        message: str = "Bot not found",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_BOT_NOT_FOUND",
            user_message="The bot wasn't found. It may have been closed or not yet running",
            **kwargs,
        )


class InvalidHealthMetricError(DomainError):
    def __init__(
        self,
        message: str = "Invalid health metric value",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_INVALID_HEALTH_METRIC",
            user_message="Incorrect value of the bot health metric",
            **kwargs,
        )


class InvalidSymbolError(DomainError):
    def __init__(
        self,
        message: str = "Invalid or unknown trading symbol",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            error_code="ERR_DOMAIN_INVALID_SYMBOL",
            user_message="Unknown trading symbol. Use for example BTC_USDT_REPR",
            **kwargs,
        )

from typing import Any

from source.core.exceptions import AppError, ErrorCode


class DomainError(AppError):
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
            error_code=error_code or ErrorCode.ERR_DOMAIN_UNKNOWN,
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
            error_code=ErrorCode.ERR_DOMAIN_CANDLE_DATA_UNAVAILABLE,
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
            error_code=ErrorCode.ERR_DOMAIN_LIQ_ESTIMATE_UNAVAILABLE,
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
            error_code=ErrorCode.ERR_DOMAIN_FUNDING_RATE_UNAVAILABLE,
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
            error_code=ErrorCode.ERR_DOMAIN_OI_DATA_UNAVAILABLE,
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
            error_code=ErrorCode.ERR_DOMAIN_GRID_ORDER_UNAVAILABLE,
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
            error_code=ErrorCode.ERR_DOMAIN_INVALID_GRID_PARAMS,
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
            error_code=ErrorCode.ERR_DOMAIN_INVALID_SYMBOL_FORMAT,
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
            error_code=ErrorCode.ERR_DOMAIN_DECISION_NOT_FOUND,
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
            error_code=ErrorCode.ERR_DOMAIN_DUPLICATE_OI_SNAPSHOT,
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
            error_code=ErrorCode.ERR_DOMAIN_OI_SNAPSHOT_PERSIST,
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
            error_code=ErrorCode.ERR_DOMAIN_BOT_INTEGRITY,
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
            error_code=ErrorCode.ERR_DOMAIN_BOT_NOT_FOUND,
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
            error_code=ErrorCode.ERR_DOMAIN_INVALID_HEALTH_METRIC,
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
            error_code=ErrorCode.ERR_DOMAIN_INVALID_SYMBOL,
            **kwargs,
        )

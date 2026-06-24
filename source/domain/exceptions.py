class BaseDomainError(Exception):
    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)

        self.original_error = original_error


class InvalidCandleDataError(BaseDomainError): ...


class InvalidLiquidationEstimateDatError(BaseDomainError): ...


class InvalidFundingRateDataError(BaseDomainError): ...


class InvalidOpenInterestDataError(BaseDomainError): ...

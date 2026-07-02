from typing import Final


FUNDING_ANNUALIZATION_FACTOR: Final[int] = 3 * 365 * 100
MIN_SNAPSHOTS_LENGTH: Final[int] = 2


CHECK_GRID_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/checkParams"
CREATE_GRID_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/create"

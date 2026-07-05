from typing import Final


FUNDING_ANNUALIZATION_FACTOR: Final[int] = 3 * 365 * 100
MIN_SNAPSHOTS_LENGTH: Final[int] = 2


CHECK_GRID_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/checkParams"
CREATE_GRID_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/create"
FUTURES_GRID_ORDER_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/order"
FUTURES_GRID_CANCEL_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/cancel"
FUTURES_GRID_ADJUST_URL: Final[str] = "/api/v1/bot/orders/futuresGrid/adjustParams"
BOT_ORDERS_LIST_URL: Final[str] = "/api/v1/bot/orders"

from typing import Any, NoReturn

import structlog

from source.core.exceptions import AppError
from source.presentation.bot.error_presenter import ErrorPresenter


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    *,
    level: str = "error",
    **context: Any,
) -> None:
    ctx = ErrorPresenter.extract_error_context(error)
    ctx.update(context)

    log_method = getattr(logger, level, logger.error)

    if isinstance(error, AppError):
        log_method(str(error), **ctx)
    else:
        log_method(str(error), **ctx, exc_info=error)


def log_and_raise(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    *,
    level: str = "error",
    **context: Any,
) -> NoReturn:
    log_error(logger, error, level=level, **context)
    raise error

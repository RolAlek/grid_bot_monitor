import logging
import logging.config
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from structlog.typing import EventDict, WrappedLogger


if TYPE_CHECKING:
    from source.settings import AppSettings


class _DailyFileHandler(logging.FileHandler):
    def __init__(self, log_dir: Path, backup_count: int = 30, **kwargs: Any) -> None:
        self._log_dir = log_dir
        self._backup_count = backup_count
        self._current_date = datetime.now(UTC).date()
        log_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(self._path_for(self._current_date), **kwargs)

    def _path_for(self, d: Any) -> str:
        return str(self._log_dir / f"{d.isoformat()}.log")

    def emit(self, record: logging.LogRecord) -> None:
        today = datetime.now(UTC).date()
        if today != self._current_date:
            self.close()
            self._current_date = today
            self.baseFilename = self._path_for(today)
            self.stream = self._open()
            self._prune()
        super().emit(record)

    def _prune(self) -> None:
        files = sorted(self._log_dir.glob("????-??-??.log"))
        for old in files[: -self._backup_count]:
            old.unlink(missing_ok=True)


def _sanitize_sensitive(
    logger: WrappedLogger,  # noqa: ARG001
    name: str,  # noqa: ARG001
    event_dict: EventDict,
) -> EventDict:
    sensitive = {"api_key", "api_secret", "authorization", "Authorization"}
    for key in sensitive:
        event_dict.pop(key, None)
    if headers := event_dict.get("http", {}).get("headers"):
        for key in sensitive:
            headers.pop(key, None)
    return event_dict


def _drop_color_message(
    logger: WrappedLogger,  # noqa: ARG001
    name: str,  # noqa: ARG001
    event_dict: EventDict,
) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def _pre_chain() -> list[Any]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO", utc=True),
        structlog.processors.CallsiteParameterAdder([
            structlog.processors.CallsiteParameter.PROCESS_NAME,
            structlog.processors.CallsiteParameter.THREAD_NAME,
        ]),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _sanitize_sensitive,
        _drop_color_message,
    ]


def _renderer(*, as_json: bool) -> Any:
    if as_json:
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer(
        colors=True,
        exception_formatter=structlog.dev.plain_traceback,
    )


def configure_logging(settings: "AppSettings") -> None:
    level_int: int = getattr(logging, str(settings.log_level), logging.INFO)
    pre = _pre_chain()
    remove_meta = structlog.stdlib.ProcessorFormatter.remove_processors_meta

    # Console handler via dictConfig
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "foreign_pre_chain": pre,
                "processors": [remove_meta, _renderer(as_json=settings.log_json)],
                "use_get_message": True,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level_int,
                "formatter": "console",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"handlers": ["console"], "level": level_int},
        "loggers": {
            "asyncio": {"level": "WARNING", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
            "hpack": {"level": "WARNING", "propagate": True},
            "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
            "sqlalchemy.pool": {"level": "WARNING", "propagate": True},
            "apscheduler": {"level": "INFO", "propagate": True},
            "aiogram": {"level": "INFO", "propagate": True},
        },
    })

    # File handler — always JSON, one file per UTC day
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=pre,
        processors=[remove_meta, structlog.processors.JSONRenderer()],
        use_get_message=True,
    )
    file_handler = _DailyFileHandler(
        log_dir=settings.log_dir,
        backup_count=settings.log_file_days,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level_int)
    logging.getLogger().addHandler(file_handler)

    structlog.configure(
        processors=[*pre, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

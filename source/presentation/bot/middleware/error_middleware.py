import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from source.core.exceptions import AppError
from source.presentation.bot.error_presenter import ErrorPresenter


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Do not reply to messages older than this many seconds (anti-spam).
_MAX_MESSAGE_AGE_SECONDS = 300  # 5 minutes


class ErrorMiddleware(BaseMiddleware):
    def __init__(self, presenter: ErrorPresenter | None = None) -> None:
        super().__init__()
        self._presenter = presenter or ErrorPresenter()

    async def __call__(  # type: ignore[override]
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except AppError as exc:
            await self._handle_app_error(exc, event)
        except Exception as exc:
            await self._handle_unknown_error(exc, event)

    async def _handle_app_error(self, error: AppError, event: TelegramObject) -> None:
        ctx = ErrorPresenter.extract_error_context(error)
        logger.error(
            "Application error caught by middleware",
            **ctx,
            exc_info=error.original_error or error,
        )
        await self._reply_safe(event, self._presenter.format_user_error(error))

    async def _handle_unknown_error(self, error: Exception, event: TelegramObject) -> None:
        logger.error(
            "Unhandled non-AppError exception caught by middleware",
            error_type=type(error).__name__,
        )
        await self._reply_safe(event, self._presenter.format_unknown_error())

    async def _reply_safe(self, event: TelegramObject, text: str) -> None:
        chat_id, message_id = self._extract_chat_info(event)
        if chat_id is None:
            return

        if message_id is not None:
            msg_date = self._extract_message_date(event)
            if msg_date is not None and (time.time() - msg_date) > _MAX_MESSAGE_AGE_SECONDS:
                return

        try:
            await self._send_message(event, text)
        except Exception:
            logger.exception("Failed to send error reply to user")

    @staticmethod
    def _extract_chat_info(event: TelegramObject) -> tuple[int | None, int | None]:
        if isinstance(event, Message):
            return event.chat.id, event.message_id

        if isinstance(event, Update):
            msg = event.message or event.callback_query.message if event.callback_query else None
            if msg:
                return msg.chat.id, msg.message_id

        if hasattr(event, "message") and event.message is not None:
            msg = event.message
            return msg.chat.id, msg.message_id

        return None, None

    @staticmethod
    def _extract_message_date(event: TelegramObject) -> float | None:

        if isinstance(event, Message):
            return event.date.timestamp() if event.date else None

        if isinstance(event, Update):
            msg = event.message or (event.callback_query.message if event.callback_query else None)
            if msg and msg.date:
                return msg.date.timestamp()

        return None

    async def _send_message(self, event: TelegramObject, text: str) -> None:
        if isinstance(event, Message):
            await event.reply(text)

        elif isinstance(event, Update):
            msg = event.message or (event.callback_query.message if event.callback_query else None)
            if msg:
                await msg.reply(text)

        elif hasattr(event, "message") and event.message is not None:
            await event.message.reply(text)

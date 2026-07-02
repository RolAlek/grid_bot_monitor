import structlog
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from source.application.ports import Notifier
from source.domain.entities import DecisionVerdict, GateResult
from source.domain.value_objects import GateStatus, VerdictAction
from source.infrastructure.telegram.formater import TelegramMessageFormatter
from source.presentation.bot.keyboards.inlines import build_verdict_reaction_kb
from source.utils.ensure import ensure


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AiogramNotifier(Notifier):
    def __init__(self, bot: Bot, chat_id: int | str) -> None:
        self._bot = bot
        self._chat_id = chat_id

        self._formatter = TelegramMessageFormatter()

    async def send_alert(
        self,
        result: GateResult,
        prev_status: GateStatus | None = None,
    ) -> None:
        await self._send_message(text=self._formatter.format_alert(result, prev_status), chat_id=self._chat_id)

    async def send_digest(self, verdict: DecisionVerdict) -> None:
        kb = build_verdict_reaction_kb(ensure(verdict.oid)) if verdict.action == VerdictAction.LAUNCH else None
        await self._send_message(text=self._formatter.format_digest(verdict), chat_id=self._chat_id, keyboard=kb)

    async def _send_message(
        self,
        text: str,
        chat_id: int | str,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> None:
        try:
            await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as error:
            logger.exception("Failed to send message", error=error, chat_id=chat_id)
            await self._bot.send_message(
                chat_id=chat_id,
                text=f"Failed to send message: {error}",
            )

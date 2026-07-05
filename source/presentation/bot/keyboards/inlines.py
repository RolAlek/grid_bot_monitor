from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from source.domain.value_objects import ActionType, HealthStatus


class Mode(StrEnum):
    MANUAL = "manual"
    AUTO = "auto"
    REJECT = "reject"


class ApplyDecisionCD(CallbackData, prefix="apply"):
    mode: Mode
    verdict_id: str


class BotActionCD(CallbackData, prefix="ba"):
    action: str  # ActionType value
    symbol: str
    bot_oid: str


def build_verdict_reaction_kb(verdict_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🦽 Manual", callback_data=ApplyDecisionCD(mode=Mode.MANUAL, verdict_id=verdict_id).pack())
    builder.button(text="🪄 Launch", callback_data=ApplyDecisionCD(mode=Mode.AUTO, verdict_id=verdict_id).pack())

    builder.adjust(2)

    return builder.as_markup()


def build_health_kb(status: HealthStatus, symbol: str, bot_oid: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Always available
    builder.button(
        text="⏸️ Pause",
        callback_data=BotActionCD(action=ActionType.PAUSE.value, symbol=symbol, bot_oid=bot_oid).pack(),
    )
    builder.button(
        text="❌ Close",
        callback_data=BotActionCD(action=ActionType.CLOSE.value, symbol=symbol, bot_oid=bot_oid).pack(),
    )

    if status in {HealthStatus.YELLOW, HealthStatus.RED}:
        builder.button(
            text="🔄 Reconfigure",
            callback_data=BotActionCD(action=ActionType.RECONFIGURE.value, symbol=symbol, bot_oid=bot_oid).pack(),
        )
        builder.button(
            text="📊 Details",
            callback_data=BotActionCD(action="details", symbol=symbol, bot_oid=bot_oid).pack(),
        )

    if status == HealthStatus.RED:
        builder.button(
            text="✅ Acknowledge",
            callback_data=BotActionCD(action=ActionType.ACKNOWLEDGE.value, symbol=symbol, bot_oid=bot_oid).pack(),
        )

    builder.adjust(2)
    return builder.as_markup()

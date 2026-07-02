from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Mode(StrEnum):
    MANUAL = "manual"
    AUTO = "auto"
    REJECT = "reject"


class ApplyDecisionCD(CallbackData, prefix="apply"):
    mode: Mode
    verdict_id: str


def build_verdict_reaction_kb(verdict_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🦽 Manual", callback_data=ApplyDecisionCD(mode=Mode.MANUAL, verdict_id=verdict_id).pack())
    builder.button(text="🪄 Launch", callback_data=ApplyDecisionCD(mode=Mode.AUTO, verdict_id=verdict_id).pack())

    builder.adjust(2)

    return builder.as_markup()

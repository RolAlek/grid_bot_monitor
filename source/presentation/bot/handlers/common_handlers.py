from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message


_HELP_TEXT = (
    "<b>Grid Bot Advisor and Monitor</b>\n"
    "\n"
    "Available commands:\n"
    "/assess — run a full three-gate assessment and receive a verdict\n"
    "/verdict — show the most recent stored verdict\n"
    "/help — show this message"
)


def common_router() -> Router:
    router = Router(name="common")

    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        name = message.from_user.first_name if message.from_user else "there"
        await message.answer(
            f"Hi, {name}!\n"
            "\n"
            "<b>Grid Bot Advisor and Monitor</b> helps you decide whether to launch a "
            "crypto futures grid bot on Pionex.\n"
            "\n"
            "Before every launch it runs three independent checks:\n"
            "• <b>Market regime</b> — confirms the market is range-bound, not strongly trending "
            "(ADX, ATR, swing range)\n"
            "• <b>Positioning</b> — checks funding rate and open-interest dynamics are not "
            "signalling crowded or high-risk conditions\n"
            "• <b>Liquidation safety</b> — verifies your liquidation price has enough buffer "
            "relative to the proposed grid range and leverage\n"
            "\n"
            "Based on the results you receive one of three verdicts:\n"
            "<b>LAUNCH</b> — all conditions met, safe to start the bot\n"
            "<b>REVIEW</b> — caution signals present, manual review recommended\n"
            "<b>HOLD</b> — one or more hard limits breached, do not launch\n"
            "\n" + _HELP_TEXT,
            parse_mode="HTML",
        )

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(_HELP_TEXT, parse_mode="HTML")

    return router

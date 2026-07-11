from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message


_HELP_TEXT = (
    "<b>🤖 Grid Bot Advisor and Monitor</b>\n"
    "\n"
    "<b>📊 Monitoring</b>\n"
    "/status — show health status of all active bots\n"
    "/status SYMBOL — show detailed status for a specific bot (e.g. /status BTC_USDT_PERP)\n"
    "/settings — display current monitoring settings\n"
    "\n"
    "<b>🛠️ Bot Management</b>\n"
    "/pause SYMBOL — pause a running bot\n"
    "/resume SYMBOL — resume a paused bot\n"
    "/close SYMBOL — close a bot via API\n"
    "/reconfigure SYMBOL — re-evaluate grid parameters through all three gates\n"
    "\n"
    "<b>📈 Assessment</b>\n"
    "/weekly_assessment — run a full three-gate assessment and receive a verdict\n"
    "/daily_assessment — run a daily positioning check (Gate 2 only)\n"
    "/verdict — show the most recent stored verdict\n"
    "\n"
    "<b>📋 Other</b>\n"
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
            "<b>🤖 Grid Bot Advisor and Monitor</b>\n"
            "\n"
            "I help you manage and monitor crypto futures grid bots on Pionex.\n"
            "\n"
            "<b>📊 Real-time Monitoring</b>\n"
            "Every 30 minutes I check each bot's health — PnL, distance to "
            "liquidation, grid fill ratio, volatility, funding rate, and ADX. "
            "Bots are classified as 🟢 GREEN / 🟡 YELLOW / 🔴 RED and you "
            "receive alerts when the status changes.\n"
            "\n"
            "<b>🛠️ Manual Controls</b>\n"
            "• <b>/pause</b> / <b>/resume</b> — pause or resume any running bot\n"
            "• <b>/close</b> — close a bot via API\n"
            "• <b>/reconfigure</b> — re-run all three assessment gates and "
            "propose new grid parameters\n"
            "\n"
            "<b>📈 Assessment (three independent gates)</b>\n"
            "• <b>Gate 1 — Market Regime:</b> confirms the market is range-bound "
            "(ADX, ATR, swing range)\n"
            "• <b>Gate 2 — Positioning:</b> checks funding rate and open-interest "
            "dynamics are not signalling crowded conditions\n"
            "• <b>Gate 3 — Liquidation Safety:</b> verifies your liquidation price "
            "has enough buffer relative to the proposed grid\n"
            "\n"
            "Based on the results you receive one of three verdicts:\n"
            "🚀 <b>LAUNCH</b> — all conditions met, safe to start\n"
            "⚠️ <b>REVIEW</b> — caution signals, manual review recommended\n"
            "⏸️ <b>HOLD</b> — hard limits breached, do not launch\n"
            "\n"
            "Use /help to see all available commands.",
            parse_mode="HTML",
        )

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(_HELP_TEXT, parse_mode="HTML")

    return router

import structlog
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from source.application.services.bot_management_service import BotManagementService
from source.application.services.health_monitor_service import HealthMonitorService
from source.domain.entities.monitoring import Bot, HealthSnapshot
from source.domain.value_objects import Symbol
from source.infrastructure.telegram.formater import TelegramMessageFormatter
from source.presentation.bot.keyboards.inlines import BotActionCD
from source.settings import Settings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def monitor_router(  # noqa: C901, PLR0915
    monitor_service: HealthMonitorService,
    bot_management: BotManagementService,
    settings: Settings,
) -> Router:
    router = Router(name="monitor")
    fmt = TelegramMessageFormatter()

    def _resolve_symbol(argument: str | None) -> Symbol | None:
        if not argument:
            return None
        try:
            return Symbol(argument.strip())
        except ValueError:
            return None

    @router.message(Command("status"))
    async def handle_status(message: Message, command: CommandObject) -> None:
        arg = command.args.strip() if command.args else ""
        symbol = _resolve_symbol(arg) if arg else None

        if symbol:
            await _show_detail(message, symbol, fmt)
        else:
            await _show_summary(message, fmt)

    @router.message(Command("pause"))
    async def handle_pause(message: Message, command: CommandObject) -> None:
        symbol = _resolve_symbol(command.args)
        if symbol is None:
            await message.reply("⚠️ Usage: /pause SYMBOL (e.g. /pause BTC_USDT_PERP)")
            return

        try:
            await bot_management.pause_bot(symbol)
            await message.reply(f"⏸️ Bot {symbol.value} paused by monitor.")
        except Exception as exc:
            await message.reply(f"❌ Failed to pause {symbol.value}: {exc}")

    @router.message(Command("resume"))
    async def handle_resume(message: Message, command: CommandObject) -> None:
        symbol = _resolve_symbol(command.args)
        if symbol is None:
            await message.reply("⚠️ Usage: /resume SYMBOL (e.g. /resume BTC_USDT_PERP)")
            return

        try:
            await bot_management.resume_bot(symbol)
            await message.reply(f"▶️ Bot {symbol.value} resumed.")
        except Exception as exc:
            await message.reply(f"❌ Failed to resume {symbol.value}: {exc}")

    @router.message(Command("close"))
    async def handle_close(message: Message, command: CommandObject) -> None:
        symbol = _resolve_symbol(command.args)
        if symbol is None:
            await message.reply("⚠️ Usage: /close SYMBOL (e.g. /close BTC_USDT_PERP)")
            return

        try:
            await bot_management.close_bot(symbol, reason="manual via Telegram")
            await message.reply(f"❌ Bot {symbol.value} closed.")
        except Exception as exc:
            await message.reply(f"❌ Failed to close {symbol.value}: {exc}")

    @router.message(Command("reconfigure"))
    async def handle_reconfigure(message: Message, command: CommandObject) -> None:
        symbol = _resolve_symbol(command.args)
        if symbol is None:
            await message.reply("⚠️ Usage: /reconfigure SYMBOL (e.g. /reconfigure BTC_USDT_PERP)")
            return

        await message.reply(f"🔄 Evaluating new parameters for {symbol.value} — running gates...")
        try:
            proposal = await bot_management.reconfigure_bot(symbol)
            if proposal is None:
                await message.reply(f"❌ Reconfigure blocked — one or more gates failed for {symbol.value}.")
            else:
                await message.reply("✅ Reconfigure proposal ready. Use bot action buttons to confirm.")
        except Exception as exc:
            await message.reply(f"❌ Reconfigure failed for {symbol.value}: {exc}")

    @router.message(Command("settings"))
    async def handle_settings(message: Message) -> None:
        mon = settings.monitoring
        lines = [
            "<b>⚙️ Monitoring Settings</b>",
            "",
            f"🔁 Health check: every <b>{mon.intervals.health_check_minutes} min</b>",
            f"⏱️ Alert debounce: <b>{mon.intervals.alert_debounce_minutes} min</b>",
            f"🗑️ Metrics TTL: <b>{mon.intervals.metrics_ttl_days} days</b>",
            f"🤖 Auto-adjust: <b>{'ON' if mon.auto_adjust_enabled else 'OFF'}</b>",
            f"🔴 Auto-pause on RED: <b>{'ON' if mon.auto_pause_on_red else 'OFF'}</b>",
            f"🟢 Auto-resume on GREEN: <b>{'ON' if mon.auto_resume_on_green else 'OFF'}</b>",
            f"🟡 Consecutive YELLOW before action: <b>{mon.max_consecutive_yellow_before_action}</b>",
        ]
        await message.reply("\n".join(lines), parse_mode="HTML")

    # ── Callbacks  ───────────────────────────────────────────────────

    @router.callback_query(BotActionCD.filter(F.action == "pause"))
    async def handle_pause_cb(callback: CallbackQuery, callback_data: BotActionCD) -> None:
        symbol = _resolve_symbol(callback_data.symbol)
        if symbol is None:
            await callback.answer("Unknown symbol", show_alert=True)
            return
        try:
            await bot_management.pause_bot(symbol)
            await callback.message.edit_text(f"⏸️ Bot {symbol.value} paused.")  # type: ignore[union-attr]
            await callback.answer()
        except Exception as exc:
            await callback.answer(f"Error: {exc}", show_alert=True)

    @router.callback_query(BotActionCD.filter(F.action == "resume"))
    async def handle_resume_cb(callback: CallbackQuery, callback_data: BotActionCD) -> None:
        symbol = _resolve_symbol(callback_data.symbol)
        if symbol is None:
            await callback.answer("Unknown symbol", show_alert=True)
            return
        try:
            await bot_management.resume_bot(symbol)
            await callback.message.edit_text(f"▶️ Bot {symbol.value} resumed.")  # type: ignore[union-attr]
            await callback.answer()
        except Exception as exc:
            await callback.answer(f"Error: {exc}", show_alert=True)

    @router.callback_query(BotActionCD.filter(F.action == "close"))
    async def handle_close_cb(callback: CallbackQuery, callback_data: BotActionCD) -> None:
        symbol = _resolve_symbol(callback_data.symbol)
        if symbol is None:
            await callback.answer("Unknown symbol", show_alert=True)
            return
        try:
            await bot_management.close_bot(symbol, reason="callback")
            await callback.message.edit_text(f"❌ Bot {symbol.value} closed.")  # type: ignore[union-attr]
            await callback.answer()
        except Exception as exc:
            await callback.answer(f"Error: {exc}", show_alert=True)

    @router.callback_query(BotActionCD.filter(F.action == "reconfigure"))
    async def handle_reconfigure_cb(callback: CallbackQuery, callback_data: BotActionCD) -> None:
        symbol = _resolve_symbol(callback_data.symbol)
        if symbol is None:
            await callback.answer("Unknown symbol", show_alert=True)
            return
        try:
            proposal = await bot_management.reconfigure_bot(symbol)
            text = (
                f"❌ Reconfigure blocked — gates failed for {symbol.value}."
                if proposal is None
                else f"🔄 Reconfigure proposal ready for {symbol.value}."
            )
            await callback.message.edit_text(text)  # type: ignore[union-attr]
            await callback.answer()
        except Exception as exc:
            await callback.answer(f"Error: {exc}", show_alert=True)

    @router.callback_query(BotActionCD.filter(F.action == "acknowledge"))
    async def handle_acknowledge_cb(callback: CallbackQuery, callback_data: BotActionCD) -> None:  # noqa: ARG001
        try:
            await callback.message.edit_reply_markup(reply_markup=None)  # type: ignore[union-attr]
            await callback.answer()
        except Exception as exc:
            await callback.answer(f"Error: {exc}", show_alert=True)

    async def _show_summary(message: Message, formatter: TelegramMessageFormatter) -> None:
        bots = await _get_active_bots()
        text = formatter.format_status_all(bots)
        await message.reply(text, parse_mode="HTML")

    async def _show_detail(message: Message, symbol: Symbol, formatter: TelegramMessageFormatter) -> None:
        bots = await _get_active_bots()
        bot = next((b for b in bots if b.symbol == symbol), None)
        if bot is None:
            await message.reply(f"⚠️ No active bot found for {symbol.value}.")
            return

        snapshots = await _get_latest_snapshot(bot)
        if snapshots is None:
            await message.reply(f"⚠️ No health snapshot yet for {symbol.value}.")
            return

        text = formatter.format_status_detail(bot, snapshots)
        await message.reply(text, parse_mode="HTML")

    async def _get_active_bots() -> list[Bot]:
        try:
            return await monitor_service._pull_active_bots()  # noqa: SLF001
        except Exception:
            return []

    async def _get_latest_snapshot(bot: Bot) -> HealthSnapshot | None:
        if bot.oid is None:
            return None
        return await monitor_service._get_latest_snapshot(bot.oid)  # noqa: SLF001

    return router

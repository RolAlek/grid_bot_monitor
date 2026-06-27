import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.value_objects import Symbol


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def router_factory(
    weekly_runner: RunWeeklyFullAssessment,
    decision_service: DecisionLogService,
    symbol: Symbol = Symbol.BTC,
) -> Router:
    router = Router(name="decision")

    @router.message(Command("assess"))
    async def handle_assess(message: Message) -> None:
        logger.info("Manual /assess requested by user_id=%s", message.from_user.id if message.from_user else "unknown")
        await message.answer("Running full assessment — this may take a few seconds…")
        try:
            async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):  # type: ignore[arg-type]
                await weekly_runner.run()
        except Exception:
            logger.exception("Assessment failed")
            await message.answer("Assessment failed — check logs for details.")

    @router.message(Command("verdict"))
    async def handle_verdict(message: Message) -> None:
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):  # type: ignore[arg-type]
            verdict = await decision_service.get_last_decision(symbol)
            if verdict is None:
                await message.answer("No verdict on record yet. Run /assess first.")
                return

            lines = [
                f"Last verdict: {verdict.action.value.upper()} ({verdict.as_of.strftime('%Y-%m-%d %H:%M UTC')})",
            ]
            for gate in verdict.gates:
                reason = gate.reasons[0] if gate.reasons else "ok"
                lines.append(f"  {gate.gate.name}: {gate.status.name} — {reason}")

            if verdict.suggested_grid_top is not None:
                lines.append(
                    f"Range: {verdict.suggested_grid_bottom:,.0f} - {verdict.suggested_grid_top:,.0f}"
                    f"  |  Leverage: {verdict.suggested_leverage}x"
                )

            await message.answer("\n".join(lines))

    return router

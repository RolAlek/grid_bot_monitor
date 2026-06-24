import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from source.application.services.decision_log_service import DecisionLogService
from source.application.services.run_weekly_full_assessment import RunWeeklyFullAssessment
from source.domain.value_objects import Symbol


logger = logging.getLogger(__name__)


def router_factory(
    weekly_runner: RunWeeklyFullAssessment,
    decision_service: DecisionLogService,
    symbol: Symbol = Symbol.BTC,
) -> Router:
    router = Router(name="decision")

    @router.message(Command("assess"))
    async def handle_assess(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.info("Manual /assess requested by user_id=%s", user_id)
        await message.answer("Running full assessment — this may take a few seconds…")

        try:
            verdict = await weekly_runner.run()
            await message.answer(f"Assessment complete. Verdict: {verdict.action.value.upper()}")
        except Exception as exc:
            logger.exception("Assessment failed", exc_info=exc)
            await message.answer("Assessment failed — check logs for details.")

    @router.message(Command("verdict"))
    async def handle_verdict(message: Message) -> None:
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

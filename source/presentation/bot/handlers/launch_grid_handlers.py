import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery
from structlog import get_logger

from source.application.services.grid_service import GridBotService
from source.presentation.bot.keyboards.inlines import ApplyDecisionCD, Mode


logger: structlog.stdlib.BoundLogger = get_logger(__name__)


def launch_grid_factory(grid_launch_service: GridBotService) -> Router:
    router = Router(name="launch")

    @router.callback_query(ApplyDecisionCD.filter(F.mode == Mode.AUTO))
    async def handle_auto_launch_callback(callback_query: CallbackQuery, callback_data: ApplyDecisionCD) -> None:
        await callback_query.answer(text="Auto launch submitted", show_alert=True)

        try:
            grid = await grid_launch_service.launch_grid_with_api(callback_data.verdict_id)

            await callback_query.message.edit_text(text=f"✅ Grid launched successfully\n{grid}")  # type: ignore[union-attr]

            logger.info(
                "Bot launched automatically",
                verdict_id=callback_data.verdict_id,
                bot_id=grid.oid,
                symbol=grid.symbol.value,
                user_id=callback_query.from_user.id,
            )
        except Exception as exc:
            logger.exception("Failed to launch bot", verdict_id=callback_data.verdict_id, error=str(exc))
            await callback_query.message.edit_text(text=f"⚠️ Error launching the grid: {exc}")  # type: ignore[union-attr]

    return router

from typing import Any, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities.monitoring import ActiveBot
from source.domain.value_objects import HealthStatus, Symbol
from source.infrastructure.database.models.grid_launch import GridLaunchModel
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository


class SQLAlchemyActiveBotRepository(SQLAlchemyBaseRepository[ActiveBot, GridLaunchModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GridLaunchModel)

    async def add(self, data: ActiveBot) -> ActiveBot:
        raise NotImplementedError(
            "ActiveBotRepository.add() is unsafe — it would overwrite grid fields. "
            "Use update_monitoring_fields() instead."
        )

    def _as_entity(self, row: GridLaunchModel) -> ActiveBot:
        return ActiveBot(
            oid=row.oid,
            symbol=Symbol(row.symbol),
            external_bot_id=row.external_id,
            status=row.status,
            health_status=HealthStatus(row.health_status),
            current_pnl=None,  # populated by health-check, not from realized_pnl
            current_pnl_pct=None,
            distance_to_liquidation_pct=row.distance_to_liquidation_pct,
            grid_fill_ratio=row.grid_fill_ratio,
            last_price=row.last_price,
            last_health_check_at=row.last_health_check_at,
            auto_adjust_enabled=row.auto_adjust_enabled,
            paused_by_monitor=row.paused_by_monitor,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _as_orm_model(self, data: ActiveBot) -> GridLaunchModel:
        return GridLaunchModel(
            oid=data.oid,
            symbol=data.symbol.value,
            external_id=data.external_bot_id,
            status=data.status,
            health_status=data.health_status.value,
            realized_pnl=data.current_pnl,
            distance_to_liquidation_pct=data.distance_to_liquidation_pct,
            grid_fill_ratio=data.grid_fill_ratio,
            last_price=data.last_price,
            last_health_check_at=data.last_health_check_at,
            auto_adjust_enabled=data.auto_adjust_enabled,
            paused_by_monitor=data.paused_by_monitor,
        )

    async def update_monitoring_fields(self, bot: ActiveBot) -> bool:
        stmt = (
            update(self._model)
            .where(self._model.oid == bot.oid)
            .values(
                health_status=bot.health_status.value,
                distance_to_liquidation_pct=bot.distance_to_liquidation_pct,
                grid_fill_ratio=bot.grid_fill_ratio,
                last_price=bot.last_price,
                last_health_check_at=bot.last_health_check_at,
                auto_adjust_enabled=bot.auto_adjust_enabled,
                paused_by_monitor=bot.paused_by_monitor,
            )
        )

        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return result.rowcount > 0

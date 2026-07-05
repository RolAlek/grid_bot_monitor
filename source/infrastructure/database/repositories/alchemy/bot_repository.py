from typing import Any, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities.monitoring import Bot
from source.domain.value_objects import GridLaunchStatus, GridType, HealthStatus, Symbol, Trend
from source.infrastructure.database.models.grid_launch import GridLaunchModel
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository


class SQLAlchemyBotRepository(SQLAlchemyBaseRepository[Bot, GridLaunchModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GridLaunchModel)

    def _as_entity(self, row: GridLaunchModel) -> Bot:
        return Bot(
            # ── Identity ──
            oid=row.oid,
            symbol=Symbol(row.symbol),
            external_id=row.external_id,
            status=GridLaunchStatus(row.status),
            # ── Grid config ──
            top=row.grid_top,
            bottom=row.grid_bottom,
            levels=row.grid_levels,
            trend=Trend(row.grid_regime),
            grid_type=GridType(row.grid_type),
            leverage=row.grid_leverage,
            investment=row.quote_investment,
            stop_loss=row.stop_loss,
            take_profit=row.take_profit,
            # ── Lifecycle ──
            decision_verdict_oid=row.decision_verdict_oid,
            created_at=row.created_at,
            closed_at=row.closed_at,
            updated_at=row.updated_at,
            # ── Financials ──
            realized_pnl=row.realized_pnl,
            current_pnl=None,  # populated by health-check, not from DB
            current_pnl_pct=None,
            # ── Monitoring ──
            health_status=HealthStatus(row.health_status),
            distance_to_liquidation_pct=row.distance_to_liquidation_pct,
            grid_fill_ratio=row.grid_fill_ratio,
            last_price=row.last_price,
            last_health_check_at=row.last_health_check_at,
            auto_adjust_enabled=row.auto_adjust_enabled,
            paused_by_monitor=row.paused_by_monitor,
        )

    def _as_orm_model(self, data: Bot) -> GridLaunchModel:
        return GridLaunchModel(
            oid=data.oid,
            symbol=data.symbol.value,
            external_id=data.external_id,
            status=data.status.value,
            # Grid config
            grid_top=data.top,
            grid_bottom=data.bottom,
            grid_levels=data.levels,
            grid_regime=data.trend.value if data.trend else None,
            grid_type=data.grid_type.value if data.grid_type else None,
            grid_leverage=data.leverage,
            quote_investment=data.investment,
            stop_loss=data.stop_loss,
            take_profit=data.take_profit,
            # Lifecycle
            decision_verdict_oid=data.decision_verdict_oid,
            closed_at=data.closed_at,
            realized_pnl=data.current_pnl,  # current_pnl → realized_pnl column
            # Monitoring
            health_status=data.health_status.value,
            distance_to_liquidation_pct=data.distance_to_liquidation_pct,
            grid_fill_ratio=data.grid_fill_ratio,
            last_price=data.last_price,
            last_health_check_at=data.last_health_check_at,
            auto_adjust_enabled=data.auto_adjust_enabled,
            paused_by_monitor=data.paused_by_monitor,
        )

    async def update_monitoring_fields(self, bot: Bot) -> bool:
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

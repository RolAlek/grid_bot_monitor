from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import CursorResult, delete
from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities.monitoring import HealthSnapshot
from source.domain.value_objects import HealthStatus, Symbol
from source.infrastructure.database.models.health_snapshot import HealthSnapshotModel
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository


class SQLAlchemyHealthSnapshotRepository(SQLAlchemyBaseRepository[HealthSnapshot, HealthSnapshotModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HealthSnapshotModel)

    def _as_entity(self, row: HealthSnapshotModel) -> HealthSnapshot:
        return HealthSnapshot(
            grid_launch_oid=row.grid_launch_oid,
            symbol=Symbol(row.symbol),
            created_at=row.created_at,
            adx14=row.adx14,
            atr14=row.atr14,
            atr_pct_of_price=row.atr_pct_of_price,
            rsi14=row.rsi14,
            realized_vol_1d=row.realized_vol_1d,
            realized_vol_7d=row.realized_vol_7d,
            last_price=row.last_price,
            unrealized_pnl=row.unrealized_pnl,
            unrealized_pnl_pct=row.unrealized_pnl_pct,
            grid_fill_ratio=row.grid_fill_ratio,
            matched_orders=row.matched_orders,
            total_orders=row.total_orders,
            distance_to_liquidation_pct=row.distance_to_liquidation_pct,
            liquidation_price=row.liquidation_price,
            leverage=row.leverage,
            funding_rate=row.funding_rate,
            funding_rate_annualized_pct=row.funding_rate_annualized_pct,
            health_status=HealthStatus(row.health_status),
            health_score=row.health_score,
            triggered_alerts=tuple(alert.alert_type for alert in row.alerts),
        )

    def _as_orm_model(self, data: HealthSnapshot) -> HealthSnapshotModel:
        return HealthSnapshotModel(
            grid_launch_oid=data.grid_launch_oid,
            symbol=data.symbol.value,
            adx14=data.adx14,
            atr14=data.atr14,
            atr_pct_of_price=data.atr_pct_of_price,
            rsi14=data.rsi14,
            realized_vol_1d=data.realized_vol_1d,
            realized_vol_7d=data.realized_vol_7d,
            last_price=data.last_price,
            unrealized_pnl=data.unrealized_pnl,
            unrealized_pnl_pct=data.unrealized_pnl_pct,
            grid_fill_ratio=data.grid_fill_ratio,
            matched_orders=data.matched_orders,
            total_orders=data.total_orders,
            distance_to_liquidation_pct=data.distance_to_liquidation_pct,
            liquidation_price=data.liquidation_price,
            leverage=data.leverage,
            funding_rate=data.funding_rate,
            funding_rate_annualized_pct=data.funding_rate_annualized_pct,
            health_status=data.health_status.value,
            health_score=data.health_score,
        )

    async def delete_older_than(self, days: int) -> int:
        stmt = delete(self._model).where(self._model.created_at < datetime.now(UTC) - timedelta(days=days))
        result: CursorResult[Any] = await self._session.execute(stmt)  # type: ignore[assignment]
        await self._session.flush()
        return result.rowcount  # type: ignore[no-any-return]

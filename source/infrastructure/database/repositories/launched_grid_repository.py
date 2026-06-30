from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities import Grid
from source.domain.value_objects import GridLaunchStatus, GridType, Symbol, Trend
from source.infrastructure.database.models.models import GridLaunchModel
from source.infrastructure.database.repositories.base import SQLAlchemyBaseRepository


class SQLAlchemyLaunchedGridRepository(SQLAlchemyBaseRepository[Grid, GridLaunchModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GridLaunchModel)

    def _to_entity(self, row: GridLaunchModel) -> Grid:

        return Grid(
            oid=row.oid,
            symbol=Symbol(row.symbol),
            top=row.grid_top,
            bottom=row.grid_bottom,
            levels=row.grid_levels,
            trend=Trend(row.grid_regime),
            grid_type=GridType(row.grid_type),
            leverage=row.grid_leverage,
            investment=row.quote_investment,
            status=GridLaunchStatus(row.status),
            created_at=row.created_at,
            closed_at=row.closed_at,
            realized_pnl=row.realized_pnl,
            decision_verdict_oid=row.decision_verdict_oid,
            stop_loss=row.stop_loss,
            take_profit=row.take_profit,
            external_id=row.external_id,
        )

    def _from_entity(self, data: Grid) -> GridLaunchModel:
        return GridLaunchModel(
            symbol=data.symbol.value,
            grid_top=data.top,
            grid_bottom=data.bottom,
            grid_levels=data.levels,
            grid_regime=data.trend.value,
            grid_type=data.grid_type.value,
            grid_leverage=int(data.leverage),
            quote_investment=data.investment,
            stop_loss=data.stop_loss,
            take_profit=data.take_profit,
            status=data.status.value,
            closed_at=data.closed_at,
            realized_pnl=data.realized_pnl,
            decision_verdict_oid=data.decision_verdict_oid,
            external_id=data.external_id,
        )

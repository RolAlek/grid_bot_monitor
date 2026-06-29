from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities import DecisionVerdict, Grid
from source.domain.value_objects import (
    Gate,
    GateResult,
    GateStatus,
    GridLaunchStatus,
    GridType,
    Symbol,
    Trend,
    VerdictAction,
)
from source.infrastructure.database.models.models import GridLaunchModel
from source.infrastructure.database.repositories.base import SQLAlchemyBaseRepository


class SQLAlchemyLaunchedGridRepository(SQLAlchemyBaseRepository[Grid, GridLaunchModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GridLaunchModel)

    def _to_entity(self, row: GridLaunchModel) -> Grid:
        verdict_row = row.decision_verdict

        verdict = DecisionVerdict(
            symbol=Symbol(verdict_row.symbol),
            as_of=verdict_row.created_at,
            action=VerdictAction(verdict_row.action),
            gates=tuple(
                GateResult(
                    gate=Gate(gate["gate"]),
                    status=GateStatus(gate["status"]),
                    reasons=tuple(gate["reasons"]),
                    raw_values=gate["raw_values"],
                )
                for gate in verdict_row.gates_json
            ),
            notes=verdict_row.notes,
        )
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
            decision_verdict=verdict,
            created_at=row.created_at,
            closed_at=row.closed_at,
            realized_pnl=row.realized_pnl,
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
            status=data.status.value,
            closed_at=data.closed_at,
            realized_pnl=data.realized_pnl,
        )

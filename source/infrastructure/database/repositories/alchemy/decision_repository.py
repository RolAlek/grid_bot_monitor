from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities import DecisionVerdict, GateResult, ProposedGridParams
from source.domain.value_objects import Gate, GateStatus, GridType, Symbol, Trend, VerdictAction
from source.infrastructure.database.models import DecisionLog
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository


class SQLAlchemyDecisionLogRepository(SQLAlchemyBaseRepository[DecisionVerdict, DecisionLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DecisionLog)

    def _as_entity(self, row: DecisionLog) -> DecisionVerdict:
        suggested = None
        if row.suggested_parameters_json:
            parameters = row.suggested_parameters_json
            suggested = ProposedGridParams(
                symbol=Symbol(parameters["symbol"]),
                trend=Trend(parameters["trend"]),
                grid_type=GridType(parameters["grid_type"]),
                top=parameters["top"],
                bottom=parameters["bottom"],
                grid_levels=parameters["grid_levels"],
                leverage=parameters["leverage"],
                quote_investment=parameters["quote_investment"],
                stop_loss=parameters.get("stop_loss"),
                take_profit=parameters.get("take_profit"),
                last_price=parameters["last_price"],
            )

        return DecisionVerdict(
            oid=row.oid,
            symbol=Symbol(row.symbol),
            created_at=row.created_at,
            action=VerdictAction(row.action),
            gates=tuple(
                GateResult(
                    gate=Gate(gate["gate"]),
                    status=GateStatus(gate["status"]),
                    reasons=tuple(gate["reasons"]),
                    raw_values=gate["raw_values"],
                )
                for gate in row.gates_json
            ),
            notes=row.notes,
            suggested_parameters=suggested,
        )

    def _as_orm_model(self, data: DecisionVerdict) -> DecisionLog:
        def _serialize_gate(gate: GateResult) -> dict[str, Any]:
            return {
                "gate": gate.gate.value,
                "status": gate.status.value,
                "reasons": list(gate.reasons),
                "raw_values": gate.raw_values,
            }

        suggested_json = None
        if data.suggested_parameters:
            parameters = data.suggested_parameters
            suggested_json = {
                "symbol": parameters.symbol.value,
                "trend": parameters.trend.value,
                "grid_type": parameters.grid_type.value,
                "top": parameters.top,
                "bottom": parameters.bottom,
                "grid_levels": parameters.grid_levels,
                "leverage": parameters.leverage,
                "quote_investment": parameters.quote_investment,
                "stop_loss": parameters.stop_loss,
                "take_profit": parameters.take_profit,
                "last_price": parameters.last_price,
            }

        return DecisionLog(
            symbol=data.symbol.value,
            action=data.action.value,
            gates_json=tuple(_serialize_gate(gate) for gate in data.gates),
            notes=data.notes,
            suggested_parameters_json=suggested_json,
        )

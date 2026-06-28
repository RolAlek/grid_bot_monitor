from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities import DecisionVerdict
from source.domain.value_objects import Gate, GateResult, GateStatus, Symbol, VerdictAction
from source.infrastructure.database.models import DecisionLog
from source.infrastructure.database.repositories.base import SQLAlchemyBaseRepository


class SQLAlchemyDecisionLogRepository(SQLAlchemyBaseRepository[DecisionVerdict, DecisionLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DecisionLog)

    def _to_entity(self, row: DecisionLog) -> DecisionVerdict:
        return DecisionVerdict(
            symbol=Symbol(row.symbol),
            as_of=row.created_at,
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
        )

    def _from_entity(self, data: DecisionVerdict) -> DecisionLog:
        return DecisionLog(
            symbol=data.symbol.value,
            action=data.action.value,
            gates_json=tuple(asdict(gate) for gate in data.gates),
            notes=data.notes,
        )

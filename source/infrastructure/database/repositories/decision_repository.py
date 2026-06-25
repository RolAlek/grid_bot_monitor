from abc import abstractmethod
from dataclasses import asdict
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities import DecisionVerdict, GateResult
from source.domain.value_objects import Gate, GateStatus, Symbol, VerdictAction
from source.infrastructure.database.models import DecisionLog
from source.infrastructure.database.repositories.base import AbstractSQLAlchemyRepository


class DecisionLogRepository(Protocol):
    @abstractmethod
    async def get_last_decision(self, symbol: Symbol) -> DecisionVerdict | None: ...

    @abstractmethod
    async def save_decision(self, data: DecisionVerdict) -> None: ...


class SQLAlchemyDecisionLogRepository(AbstractSQLAlchemyRepository, DecisionLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_last_decision(self, symbol: Symbol) -> DecisionVerdict | None:
        stmt = (
            select(DecisionLog)
            .where(DecisionLog.symbol == symbol.value)
            .order_by(DecisionLog.created_at.desc())
            .limit(1)
        )
        result = await self._session.scalar(stmt)

        if not result:
            return None

        return DecisionVerdict(
            symbol=Symbol(result.symbol),
            as_of=result.created_at,
            action=VerdictAction(result.action),
            gates=tuple(
                GateResult(
                    gate=Gate(gate["gate"]),
                    status=GateStatus(gate["status"]),
                    reasons=tuple(gate["reasons"]),
                    raw_values=gate["raw_values"],
                )
                for gate in result.gates_json
            ),
            notes=result.notes,
        )

    async def save_decision(self, data: DecisionVerdict) -> None:
        obj = DecisionLog(
            symbol=data.symbol.value,
            action=data.action.value,
            gates_json=tuple(asdict(gate) for gate in data.gates),
            notes=data.notes,
        )
        self._session.add(obj)
        await self._session.commit()

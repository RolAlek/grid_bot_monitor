from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.application.dto import DecisionLogCreateDTO, DecisionLogGetDTO
from source.domain.value_objects import Symbol, VerdictAction
from source.infrastructure.database.models import DecisionLog
from source.infrastructure.database.repositories.base import BaseSQLAlchemyRepository


class DecisionLogRepository(BaseSQLAlchemyRepository[DecisionLog, DecisionLogCreateDTO]):
    def __init__(self, session: AsyncSession, model: type[DecisionLog]) -> None:
        super().__init__(session, model)

    async def get_last_decision(self, symbol: Symbol) -> DecisionLogGetDTO | None:
        stmt = (
            select(self._model)
            .where(self._model.symbol == symbol.value)
            .order_by(self._model.created_at.desc())
            .limit(1)
        )
        result = await self._session.scalar(stmt)

        if not result:
            return None

        return DecisionLogGetDTO(
            symbol=Symbol(result.symbol),
            action=VerdictAction(result.action),
            gates_json=result.gates_json,
            notes=result.notes,
            created_at=result.created_at,
        )

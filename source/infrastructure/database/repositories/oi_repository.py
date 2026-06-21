from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from source.application.dto import OISnapshotCrateDTO, OISnapshotReadDTO
from source.domain.value_objects import Symbol
from source.infrastructure.database.models.models import OISnapshot
from source.infrastructure.database.repositories.base import BaseSQLAlchemyRepository


class OISnapshotRepository(BaseSQLAlchemyRepository[OISnapshot, OISnapshotCrateDTO]):
    def __init__(self, session: AsyncSession, model: type[OISnapshot]) -> None:
        super().__init__(session, model)

    async def get_oi_snapshots_last_7d(
        self,
        symbol: Symbol,
        as_of: datetime,
    ) -> list[OISnapshotReadDTO]:
        cutoff = as_of - timedelta(days=7)
        stmt = (
            select(self._model)
            .where(
                and_(
                    self._model.symbol == symbol.value,
                    self._model.created_at >= cutoff,
                )
            )
            .order_by(self._model.created_at.asc())
        )
        results = await self._session.scalars(stmt)
        return [
            OISnapshotReadDTO(
                symbol=Symbol(snapshot.symbol),
                open_interests=snapshot.open_interests,
            )
            for snapshot in results
        ]

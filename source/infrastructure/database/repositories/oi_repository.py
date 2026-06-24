from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities import FundingOiSnapshot
from source.domain.value_objects import Symbol
from source.infrastructure.database.models.models import OISnapshot


class SnapshotRepository(Protocol):
    @abstractmethod
    async def get_oi_snapshots_last_7d(self, symbol: Symbol, as_of: datetime) -> list[FundingOiSnapshot]: ...

    @abstractmethod
    async def save_snapshot(self, snapshot_data: FundingOiSnapshot) -> None: ...


class SQLAlchemySnapshotRepository(SnapshotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_oi_snapshots_last_7d(self, symbol: Symbol, as_of: datetime) -> list[FundingOiSnapshot]:
        stmt = (
            select(OISnapshot)
            .where(
                and_(
                    OISnapshot.symbol == symbol.value,
                    OISnapshot.created_at >= as_of.replace(tzinfo=None) - timedelta(days=7),
                )
            )
            .order_by(OISnapshot.created_at.asc())
        )
        results = (await self._session.scalars(stmt)).all()
        return [
            FundingOiSnapshot(
                symbol=Symbol(snapshot.symbol),
                as_of=snapshot.created_at,
                funding_rate_last=snapshot.funding_rate_last,
                funding_rate_annualized_pct=snapshot.funding_rate_annualized_pct,
                open_interest=snapshot.open_interest,
                oi_pct_change_7d=snapshot.oi_pct_change_7d,
            )
            for snapshot in results
        ]

    async def save_snapshot(self, snapshot_data: FundingOiSnapshot) -> None:
        obj = OISnapshot(
            symbol=snapshot_data.symbol.value,
            funding_rate_last=snapshot_data.funding_rate_last,
            funding_rate_annualized_pct=snapshot_data.funding_rate_annualized_pct,
            open_interest=snapshot_data.open_interest,
            oi_pct_change_7d=snapshot_data.oi_pct_change_7d,
        )
        self._session.add(obj)
        await self._session.commit()

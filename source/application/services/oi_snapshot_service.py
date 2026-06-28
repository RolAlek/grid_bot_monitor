from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta

from source.constants import MIN_SNAPSHOTS_LENGTH
from source.domain.entities import FundingOiSnapshot
from source.domain.value_objects import Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters.base import BaseFieldCondition, BaseQueryFilter, Operator


class OISnapshotService:
    def __init__(
        self,
        provider_oi_snapshot_repository: Callable[
            [], AbstractAsyncContextManager[AbstractRepository[FundingOiSnapshot]]
        ],
    ) -> None:
        self._provider_oi_snapshot_repository = provider_oi_snapshot_repository

    async def compute_oi_pct_change_7d(self, symbol: Symbol, as_of: datetime, newest_oi: float) -> float | None:
        filters = BaseQueryFilter(
            conditions=(
                BaseFieldCondition(field="symbol", operator=Operator.EQUALS, value=symbol.value),
                BaseFieldCondition(
                    field="created_at",
                    operator=Operator.GREATER_OR_EQUALS,
                    value=as_of.replace(tzinfo=None) - timedelta(days=7),
                ),
            ),
            order_by=("created_at",),
        )
        async with self._provider_oi_snapshot_repository() as repository:
            snapshots = await repository.get_list(filters)

        if len(snapshots) < MIN_SNAPSHOTS_LENGTH:
            return None

        oldest_oi = snapshots[0].open_interest

        if oldest_oi == 0:
            return None

        return (newest_oi - oldest_oi) / oldest_oi * 100

    async def persist_oi_snapshot(self, snapshot: FundingOiSnapshot) -> None:
        async with self._provider_oi_snapshot_repository() as repository:
            await repository.add(snapshot)

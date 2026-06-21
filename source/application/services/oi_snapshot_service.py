from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime

from source.application.dto import OISnapshotDTO
from source.domain.value_objects import Symbol
from source.infrastructure.database.repositories import OISnapshotRepository


class OISnapshotService:
    def __init__(
        self,
        provider_oi_snapshot_repository: Callable[
            [], AbstractAsyncContextManager[OISnapshotRepository]
        ],
    ) -> None:
        self._provider_oi_snapshot_repository = provider_oi_snapshot_repository

    async def compute_oi_pct_change_7d(
        self,
        symbol: Symbol,
        as_of: datetime,
    ) -> float | None:
        async with self._provider_oi_snapshot_repository() as repository:
            snapshots = await repository.get_oi_snapshots_last_7d(symbol, as_of)

        if len(snapshots) < 2:
            return None

        oldest_oi = snapshots[0].open_interests
        newest_oi = snapshots[-1].open_interests

        if oldest_oi == 0:
            return None

        return (newest_oi - oldest_oi) / oldest_oi * 100

    async def persist_oi_snapshot(
        self,
        symbol: Symbol,
        open_interest: float,
    ) -> None:
        async with self._provider_oi_snapshot_repository() as repository:
            await repository.add(
                OISnapshotDTO(symbol=symbol, open_interests=open_interest)
            )

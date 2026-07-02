from datetime import UTC, datetime

from source.application.ports import GridPort
from source.domain.entities import DecisionVerdict, Grid, LiquidationEstimate, ProposedGridParams


class StalenessGuardAdapter:
    def __init__(self, delegate: GridPort, ttl_seconds: int = 120) -> None:
        self._delegate = delegate
        self._ttl = ttl_seconds
        self._cache: dict[ProposedGridParams, tuple[datetime, LiquidationEstimate]] = {}

    async def check_grid_params(self, params: ProposedGridParams) -> LiquidationEstimate:
        now = datetime.now(UTC)

        if exist := self._cache.get(params):
            cached_at, estimate = exist
            if (now - cached_at).total_seconds() < self._ttl:
                return estimate

        estimate = await self._delegate.check_grid_params(params)
        self._cache[params] = (now, estimate)
        return estimate

    async def place_grid(self, verdict: DecisionVerdict) -> Grid:
        return await self._delegate.place_grid(verdict)

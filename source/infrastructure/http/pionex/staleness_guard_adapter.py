from datetime import UTC, datetime

from source.application.ports import GridValidationPort
from source.domain.entities import LiquidationEstimate, ProposedGridParams


class StalenessGuardAdapter(GridValidationPort):
    def __init__(self, delegate: GridValidationPort, ttl_seconds: int = 120) -> None:
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

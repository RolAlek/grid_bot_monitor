from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta

import structlog

from source.application.ports import MarketDataPort
from source.constants import MIN_SNAPSHOTS_LENGTH
from source.domain.entities import FundingOiSnapshot, OpenInterest
from source.domain.exceptions import DuplicateOISnapshotError
from source.domain.value_objects import Symbol
from source.infrastructure.database.repositories.base import AbstractRepository
from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter, Operator


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class OISnapshotService:
    def __init__(
        self,
        provider_oi_snapshot_repository: Callable[
            [], AbstractAsyncContextManager[AbstractRepository[FundingOiSnapshot]]
        ],
        market_data_client: MarketDataPort,
    ) -> None:
        self._provider_oi_snapshot_repository = provider_oi_snapshot_repository
        self._market_data_client = market_data_client

    async def persist_oi_snapshot(self, snapshot: FundingOiSnapshot) -> FundingOiSnapshot:
        try:
            async with self._provider_oi_snapshot_repository() as repository:
                return await repository.add(snapshot)
        except Exception:
            logger.exception("Failed to persist OI snapshot", symbol=snapshot.symbol.value)
            raise

    async def create_snapshot(self, symbol: Symbol) -> FundingOiSnapshot:
        try:
            current_dt = datetime.now(UTC)
            funding_rate = await self._pull_latest_funding_rate(symbol)
            open_interest, oi_change = await self._pull_latest_oi(symbol, current_dt)

            return await self.persist_oi_snapshot(
                FundingOiSnapshot(
                    symbol=symbol,
                    created_at=current_dt,
                    funding_rate_last=funding_rate,
                    open_interest=open_interest.open_interest,
                    oi_pct_change_7d=oi_change,
                )
            )
        except DuplicateOISnapshotError:
            snapshot = await self.get_last_snapshot(symbol)
            if snapshot is None:
                logger.exception(
                    "Duplicate OI snapshot error occurred, but no last snapshot found",
                    symbol=symbol.value,
                )
                raise
            return snapshot

        except Exception:
            logger.exception("Failed to create OI snapshot", symbol=symbol.value)
            raise

    async def _pull_latest_funding_rate(self, symbol: Symbol) -> float:
        try:
            rows = await self._market_data_client.get_funding_rates(symbol, limit=1)
            rows.sort(key=lambda rate: rate.time)
            return float(rows[-1].rate)
        except Exception:
            logger.exception("Failed to fetch latest funding rate", symbol=symbol.value)
            raise

    async def _pull_latest_oi(self, symbol: Symbol, current_dt: datetime) -> tuple[OpenInterest, float | None]:
        try:
            oi = await self._market_data_client.get_open_interest(symbol)
            oi_change = await self._compute_oi_pct_change_7d(
                symbol=symbol,
                as_of=current_dt,
                newest_oi=oi.open_interest,
            )
            return oi, oi_change
        except Exception:
            logger.exception("Failed to fetch latest open interest", symbol=symbol.value)
            raise

    async def _compute_oi_pct_change_7d(self, symbol: Symbol, as_of: datetime, newest_oi: float) -> float | None:
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

    async def get_last_snapshot(self, symbol: Symbol) -> FundingOiSnapshot | None:
        filters = BaseQueryFilter(
            conditions=(BaseFieldCondition(field="symbol", operator=Operator.EQUALS, value=symbol.value),),
            order_by=("created_at",),
        )
        async with self._provider_oi_snapshot_repository() as repository:
            return await repository.get_one(filters)

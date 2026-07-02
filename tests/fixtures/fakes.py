from datetime import UTC, datetime

from source.domain.entities import DecisionVerdict, FundingOiSnapshot
from source.infrastructure.database.repositories.filters import BaseQueryFilter


class FakeDecisionLogRepository:
    def __init__(self) -> None:
        self._storage: list[DecisionVerdict] = []

    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[DecisionVerdict]:
        result = list(self._storage)
        if filters is not None:
            for condition in filters.conditions:
                if condition.field == "symbol":
                    result = [v for v in result if v.symbol.value == condition.value]

            if filters.order_by:
                for order_field in filters.order_by:
                    descending = order_field.startswith("-")
                    field = order_field[1:] if descending else order_field

                    if field == "created_at":
                        result.sort(key=lambda v: v.created_at or datetime.min.replace(tzinfo=UTC), reverse=descending)
        return result

    async def get_one(self, filters: BaseQueryFilter) -> DecisionVerdict | None:
        results = await self.get_list(filters)
        return results[0] if results else None

    async def get_by_oid(self, oid: str) -> DecisionVerdict | None:  # noqa: ARG002
        return None

    async def add(self, data: DecisionVerdict) -> DecisionVerdict:
        self._storage.append(data)
        return data


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self._snapshots: list[FundingOiSnapshot] = []

    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[FundingOiSnapshot]:
        if filters is None:
            return list(self._snapshots)
        result = list(self._snapshots)

        for condition in filters.conditions:
            match condition.field:
                case "symbol":
                    result = [s for s in result if s.symbol.value == condition.value]
                case "created_at":
                    cutoff = condition.value
                    result = [s for s in result if s.created_at.replace(tzinfo=UTC) >= cutoff.replace(tzinfo=UTC)]

        result.sort(key=lambda s: s.created_at)
        return result

    async def get_one(self, filters: BaseQueryFilter) -> FundingOiSnapshot | None:
        results = await self.get_list(filters)
        return results[0] if results else None

    async def get_by_oid(self, oid: str) -> FundingOiSnapshot | None:  # noqa: ARG002
        return None

    async def add(self, data: FundingOiSnapshot) -> FundingOiSnapshot:
        self._snapshots.append(data)
        return data

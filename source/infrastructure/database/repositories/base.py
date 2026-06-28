from abc import ABC, abstractmethod
from typing import TypeVar

from source.infrastructure.database.repositories.filters.base import QueryFilter


DomainT = TypeVar("DomainT")


class AbstractRepository[DT](ABC):
    @abstractmethod
    async def get_list(self, filters: QueryFilter) -> list[DT]: ...

    @abstractmethod
    async def get_one(self, filters: QueryFilter) -> DT | None: ...

    @abstractmethod
    async def add(self, data: DT) -> DT: ...

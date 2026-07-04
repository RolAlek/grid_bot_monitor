from abc import ABC, abstractmethod
from uuid import UUID

from source.infrastructure.database.repositories.filters import BaseQueryFilter


class AbstractRepository[ET](ABC):
    @abstractmethod
    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[ET]: ...

    @abstractmethod
    async def get_one(self, filters: BaseQueryFilter) -> ET | None: ...

    @abstractmethod
    async def get_by_oid(self, oid: UUID) -> ET | None: ...

    @abstractmethod
    async def add(self, data: ET) -> ET: ...

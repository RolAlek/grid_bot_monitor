from abc import ABC, abstractmethod

from source.domain.entities import DecisionVerdict
from source.infrastructure.database.repositories.filters import BaseQueryFilter


class Notifier(ABC):
    @abstractmethod
    async def send_alert(self, verdict: DecisionVerdict) -> None: ...

    @abstractmethod
    async def send_digest(self, verdict: DecisionVerdict) -> None: ...


class AbstractRepository[ET](ABC):
    @abstractmethod
    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[ET]: ...

    @abstractmethod
    async def get_one(self, filters: BaseQueryFilter) -> ET | None: ...

    @abstractmethod
    async def get_by_oid(self, oid: str) -> ET | None: ...

    @abstractmethod
    async def add(self, data: ET) -> ET: ...

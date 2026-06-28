from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from source.infrastructure.database.repositories.filters.alchemy import SQLAlchemyQueryFilter
from source.infrastructure.database.repositories.filters.base import BaseQueryFilter


class AbstractRepository[ET, FT: BaseQueryFilter[Any]](ABC):
    @abstractmethod
    async def get_list(self, filters: FT | None = None) -> list[ET]: ...

    @abstractmethod
    async def get_one(self, filters: FT) -> ET | None: ...

    @abstractmethod
    async def add(self, data: ET) -> ET: ...


class SQLAlchemyRepository[ET, MT: DeclarativeBase](AbstractRepository[ET, SQLAlchemyQueryFilter]):
    def __init__(self, session: AsyncSession, model: type[MT]) -> None:
        self._session = session
        self._model = model

    async def get_list(self, filters: SQLAlchemyQueryFilter | None = None) -> list[ET]:
        stmt = self._apply_filters(filters)
        rows = (await self._session.scalars(stmt)).all()
        return [self._to_entity(row) for row in rows]

    async def get_one(self, filters: SQLAlchemyQueryFilter) -> ET | None:
        stmt = self._apply_filters(filters)
        stmt = stmt.limit(1)
        row = await self._session.scalar(stmt)
        return self._to_entity(row) if row else None

    async def add(self, data: ET) -> ET:
        orm_obj = self._from_entity(data)
        self._session.add(orm_obj)
        await self._session.flush()

        return self._to_entity(orm_obj)

    def _apply_filters(self, filters: SQLAlchemyQueryFilter | None) -> Select[tuple[MT]]:
        stmt = select(self._model)

        if not filters:
            return stmt

        return filters.apply(stmt, self._model)

    @abstractmethod
    def _to_entity(self, row: MT) -> ET: ...

    @abstractmethod
    def _from_entity(self, data: ET) -> MT: ...

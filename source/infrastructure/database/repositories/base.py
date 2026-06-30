from abc import ABC, abstractmethod

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from source.infrastructure.database.repositories.filters.alchemy import SQLAlchemyFieldCondition, SQLAlchemyQueryFilter
from source.infrastructure.database.repositories.filters.base import BaseQueryFilter


class AbstractRepository[ET](ABC):
    @abstractmethod
    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[ET]: ...

    @abstractmethod
    async def get_one(self, filters: BaseQueryFilter) -> ET | None: ...

    @abstractmethod
    async def get_by_oid(self, oid: str) -> ET | None: ...

    @abstractmethod
    async def add(self, data: ET) -> ET: ...


class SQLAlchemyBaseRepository[ET, MT: DeclarativeBase](AbstractRepository[ET]):
    def __init__(self, session: AsyncSession, model: type[MT]) -> None:
        self._session = session
        self._model = model

    async def get_list(self, filters: BaseQueryFilter | None = None) -> list[ET]:
        stmt = self._apply_filters(filters)
        rows = (await self._session.scalars(stmt)).all()
        return [self._to_entity(row) for row in rows]

    async def get_one(self, filters: BaseQueryFilter) -> ET | None:
        stmt = self._apply_filters(filters)
        stmt = stmt.limit(1)
        row = await self._session.scalar(stmt)
        return self._to_entity(row) if row else None

    async def get_by_oid(self, oid: str) -> ET | None:
        row = await self._session.get(self._model, oid)

        return self._to_entity(row) if row else None

    async def add(self, data: ET) -> ET:
        orm_obj = self._from_entity(data)
        self._session.add(orm_obj)
        await self._session.flush()

        return self._to_entity(orm_obj)

    def _apply_filters(self, filters: BaseQueryFilter | None) -> Select[tuple[MT]]:
        stmt = select(self._model)

        if not filters:
            return stmt

        sql_filter = self._to_sqlalchemy_filter(filters)
        if sql_filter:
            stmt = sql_filter.apply(stmt, self._model)

        return stmt

    def _to_sqlalchemy_filter(
        self,
        filters: BaseQueryFilter | None,
    ) -> SQLAlchemyQueryFilter | None:
        if not filters:
            return None

        conditions = []
        for condition in filters.conditions:
            sql_cond = SQLAlchemyFieldCondition(
                field=condition.field,
                operator=condition.operator,
                value=condition.value,
            )
            conditions.append(sql_cond)

        return SQLAlchemyQueryFilter(
            conditions=tuple(conditions),
            order_by=filters.order_by,
            limit=filters.limit,
            offset=filters.offset,
        )

    @abstractmethod
    def _to_entity(self, row: MT) -> ET: ...

    @abstractmethod
    def _from_entity(self, data: ET) -> MT: ...

from abc import ABC, abstractmethod
from dataclasses import asdict, fields, is_dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.application.dto import AbstractCreateDTO, AbstractReadDTO
from source.infrastructure.database.models.base import Base


class AbstractRepository(ABC):
    @abstractmethod
    async def add(self, data: AbstractCreateDTO) -> Any: ...

    @abstractmethod
    async def get_list(self, **filters: dict[str, Any]) -> Any: ...


class BaseSQLAlchemyRepository[MT: Base, CT: AbstractCreateDTO](AbstractRepository):
    def __init__(self, session: AsyncSession, model: type[MT]) -> None:
        self._session = session
        self._model = model

    async def add(self, data: CT) -> MT:  # type: ignore[override]
        instance = self._model(**asdict(data))
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def get_list(self, **filters: dict[str, Any]) -> list[MT]:
        stmt = select(self._model)

        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self._model, key) == value)

        results = (await self._session.scalars(stmt)).all()

        return list(results)

    def to_dataclass(self, obj: MT, dto_model: type[AbstractReadDTO]) -> AbstractReadDTO:
        if not is_dataclass(dto_model):
            raise TypeError(f"{dto_model} is not a dataclass")

        field_names = {f.name for f in fields(dto_model)}

        kwargs = {}
        for field_name in field_names:
            kwargs[field_name] = getattr(obj, field_name)

        return dto_model(**kwargs)

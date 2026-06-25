from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class AbstractSQLAlchemyRepository(ABC):
    @abstractmethod
    def __init__(self, session: AsyncSession) -> None: ...

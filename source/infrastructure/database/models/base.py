from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from source.infrastructure.database.models.types import CreatedAt


class Base(DeclarativeBase):
    oid: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[CreatedAt]

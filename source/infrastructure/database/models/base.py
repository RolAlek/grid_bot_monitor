from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BLOB, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    oid: Mapped[UUID] = mapped_column(BLOB(16), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

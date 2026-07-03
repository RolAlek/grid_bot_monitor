from datetime import UTC, datetime
from typing import Annotated

from sqlalchemy import String, func
from sqlalchemy.orm import mapped_column


SymbolType = Annotated[str, mapped_column(String(16), index=True)]
CreatedAt = Annotated[
    datetime,
    mapped_column(server_default=func.now(UTC)),
]
UpdatedAt = Annotated[datetime, mapped_column(server_default=func.now(UTC), onupdate=func.now(UTC))]

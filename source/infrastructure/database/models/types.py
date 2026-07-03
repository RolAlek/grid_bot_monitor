from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import mapped_column


SymbolType = Annotated[str, mapped_column(String(16), index=True)]
CreatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now()),
]
UpdatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
]

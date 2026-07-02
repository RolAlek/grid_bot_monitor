import json
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, cast

from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import mapped_column


SymbolType = Annotated[str, mapped_column(String(16), index=True)]
CreatedAt = Annotated[
    datetime,
    mapped_column(default=lambda: datetime.now(UTC)),
]
UpdatedAt = Annotated[
    datetime,
    mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)),
]


class _EnumEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class JSONType(TypeDecorator[tuple[dict[str, Any]]]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: tuple[dict[str, Any]] | None, dialect: Dialect) -> str | None:  # noqa: ARG002
        if value is not None:
            return json.dumps(value, cls=_EnumEncoder, ensure_ascii=False)

        return None

    def process_result_value(self, value: str | None, dialect: Dialect) -> tuple[dict[str, Any]] | None:  # noqa: ARG002
        if value is not None:
            return cast(tuple[dict[str, Any]], json.loads(value))

        return None

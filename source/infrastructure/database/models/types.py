import json
from typing import Annotated, Any, cast

from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import mapped_column


_symbol = Annotated[str, mapped_column(String(16))]


class JSONType(TypeDecorator[tuple[dict[str, Any]]]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: tuple[dict[str, Any]] | None, dialect: Dialect) -> str | None:  # noqa: ARG002
        if value is not None:
            return json.dumps(value, ensure_ascii=False)

        return None

    def process_result_value(self, value: str | None, dialect: Dialect) -> tuple[dict[str, Any]] | None:  # noqa: ARG002
        if value is not None:
            return cast(tuple[dict[str, Any]], json.loads(value))

        return None

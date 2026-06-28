from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Operator(StrEnum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_OR_EQUALS = "gte"
    LESS_THAN = "lt"
    LESS_OR_EQUALS = "lte"
    IN = "in"
    CONTAINS = "contains"
    ICONTAINS = "icontains"


@dataclass(frozen=True, slots=True)
class BaseFieldCondition:
    field: str
    operator: Operator
    value: Any


@dataclass(frozen=True, slots=True)
class BaseQueryFilter:
    conditions: tuple[BaseFieldCondition, ...] = field(default_factory=tuple)
    order_by: tuple[str, ...] = field(default_factory=tuple)
    limit: int | None = None
    offset: int | None = None

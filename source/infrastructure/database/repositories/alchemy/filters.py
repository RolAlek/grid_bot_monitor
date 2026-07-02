from dataclasses import dataclass, field
from typing import Any, cast

from sqlalchemy import ColumnElement, asc, desc
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute
from sqlalchemy.sql import Select

from source.infrastructure.database.repositories.filters import BaseFieldCondition, BaseQueryFilter


@dataclass(frozen=True, slots=True)
class SQLAlchemyFieldCondition(BaseFieldCondition):
    def to_expression(self, model: type[DeclarativeBase]) -> ColumnElement[bool]:
        column = cast(InstrumentedAttribute[Any], getattr(model, self.field))

        match self.operator:
            case "eq":
                expr = column == self.value
            case "ne":
                expr = column != self.value
            case "gt":
                expr = column > self.value
            case "gte":
                expr = column >= self.value
            case "lt":
                expr = column < self.value
            case "lte":
                expr = column <= self.value
            case "in":
                expr = column.in_(self.value)
            case "contains":
                expr = column.like(f"%{self.value}%")
            case "icontains":
                expr = column.ilike(f"%{self.value}%")
            case _:
                raise AssertionError(f"unreachable operator: {self.operator!r}")

        return cast(ColumnElement[bool], expr)


@dataclass(frozen=True, slots=True)
class SQLAlchemyQueryFilter(BaseQueryFilter):
    conditions: tuple[SQLAlchemyFieldCondition, ...] = field(default_factory=tuple)

    def apply(self, stmt: Select[Any], model: type[DeclarativeBase]) -> Select[Any]:
        if self.conditions:
            stmt = stmt.where(*(condition.to_expression(model) for condition in self.conditions))

        for field_spec in self.order_by:
            column = getattr(model, field_spec.lstrip("-"))
            stmt = stmt.order_by(desc(column) if field_spec.startswith("-") else asc(column))

        if self.limit is not None:
            stmt = stmt.limit(self.limit)

        if self.offset is not None:
            stmt = stmt.offset(self.offset)

        return stmt

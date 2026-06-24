from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel


PrimitiveData = str | int | float | bool | None

TResponse = TypeVar("TResponse", bound=BaseModel)
TError = TypeVar("TError", bound=BaseModel)


IncExType = set[int] | set[str] | dict[int, Any] | dict[str, Any]
PayloadType = BaseModel | Sequence[BaseModel]
ParamType = (
    Mapping[str, PrimitiveData | Sequence[PrimitiveData]]
    | list[tuple[str, PrimitiveData]]
    | tuple[tuple[str, PrimitiveData], ...]
    | str
    | bytes
)
RequestJson = Mapping[str, Any] | str | bytes
HeaderTypes = Mapping[str, str]

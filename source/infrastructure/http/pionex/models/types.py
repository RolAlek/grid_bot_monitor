from typing import Annotated, Any

from pydantic import BeforeValidator


def parse_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except ValueError as error:
        raise TypeError("Invalid type") from error


StringFloat = Annotated[float | None, BeforeValidator(parse_float)]

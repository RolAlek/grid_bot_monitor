from typing import Annotated

from sqlalchemy import String
from sqlalchemy.orm import mapped_column


_symbol = Annotated[str, mapped_column(String(16))]

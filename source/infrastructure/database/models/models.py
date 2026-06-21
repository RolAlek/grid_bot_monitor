from sqlalchemy.orm import Mapped

from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import _symbol


class OISnapshot(Base):
    __tablename__ = "oi_snapshots"

    symbol: Mapped[_symbol]
    open_interests: Mapped[float]


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    symbol: Mapped[_symbol]
    action: Mapped[str]
    gates_json: Mapped[str]
    notes: Mapped[str | None]

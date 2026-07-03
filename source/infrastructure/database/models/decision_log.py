from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.domain.value_objects import VerdictAction
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import JSONType, SymbolType


if TYPE_CHECKING:
    from source.infrastructure.database.models.grid_launch import GridLaunchModel


class DecisionLog(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({', '.join(f"'{action.value}'" for action in VerdictAction)})",
            name="chk_action",
        ),
    )

    symbol: Mapped[SymbolType]
    action: Mapped[str] = mapped_column(String(32))
    gates_json: Mapped[tuple[dict[str, Any]]] = mapped_column(JSONType)
    notes: Mapped[str | None]

    launched_grid: Mapped["GridLaunchModel | None"] = relationship(back_populates="decision_verdict", lazy="joined")

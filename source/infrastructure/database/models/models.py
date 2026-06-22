from typing import Any

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from source.domain.entities import VerdictAction
from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import JSONType, _symbol


class OISnapshot(Base):
    __tablename__ = "oi_snapshots"
    __table_args__ = (Index("idx_oi_snapshot_symbol_created_at", "symbol", "created_at"),)

    symbol: Mapped[_symbol]
    funding_rate_last: Mapped[float]
    funding_rate_annualized_pct: Mapped[float]
    open_interest: Mapped[float]
    oi_pct_change_7d: Mapped[float | None]


class DecisionLog(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (
        CheckConstraint(
            f"action IN ({', '.join(f"'{action.value}'" for action in VerdictAction)})",
            name="chk_action",
        ),
    )

    symbol: Mapped[_symbol]
    action: Mapped[str] = mapped_column(String(32))
    gates_json: Mapped[tuple[dict[str, Any]]] = mapped_column(JSONType)
    notes: Mapped[str | None]

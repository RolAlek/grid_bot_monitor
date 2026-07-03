from sqlalchemy import Index, func, text
from sqlalchemy.orm import Mapped

from source.infrastructure.database.models.base import Base
from source.infrastructure.database.models.types import SymbolType


class OISnapshot(Base):
    __tablename__ = "oi_snapshots"
    __table_args__ = (
        Index("idx_oi_snapshot_symbol_created_at", "symbol", "created_at"),
        Index("uq_oi_snapshot_symbol_date", "symbol", func.date(text("created_at")), unique=True),
    )

    symbol: Mapped[SymbolType]
    funding_rate_last: Mapped[float]
    funding_rate_annualized_pct: Mapped[float]
    open_interest: Mapped[float]
    oi_pct_change_7d: Mapped[float | None]

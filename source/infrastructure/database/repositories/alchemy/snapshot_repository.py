from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger
from structlog.stdlib import BoundLogger

from source.domain.entities import FundingOiSnapshot
from source.domain.exceptions import DuplicateOISnapshotError
from source.domain.value_objects import Symbol
from source.infrastructure.database.models.models import OISnapshot
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository


logger: BoundLogger = get_logger(__name__)


class SQLAlchemySnapshotRepository(SQLAlchemyBaseRepository[FundingOiSnapshot, OISnapshot]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OISnapshot)

    def _as_entity(self, row: OISnapshot) -> FundingOiSnapshot:
        return FundingOiSnapshot(
            symbol=Symbol(row.symbol),
            created_at=row.created_at,
            funding_rate_last=row.funding_rate_last,
            open_interest=row.open_interest,
            oi_pct_change_7d=row.oi_pct_change_7d,
        )

    def _as_orm_model(self, data: FundingOiSnapshot) -> OISnapshot:
        return OISnapshot(
            symbol=data.symbol.value,
            funding_rate_last=data.funding_rate_last,
            funding_rate_annualized_pct=data.funding_rate_annualized_pct,
            open_interest=data.open_interest,
            oi_pct_change_7d=data.oi_pct_change_7d,
        )

    async def add(self, data: FundingOiSnapshot) -> FundingOiSnapshot:
        try:
            return await super().add(data)
        except IntegrityError as error:
            if "uq_oi_snapshot_symbol_date" in str(error.orig):
                logger.warning(
                    "Duplicate OI snapshot — skipping duplicate write",
                    symbol=data.symbol.value,
                    date=data.created_at.date(),
                )
                raise DuplicateOISnapshotError(
                    f"Duplicate OI snapshot for {data.symbol.value} on {data.created_at.date()}",
                    original_error=error,
                ) from error

            raise

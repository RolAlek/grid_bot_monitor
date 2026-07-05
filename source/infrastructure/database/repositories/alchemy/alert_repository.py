from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities.monitoring import Alert
from source.domain.value_objects import AlertType, HealthStatus, Symbol
from source.infrastructure.database.models.alert import AlertModel
from source.infrastructure.database.repositories.alchemy.base import SQLAlchemyBaseRepository


class SQLAlchemyAlertRepository(SQLAlchemyBaseRepository[Alert, AlertModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AlertModel)

    def _as_entity(self, row: AlertModel) -> Alert:
        return Alert(
            oid=row.oid,
            created_at=row.created_at,
            grid_launch_oid=row.grid_launch_oid,
            symbol=Symbol(row.symbol),
            alert_type=AlertType(row.alert_type),
            severity=HealthStatus(row.severity),
            message=row.message,
            health_snapshot_oid=row.health_snapshot_oid,
            acknowledged=row.acknowledged,
            acknowledged_by=row.acknowledged_by,
            acknowledged_at=row.acknowledged_at,
        )

    def _as_orm_model(self, data: Alert) -> AlertModel:
        return AlertModel(
            oid=data.oid or None,  # None → DB generates UUID
            created_at=data.created_at,
            grid_launch_oid=data.grid_launch_oid,
            symbol=data.symbol.value,
            alert_type=data.alert_type.value,
            severity=data.severity.value,
            message=data.message,
            health_snapshot_oid=data.health_snapshot_oid,
            acknowledged=data.acknowledged,
            acknowledged_by=data.acknowledged_by,
            acknowledged_at=data.acknowledged_at,
        )

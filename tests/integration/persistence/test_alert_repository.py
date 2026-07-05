from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from source.domain.entities.monitoring import Alert
from source.domain.value_objects import (
    AlertType,
    GridLaunchStatus,
    GridType,
    HealthStatus,
    Symbol,
    Trend,
    VerdictAction,
)
from source.infrastructure.database.models.decision_log import DecisionLog
from source.infrastructure.database.models.grid_launch import GridLaunchModel
from source.infrastructure.database.repositories.alchemy.alert_repository import SQLAlchemyAlertRepository


@pytest.fixture
async def grid_launch_oid(db_session: AsyncSession) -> str:
    decision = DecisionLog(
        oid=uuid4(),
        symbol=Symbol.BTC.value,
        action=VerdictAction.LAUNCH.value,
        gates_json=(),
    )
    db_session.add(decision)
    await db_session.flush()

    model = GridLaunchModel(
        oid=uuid4(),
        symbol=Symbol.BTC.value,
        grid_top=100_000.0,
        grid_bottom=88_000.0,
        grid_levels=50,
        grid_regime=Trend.NEUTRAL.value,
        grid_type=GridType.GEOMETRIC.value,
        grid_leverage=3,
        quote_investment=1_000.0,
        status=GridLaunchStatus.CLOSED.value,
        closed_at=datetime(2026, 6, 1, tzinfo=UTC),
        decision_verdict_oid=decision.oid,
    )
    db_session.add(model)
    await db_session.flush()
    return str(model.oid)


@pytest.fixture
def alert_repo(db_session: AsyncSession) -> SQLAlchemyAlertRepository:
    return SQLAlchemyAlertRepository(db_session)


def _make_alert(
    *,
    grid_launch_oid: str,
    alert_type: AlertType = AlertType.VOLATILITY_SPIKE,
    severity: HealthStatus = HealthStatus.YELLOW,
    message: str = "ATR spike detected for BTC",
) -> Alert:
    return Alert(
        grid_launch_oid=grid_launch_oid,  # type: ignore[arg-type]
        symbol=Symbol.BTC,
        alert_type=alert_type,
        severity=severity,
        message=message,
    )


async def test_add_and_retrieve_alert_round_trips(
    alert_repo: SQLAlchemyAlertRepository,
    grid_launch_oid: str,
) -> None:
    alert = _make_alert(grid_launch_oid=grid_launch_oid)
    saved = await alert_repo.add(alert)

    assert saved.oid is not None
    assert saved.created_at is not None
    assert saved.symbol == Symbol.BTC
    assert saved.alert_type == AlertType.VOLATILITY_SPIKE
    assert saved.severity == HealthStatus.YELLOW
    assert saved.message == "ATR spike detected for BTC"
    assert saved.acknowledged is False

    retrieved = await alert_repo.get_by_oid(saved.oid)  # type: ignore[arg-type]
    assert retrieved is not None
    assert retrieved.oid == saved.oid
    assert retrieved.alert_type == AlertType.VOLATILITY_SPIKE


async def test_get_by_oid_returns_none_for_unknown(
    alert_repo: SQLAlchemyAlertRepository,
) -> None:
    result = await alert_repo.get_by_oid("00000000-0000-0000-0000-00000000dead")  # type: ignore[arg-type]
    assert result is None


async def test_get_list_returns_all_alerts(
    alert_repo: SQLAlchemyAlertRepository,
    grid_launch_oid: str,
) -> None:
    await alert_repo.add(_make_alert(grid_launch_oid=grid_launch_oid, message="Alert 1"))
    await alert_repo.add(
        _make_alert(grid_launch_oid=grid_launch_oid, message="Alert 2", alert_type=AlertType.LIQUIDATION_RISK)
    )

    all_alerts = await alert_repo.get_list()
    assert len(all_alerts) == 2
    messages = {a.message for a in all_alerts}
    assert messages == {"Alert 1", "Alert 2"}

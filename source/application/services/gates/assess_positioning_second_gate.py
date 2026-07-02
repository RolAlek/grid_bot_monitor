import structlog

from source.application.ports import MarketDataPort
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.use_cases.check_positioning_rules import build_positioning_checks
from source.application.utils import evaluate_checks
from source.domain.entities import GateResult
from source.domain.value_objects import Gate, Symbol
from source.settings import DecisionEngineSettings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AssessPositioningService:
    def __init__(
        self,
        settings: DecisionEngineSettings,
        market_data: MarketDataPort,
        oi_service: OISnapshotService,
    ) -> None:
        self._settings = settings
        self._market_data = market_data
        self._oi_service = oi_service

    async def execute(self, symbol: Symbol) -> GateResult:
        logger.info("Start assessing positioning for %s", symbol.value)

        snapshot = await self._oi_service.create_snapshot(symbol)
        checks = build_positioning_checks(snapshot, self._settings)
        statuses, reasons = evaluate_checks(checks)

        await self._oi_service.persist_oi_snapshot(snapshot)

        return GateResult(
            gate=Gate.POSITIONING,
            status=statuses,
            reasons=reasons,
            raw_values={
                "funding_rate_annualized_pct": snapshot.funding_rate_annualized_pct,
                "oi_pct_change_7d": snapshot.oi_pct_change_7d,
                "open_interest": snapshot.open_interest,
            },
        )

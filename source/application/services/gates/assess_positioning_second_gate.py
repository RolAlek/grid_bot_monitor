from datetime import UTC, datetime

import structlog

from source.application.ports import MarketDataPort
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.use_cases.check_positioning_rueles import build_positioning_checks
from source.application.utils import evaluate_checks
from source.domain.entities import FundingOiSnapshot, OpenInterest
from source.domain.value_objects import Gate, GateResult, Symbol
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

        snapshot = await self._build_snapshot(symbol)
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

    async def _build_snapshot(self, symbol: Symbol) -> FundingOiSnapshot:
        current_dt = datetime.now(UTC)
        funding_rate = await self._pull_latest_funding_rate(symbol)
        open_interest, oi_change = await self._pull_latest_oi(symbol, current_dt)

        return FundingOiSnapshot(
            symbol=symbol,
            as_of=current_dt,
            funding_rate_last=funding_rate,
            open_interest=open_interest.open_interest,
            oi_pct_change_7d=oi_change,
        )

    async def _pull_latest_funding_rate(self, symbol: Symbol) -> float:
        try:
            rows = await self._market_data.get_funding_rates(symbol, limit=1)
            rows.sort(key=lambda rate: rate.time)
            return float(rows[-1].rate)
        except Exception:
            logger.exception("Failed to fetch latest funding rate", symbol=symbol.value)
            raise

    async def _pull_latest_oi(self, symbol: Symbol, current_dt: datetime) -> tuple[OpenInterest, float | None]:
        try:
            oi = await self._market_data.get_open_interest(symbol)
            oi_change = await self._oi_service.compute_oi_pct_change_7d(
                symbol=symbol,
                as_of=current_dt,
                newest_oi=oi.open_interest,
            )
            return oi, oi_change
        except Exception:
            logger.exception("Failed to fetch latest open interest", symbol=symbol.value)
            raise

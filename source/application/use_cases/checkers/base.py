from datetime import datetime

from source.application.ports import MarketDataPort
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.use_cases.assess_positioning import AssessPositioning
from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.entities import FundingOiSnapshot, GateResult, Symbol


class BaseChecker:
    def __init__(self, market_data: MarketDataPort, gate2: AssessPositioning, oi_service: OISnapshotService) -> None:
        self._market_data = market_data
        self._gate2 = gate2
        self._oi_service = oi_service

    async def check_second_gate(
        self, symbol: Symbol, now: datetime, *, is_save: bool
    ) -> tuple[GateResult, FundingOiSnapshot]:
        oi = await self._market_data.get_open_interest(symbol)
        funding_rows = await self._market_data.get_funding_rates(symbol, limit=1)
        rate = float(funding_rows[-1].rate)

        oi_change = await self._oi_service.compute_oi_pct_change_7d(
            symbol=symbol,
            as_of=now,
            newest_oi=oi.open_interest,
        )

        snapshot = FundingOiSnapshot(
            symbol=symbol,
            as_of=now,
            funding_rate_last=rate,
            funding_rate_annualized_pct=rate * FUNDING_ANNUALIZATION_FACTOR,
            open_interest=float(oi.open_interest),
            oi_pct_change_7d=oi_change,
        )

        if is_save:
            await self._oi_service.persist_oi_snapshot(snapshot)

        return self._gate2.assess(snapshot), snapshot
